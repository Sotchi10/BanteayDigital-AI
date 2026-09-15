from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AnalysisFinding(BaseModel):
    code: str
    message: str
    severity: Literal["CAUTION", "SUSPICIOUS"]


class RetrievedScamCase(BaseModel):
    case_id: int = Field(alias="caseId")
    title: str
    scam_type: str = Field(alias="scamType")
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(alias="riskLevel")
    score: float = Field(ge=0, le=1)
    verified: bool


class AnalyzeRequest(BaseModel):
    type: Literal["TEXT", "URL"]
    value: str = Field(min_length=1, max_length=10_000)
    deterministic_findings: list[AnalysisFinding] = Field(default_factory=list, alias="deterministicFindings")
    retrieved_cases: list[RetrievedScamCase] = Field(default_factory=list, alias="retrievedCases")
    url_evidence: "UrlEvidence | None" = Field(default=None, alias="urlEvidence")

    @model_validator(mode="after")
    def validate_url_context(self) -> "AnalyzeRequest":
        if self.url_evidence is not None and self.type != "URL":
            raise ValueError("urlEvidence is only accepted for URL scans")
        return self


class UrlStats(BaseModel):
    malicious: int = Field(ge=0)
    suspicious: int = Field(ge=0)
    harmless: int = Field(ge=0)
    undetected: int = Field(ge=0)
    timeout: int = Field(ge=0)


class UrlDetection(BaseModel):
    engine: str = Field(min_length=1, max_length=200)
    category: Literal["malicious", "suspicious"]
    result: str | None = Field(default=None, max_length=200)


class UrlEvidence(BaseModel):
    provider: Literal["VirusTotal"] = "VirusTotal"
    status: Literal["queued", "in-progress", "completed"]
    analysis_date: int | None = Field(default=None, ge=0, alias="analysisDate")
    stats: UrlStats | None = None
    detections: list[UrlDetection] = Field(default_factory=list, max_length=200)
    final_url: str | None = Field(default=None, max_length=10_000, alias="finalUrl")
    source: Literal["report", "analysis"]

    @model_validator(mode="after")
    def validate_completed_stats(self) -> "UrlEvidence":
        if self.status == "completed" and (
            self.stats is None or sum(self.stats.model_dump().values()) == 0
        ):
            raise ValueError("Completed URL evidence requires usable statistics")
        return self


AnalyzeRequest.model_rebuild()


class GroundedAnalysis(BaseModel):
    """Small, user-facing result returned by the testing AI integration."""

    assessment: Literal[
        "NO_STRONG_WARNING_SIGNS",
        "INSUFFICIENT_EVIDENCE",
        "CAUTION",
        "SUSPICIOUS",
        "STRONG_SCAM_INDICATORS",
    ]
    summary: str = Field(min_length=1, max_length=280)
    recommended_actions: list[str] = Field(min_length=1, max_length=3, alias="recommendedActions")
