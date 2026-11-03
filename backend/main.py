import json
import logging
import tempfile
import uuid

from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    status
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from backend.config import PROJECT_ROOT, SETTINGS
from backend.clang_analyzer import run_clang_analysis
from backend.cppcheck_analyzer import (
    run_cppcheck_analysis,
    run_misra_analysis
)
from backend.result_processor import build_analysis_report
from backend.schemas import AnalysisReport


logger = logging.getLogger(__name__)

api_settings = SETTINGS["api"]

app = FastAPI(
    title=api_settings["title"],
    version=api_settings["version"],
    description=api_settings["description"],
    docs_url=api_settings["docs_url"],
    openapi_url=api_settings["openapi_url"]
)


def resolve_project_path(configured_path: str) -> Path:

    path = Path(configured_path).expanduser()

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


def get_report_path(report_id: str) -> Path:

    try:
        parsed_id = uuid.UUID(hex=report_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found."
        )

    if parsed_id.hex != report_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found."
        )

    report_settings = SETTINGS["report"]

    report_directory = resolve_project_path(
        report_settings["output_directory"]
    )

    report_filename = report_settings[
        "api_filename_template"
    ].format(report_id=parsed_id.hex)

    return report_directory / report_filename


def run_analysis_and_save(
    source_path: Path,
    original_filename: str
) -> dict:

    logger.info("Starting analysis for %s", original_filename)

    clang_result = run_clang_analysis(str(source_path))

    cppcheck_result = run_cppcheck_analysis(str(source_path))

    misra_result = run_misra_analysis(str(source_path))

    report = build_analysis_report(
        file_name=original_filename,
        clang_result=clang_result,
        cppcheck_result=cppcheck_result,
        misra_result=misra_result
    )

    report_id = uuid.uuid4().hex
    report["report_id"] = report_id

    report_path = get_report_path(report_id)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report_settings = SETTINGS["report"]

    report_path.write_text(
        json.dumps(
            report,
            indent=report_settings["json_indent"],
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    logger.info("Analysis report saved: %s", report_path)

    return report


@app.get(api_settings["health_route"])
def health_check():

    return {
        "status": "healthy",
        "service": api_settings["title"]
    }


@app.get(api_settings["ui_config_route"])
def frontend_config():

    return {
        "title": api_settings["title"],
        "health_route": api_settings["health_route"],
        "analyze_route": api_settings["analyze_route"],
        "download_route_template": api_settings["download_route"],
        "allowed_extensions": SETTINGS["input"]["allowed_extensions"],
        "max_file_size_bytes": SETTINGS["upload"]["max_file_size_bytes"],
        "pasted_code_filename": SETTINGS["upload"][
            "pasted_code_filename"
        ]
    }


@app.post(
    api_settings["analyze_route"],
    response_model=AnalysisReport
)
async def analyze_uploaded_file(
    file: UploadFile | None = File(default=None),
    code: str | None = Form(default=None)
):

    # Require exactly one input method.
    if file is None and code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a C file or paste C source code."
        )

    if file is not None and code is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either a file or pasted code, not both."
        )

    upload_settings = SETTINGS["upload"]

    maximum_size = upload_settings["max_file_size_bytes"]
    chunk_size = upload_settings["read_chunk_bytes"]

    if maximum_size <= 0 or chunk_size <= 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid upload configuration."
        )

    if file is not None:
        raw_filename = (file.filename or "").replace("\\", "/")
        original_filename = raw_filename.rsplit("/", 1)[-1]
    else:
        original_filename = upload_settings["pasted_code_filename"]

    original_filename = (
        original_filename.strip().replace("\x00", "")
    )

    if not original_filename or original_filename in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid filename is required."
        )

    allowed_extensions = {
        extension.lower()
        for extension in SETTINGS["input"]["allowed_extensions"]
    }

    if Path(original_filename).suffix.lower() not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported file type. Allowed extensions: "
                f"{', '.join(sorted(allowed_extensions))}"
            )
        )

    temporary_root = resolve_project_path(
        upload_settings["temporary_directory"]
    )

    try:
        temporary_root.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(
            prefix=upload_settings["temporary_directory_prefix"],
            dir=temporary_root
        ) as temporary_directory:

            temporary_file = (
                Path(temporary_directory) / original_filename
            )

            received_bytes = 0

            if file is not None:

                with temporary_file.open("wb") as destination:

                    while True:
                        chunk = await file.read(chunk_size)

                        if not chunk:
                            break

                        received_bytes += len(chunk)

                        if received_bytes > maximum_size:
                            raise HTTPException(
                                status_code=(
                                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                                ),
                                detail=(
                                    "Uploaded file exceeds the configured "
                                    "maximum size."
                                )
                            )

                        destination.write(chunk)

            else:

                if not code or not code.strip():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Pasted C source code cannot be empty."
                    )

                source_bytes = code.encode("utf-8")
                received_bytes = len(source_bytes)

                if received_bytes > maximum_size:
                    raise HTTPException(
                        status_code=(
                            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                        ),
                        detail=(
                            "Pasted code exceeds the configured "
                            "maximum size."
                        )
                    )

                temporary_file.write_bytes(source_bytes)

            if received_bytes == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The source input is empty."
                )

            report = await run_in_threadpool(
                run_analysis_and_save,
                temporary_file,
                original_filename
            )

            return report

    except HTTPException:
        raise

    except Exception:
        logger.exception("Source analysis failed.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed. Check the server logs."
        )

    finally:
        if file is not None:
            await file.close()


@app.get(api_settings["download_route"])
def download_report(report_id: str):

    report_path = get_report_path(report_id)

    if not report_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found."
        )

    return FileResponse(
        path=report_path,
        media_type="application/json",
        filename=report_path.name
    )


frontend_directory = resolve_project_path(
    SETTINGS["frontend"]["static_directory"]
)

if not frontend_directory.is_dir():
    raise RuntimeError(
        f"Frontend directory not found: {frontend_directory}"
    )

# Keep the static mount after all API routes.
app.mount(
    "/",
    StaticFiles(directory=str(frontend_directory), html=True),
    name="frontend"
)
