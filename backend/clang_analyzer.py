import subprocess

from pathlib import Path
from backend.config import get_tool_settings


def run_clang_analysis(file_path: str):

    file_path = Path(file_path).resolve()

    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    settings = get_tool_settings("clang")

    command = [
        settings["executable"],
        *settings["arguments"],
        str(file_path)
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=settings["timeout_seconds"],
            check=False
        )

        return {
            "tool": settings["display_name"],
            "file": file_path.name,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    except subprocess.TimeoutExpired:
        return {
            "tool": settings["display_name"],
            "file": file_path.name,
            "error": (
                f"Analysis timed out after "
                f"{settings['timeout_seconds']} seconds"
            )
        }

    except FileNotFoundError:
        return {
            "tool": settings["display_name"],
            "file": file_path.name,
            "error": (
                f"Analyzer executable unavailable: "
                f"{settings['executable']}"
            )
        }
