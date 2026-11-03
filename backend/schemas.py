from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolError(BaseModel):
    tool: str
    error: str


class AnalysisSummary(BaseModel):
    total_findings: int
    programming_defects: int
    code_quality_findings: int
    misra_violations: int
    misra_unique_rules: int


class AnalysisFinding(BaseModel):
    model_config = ConfigDict(extra="allow")

    finding_id: str
    file: str
    line: int | None = None
    column: int | None = None
    category: str
    issue_type: str
    severity: str
    message: str
    analysis_type: str

    detected_by: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)
    tool_diagnostics: list[dict[str, Any]] = Field(
        default_factory=list
    )

    tool_issue_id: str | None = None
    misra_rule_id: str | None = None
    cwe: str | None = None


class AnalysisReport(BaseModel):
    model_config = ConfigDict(extra="allow")

    report_id: str
    schema_version: str
    file_name: str
    analysis_status: str

    tools_used: list[str]
    summary: AnalysisSummary
    tool_errors: list[ToolError]
    findings: list[AnalysisFinding]
