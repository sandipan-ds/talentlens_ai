"""Schemas for recruiter scoring policies and candidate evaluations."""

from pydantic import BaseModel, Field

from hireintel_ai.schemas.evidence import EvidenceSnippet


class ScoringPolicy(BaseModel):
    """Recruiter-defined scoring policy for a job.

    Attributes:
        policy_id: Stable scoring policy identifier.
        job_id: Job identifier this policy applies to.
        weights: Requirement or category weights; values should sum to 100.
    """

    policy_id: str
    job_id: str
    weights: dict[str, float] = Field(default_factory=dict)


class ScoreBreakdown(BaseModel):
    """Score and evidence for one evaluation dimension.

    Attributes:
        dimension: Evaluation dimension such as skill coverage.
        score: Earned score for the dimension.
        max_score: Maximum possible score for the dimension.
        evidence: Resume evidence supporting the score.
    """

    dimension: str
    score: float
    max_score: float
    evidence: list[EvidenceSnippet] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    """Candidate evaluation result produced by deterministic scoring.

    Attributes:
        candidate_id: Candidate being evaluated.
        job_id: Job being evaluated against.
        total_score: Final deterministic score.
        breakdown: Per-dimension score explanations.
    """

    candidate_id: str
    job_id: str
    total_score: float
    breakdown: list[ScoreBreakdown] = Field(default_factory=list)

