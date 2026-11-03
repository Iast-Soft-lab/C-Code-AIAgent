import argparse
import json

from pathlib import Path

from backend.config import PROJECT_ROOT, SETTINGS
from backend.clang_analyzer import run_clang_analysis
from backend.cppcheck_analyzer import (
    run_cppcheck_analysis,
    run_misra_analysis
)
from backend.result_processor import build_analysis_report


def main():

    parser = argparse.ArgumentParser(
        description="Run C static analysis."
    )

    parser.add_argument(
        "source_file",
        help="Path to the C source file."
    )

    parser.add_argument(
        "--output",
        help="Optional custom path for the JSON report."
    )

    args = parser.parse_args()

    file_path = Path(args.source_file).expanduser().resolve()

    if not file_path.is_file():
        parser.error(f"Input file does not exist: {file_path}")

    allowed_extensions = {
        extension.lower()
        for extension in SETTINGS["input"]["allowed_extensions"]
    }

    if file_path.suffix.lower() not in allowed_extensions:
        parser.error(
            f"Unsupported file extension. Allowed extensions: "
            f"{', '.join(sorted(allowed_extensions))}"
        )

    print("Running Clang...")
    clang_result = run_clang_analysis(str(file_path))

    print("Running Cppcheck...")
    cppcheck_result = run_cppcheck_analysis(str(file_path))

    print("Running MISRA analysis...")
    misra_result = run_misra_analysis(str(file_path))

    report = build_analysis_report(
        file_name=file_path.name,
        clang_result=clang_result,
        cppcheck_result=cppcheck_result,
        misra_result=misra_result
    )

    report_settings = SETTINGS["report"]

    if args.output:
        output_file = Path(args.output).expanduser().resolve()
    else:
        output_directory = Path(
            report_settings["output_directory"]
        ).expanduser()

        if not output_directory.is_absolute():
            output_directory = PROJECT_ROOT / output_directory

        output_file = (
            output_directory / report_settings["filename"]
        ).resolve()

    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_file.write_text(
        json.dumps(
            report,
            indent=report_settings["json_indent"],
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print("\nAnalysis completed!")
    print(json.dumps(report["summary"], indent=report_settings["json_indent"]))

    print(f"\nJSON report saved at: {output_file}")


if __name__ == "__main__":
    main()
