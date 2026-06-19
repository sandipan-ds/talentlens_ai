"""Shared typed schemas used across platform workflows."""

from hireintel_ai.schemas.candidate import CandidateProfile
from hireintel_ai.schemas.evidence import EvidenceSnippet
from hireintel_ai.schemas.job_description import JobDescription, Requirement
from hireintel_ai.schemas.scoring import EvaluationResult, ScoreBreakdown, ScoringPolicy

__all__ = [
    "CandidateProfile",
    "EvaluationResult",
    "EvidenceSnippet",
    "JobDescription",
    "Requirement",
    "ScoreBreakdown",
    "ScoringPolicy",
]

