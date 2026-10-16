from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

class LogEntry(BaseModel):
    level: str = "error"
    message: str

class MetricPoint(BaseModel):
    name: str
    value: float
    unit: str | None = None
    baseline: float | None = None
    note: str | None = None

class CodeChange(BaseModel):
    commit: str | None = None
    file: str | None = None
    message: str | None = None

class HistoricalIncident(BaseModel):
    incident_id: str
    summary: str
    root_cause: str
    similarity: float | None = Field(default=None, ge=0, le=1)

class IncidentRequest(BaseModel):
    service: str
    repository: str | None = None
    github_branch: str | None = None
    github_commit_limit: int = Field(default=3, ge=1, le=10)

    deployment_id: str | None = None
    error: str
    severity: Literal["low", "medium", "high", "critical"] = "high"

    logs: list[LogEntry] = Field(default_factory=list)
    metrics: list[MetricPoint] = Field(default_factory=list)
    recent_changes: list[CodeChange] = Field(default_factory=list)
    historical_incidents: list[HistoricalIncident] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

class Hypothesis(BaseModel):
    rank: int
    cause: str
    confidence: float = Field(ge=0, le=1)
    supporting_evidence: list[str]
    recommended_checks: list[str]

class IncidentAnalysis(BaseModel):
    incident_id: str
    status: Literal["completed", "needs_more_evidence"]
    summary: str
    hypotheses: list[Hypothesis]
    recommended_action: str
    needs_human_review: bool = True
    evidence_count: int
    github_changes_collected: int = 0

class IncidentRecordOut(BaseModel):
    incident_id: str
    service: str
    deployment_id: str | None
    error: str
    status: str
    created_at: datetime
    result: dict | None = None
