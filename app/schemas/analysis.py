from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

BoundedIndicator = Annotated[str, Field(min_length=1, max_length=500)]
BoundedAction = Annotated[str, Field(min_length=1, max_length=500)]


class AnalysisFinding(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=500)
    severity: Literal["CAUTION", "SUSPICIOUS"]


class RetrievedScamCase(BaseModel):
    case_id: int = Field(alias="caseId")
    title: str = Field(min_length=1, max_length=255)
    scam_type: str = Field(min_length=1, max_length=100, alias="scamType")
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(alias="riskLevel")
    score: float = Field(ge=0, le=1)
    verified: bool
    description: str | None = Field(default=None, max_length=2_000)
    sample_text: str | None = Field(default=None, max_length=10_000, alias="sampleText")
    indicators: list[BoundedIndicator] = Field(default_factory=list, max_length=50)


class RiskSignal(BaseModel):
    category: Literal[
        "CREDENTIAL_THEFT",
        "PAYMENT_OR_ASSET_TRANSFER",
        "IMPERSONATION",
        "URGENCY_OR_COERCION",
        "REMOTE_ACCESS_OR_MALWARE",
        "INVESTMENT_OR_TASK_SCAM",
        "EXTORTION_OR_THREAT",
        "IDENTITY_THEFT",
        "SUSPICIOUS_LINK",
        "SOCIAL_ENGINEERING",
        "OTHER",
    ]
    severity: Literal["CAUTION", "SUSPICIOUS", "CRITICAL"]
    evidence: str = Field(min_length=1, max_length=240)
    message: str = Field(min_length=1, max_length=280)


class AnalyzeRequest(BaseModel):
    type: Literal["TEXT", "URL"]
    value: str = Field(min_length=1, max_length=10_000)
    language: Literal["en", "km"] = "en"
    deterministic_findings: list[AnalysisFinding] = Field(default_factory=list, max_length=50, alias="deterministicFindings")
    retrieved_cases: list[RetrievedScamCase] = Field(default_factory=list, max_length=10, alias="retrievedCases")
    retrieval_status: Literal["AVAILABLE", "UNAVAILABLE", "NOT_REQUESTED"] = Field(
        default="NOT_REQUESTED", alias="retrievalStatus"
    )
    top_similarity: float | None = Field(default=None, ge=0, le=1, alias="topSimilarity")
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

    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(alias="riskLevel")
    confidence_score: float = Field(ge=0, le=1, alias="confidenceScore")
    assessment: Literal[
        "NO_STRONG_WARNING_SIGNS",
        "INSUFFICIENT_EVIDENCE",
        "CAUTION",
        "SUSPICIOUS",
        "STRONG_SCAM_INDICATORS",
    ]
    evidence_sufficiency: Literal["SUFFICIENT", "AMBIGUOUS", "INSUFFICIENT"] = Field(
        alias="evidenceSufficiency"
    )
    risk_signals: list[RiskSignal] = Field(max_length=8, alias="riskSignals")
    summary: str = Field(min_length=1, max_length=280)
    recommended_actions: list[BoundedAction] = Field(min_length=1, max_length=3, alias="recommendedActions")
