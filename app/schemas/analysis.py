from typing import Literal

from pydantic import BaseModel, Field


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
