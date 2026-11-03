
import re
import os
from backend.config import SETTINGS


# Convert different tool messages into common issue categories.
def classify_issue(issue_id: str, message: str):

    text = f"{issue_id} {message}".lower()

    classification = SETTINGS["classification"]

    for rule in classification["issue_rules"]:

        if any(keyword in text for keyword in rule["match_any"]):
            return rule["issue_type"], rule["category"]

    default_issue = classification["default_issue"]

    return (
        default_issue["issue_type"],
        default_issue["category"]
    )

# Convert Clang's text diagnostics into structured findings.
def parse_clang_findings(clang_result: dict):

    findings = []

    output = clang_result.get("stderr", "")

    diagnostic_pattern = re.compile(
        r"^(?P<file>.+?):"
        r"(?P<line>\d+):"
        r"(?P<column>\d+): "
        r"(?P<severity>warning|error|fatal error): "
        r"(?P<message>.*?)(?: \[(?P<check>[^\]]+)\])?$"
    )

    for line in output.splitlines():

        match = diagnostic_pattern.match(line.strip())

        if not match:
            continue

        data = match.groupdict()

        message = data["message"]
        check_id = data.get("check") or "unknown"

        issue_type, category = classify_issue(
            check_id,
            message
        )

        findings.append({
            "file": os.path.basename(os.path.normpath(data["file"])),
            "line": int(data["line"]),
            "column": int(data["column"]),
            "category": category,
            "issue_type": issue_type,
            "severity": (
                "error"
                if data["severity"] == "fatal error"
                else data["severity"]
            ),
            "message": message,
            "analysis_type": "static_analysis",
            "detected_by": "Clang",
            "tool_issue_id": check_id
        })

    return findings


# Convert Cppcheck XML findings into our common format.
def parse_cppcheck_findings(cppcheck_result: dict):

    findings = []

    for item in cppcheck_result.get("findings", []):

        issue_id = item.get("issue_id", "unknown")
        message = item.get("message", "")

        issue_type, category = classify_issue(
            issue_id,
            message
        )

        # Separate style suggestions from programming defects.
        analysis_type = (
            "code_quality"
            if item.get("severity") == "style"
            else "static_analysis"
        )

        findings.append({
            "file": os.path.basename(os.path.normpath(item.get("file", ""))),
            "line": item.get("line"),
            "column": None,
            "category": category,
            "issue_type": issue_type,
            "severity": item.get("severity", "unknown"),
            "message": message,
            "analysis_type": analysis_type,
            "detected_by": "Cppcheck",
            "tool_issue_id": issue_id,
            "cwe": item.get("cwe")
        })

    return findings


# Extract only MISRA C:2012 messages from the addon output.
def parse_misra_findings(misra_result: dict):

    findings = []

    output = misra_result.get("raw_output", "")

    pattern = re.compile(
        r"^(?P<file>.+?):"
        r"(?P<line>\d+):"
        r"(?P<column>\d+):\s*"
        r"(?P<severity>\w+):\s*"
        r"misra violation.*?"
        r"\[(?P<rule>misra-c2012-(?P<rule_id>\d+(?:\.\d+)?))\]"
    )

    for line in output.splitlines():

        match = pattern.match(line.strip())

        if not match:
            continue

        data = match.groupdict()

        rule_id = data["rule_id"]

        findings.append({
            "file": os.path.basename(os.path.normpath(data["file"])),
            "line": int(data["line"]),
            "column": int(data["column"]),
            "category": "MISRA Compliance",
            "issue_type": "MISRA Rule Violation",
            "severity": data["severity"],
            "message": (
                f"Cppcheck MISRA addon reported "
                f"a violation of MISRA C:2012 Rule {rule_id}."
            ),
            "analysis_type": "misra",
            "detected_by": "Cppcheck MISRA Addon",
            "misra_rule_id": f"MISRA-C:2012-{rule_id}",
            "tool_issue_id": data["rule"]
        })

    return findings


# Identify findings that refer to the same underlying issue.
def get_deduplication_key(finding):

    file_name = finding.get("file", "")
    line = finding.get("line")

    if finding["analysis_type"] == "misra":
        return (
            "misra",
            file_name,
            line,
            finding.get("misra_rule_id")
        )

    return (
        "code",
        file_name,
        line,
        finding.get("issue_type")
    )


# Merge duplicate reports while preserving tool evidence.
def merge_findings(findings):

    merged = {}

    severity_rank = SETTINGS["classification"]["severity_rank"]

    for finding in findings:

        key = get_deduplication_key(finding)

        diagnostic = {
            "tool": finding["detected_by"],
            "tool_issue_id": finding.get("tool_issue_id"),
            "severity": finding["severity"],
            "message": finding["message"],
            "column": finding.get("column"),
            "cwe": finding.get("cwe")
        }

        if key not in merged:

            item = finding.copy()

            item["detected_by"] = [finding["detected_by"]]
            item["messages"] = [finding["message"]]
            item["tool_diagnostics"] = [diagnostic]

            merged[key] = item

        else:

            existing = merged[key]

            if finding["detected_by"] not in existing["detected_by"]:
                existing["detected_by"].append(
                    finding["detected_by"]
                )

            if finding["message"] not in existing["messages"]:
                existing["messages"].append(finding["message"])

            # Preserve unique diagnostic evidence only.
            if diagnostic not in existing["tool_diagnostics"]:
                existing["tool_diagnostics"].append(diagnostic)

            current_rank = severity_rank.get(
                existing["severity"], 0
            )

            new_rank = severity_rank.get(
                finding["severity"], 0
            )

            if new_rank > current_rank:
                existing["severity"] = finding["severity"]

    return list(merged.values())


# Main function: build the final report.
def build_analysis_report(
    file_name: str,
    clang_result: dict,
    cppcheck_result: dict,
    misra_result: dict
):

    clang_findings = parse_clang_findings(clang_result)

    cppcheck_findings = parse_cppcheck_findings(
        cppcheck_result
    )

    misra_findings = parse_misra_findings(misra_result)

    all_findings = (
        clang_findings
        + cppcheck_findings
        + misra_findings
    )

    final_findings = merge_findings(all_findings)

    for index, finding in enumerate(final_findings, start=1):
        finding["finding_id"] = f"F{index:03d}"

    programming_defects = sum(
        1 for item in final_findings
        if item["analysis_type"] == "static_analysis"
    )

    quality_findings = sum(
        1 for item in final_findings
        if item["analysis_type"] == "code_quality"
    )

    misra_violations = sum(
        1 for item in final_findings
        if item["analysis_type"] == "misra"
    )

    misra_unique_rules = len({
        item.get("misra_rule_id")
        for item in final_findings
        if item["analysis_type"] == "misra"
        and item.get("misra_rule_id")
    })

    tool_errors = []

    for tool_name, result in [
        ("Clang", clang_result),
        ("Cppcheck", cppcheck_result),
        ("MISRA", misra_result)
    ]:
        if result.get("error"):
            tool_errors.append({
                "tool": tool_name,
                "error": result["error"]
            })

    return {
        "schema_version": "1.0",
        "file_name": file_name,
        "analysis_status": (
            "completed_with_errors"
            if tool_errors
            else "completed"
        ),

        "tools_used": [
            "Clang Static Analyzer",
            "Cppcheck",
            "Cppcheck MISRA Addon"
        ],

        "summary": {
            "total_findings": len(final_findings),
            "programming_defects": programming_defects,
            "code_quality_findings": quality_findings,
            "misra_violations": misra_violations,
            "misra_unique_rules": misra_unique_rules
        },

        "tool_errors": tool_errors,
        "findings": final_findings
    }
