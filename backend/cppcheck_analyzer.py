import subprocess
import xml.etree.ElementTree as ET

from pathlib import Path
from backend.config import get_tool_settings


def run_cppcheck_analysis(file_path: str):

    file_path = Path(file_path).resolve()

    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    settings = get_tool_settings("cppcheck")

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

        xml_output = result.stderr

        start = xml_output.find("<?xml")

        if start == -1:
            start = xml_output.find("<results")

        if start == -1:
            return {
                "tool": settings["display_name"],
                "file": file_path.name,
                "return_code": result.returncode,
                "findings": [],
                "error": "Cppcheck did not return XML output",
                "raw_output": result.stdout + result.stderr
            }

        xml_output = xml_output[start:]

        root = ET.fromstring(xml_output)

        findings = []

        for error in root.findall(".//errors/error"):

            locations = error.findall("location")

            primary_location = (
                locations[0] if locations else None
            )

            findings.append({
                "tool": settings["display_name"],
                "file": (
                    primary_location.get("file")
                    if primary_location is not None
                    else file_path.name
                ),
                "line": (
                    int(primary_location.get("line"))
                    if primary_location is not None
                    and primary_location.get("line")
                    else None
                ),
                "issue_id": error.get("id"),
                "severity": error.get("severity"),
                "message": error.get("msg"),
                "verbose": error.get("verbose"),
                "cwe": error.get("cwe")
            })

        return {
            "tool": settings["display_name"],
            "file": file_path.name,
            "return_code": result.returncode,
            "findings_count": len(findings),
            "findings": findings
        }

    except ET.ParseError as exc:
        return {
            "tool": settings["display_name"],
            "file": file_path.name,
            "error": f"Could not parse XML: {exc}"
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


def run_misra_analysis(file_path: str):

    file_path = Path(file_path).resolve()

    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    settings = get_tool_settings("misra")

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
            "raw_output": result.stdout + result.stderr
        }

    except subprocess.TimeoutExpired:
        return {
            "tool": settings["display_name"],
            "file": file_path.name,
            "error": (
                f"MISRA analysis timed out after "
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
