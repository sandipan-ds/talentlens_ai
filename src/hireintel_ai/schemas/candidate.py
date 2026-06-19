"""Schemas for parsed candidate profile data."""

from pydantic import BaseModel, Field

from hireintel_ai.schemas.evidence import EvidenceSnippet


class CandidateProfile(BaseModel):
    """Structured profile extracted from a candidate resume.

    Attributes:
        candidate_id: Stable candidate identifier.
        resume_id: Source resume identifier.
        name: Candidate name when found in the resume.
        skills: Extracted candidate skills.
        education: Extracted education statements.
        experience: Extracted work experience statements.
        projects: Extracted project statements.
        evidence: Supporting evidence snippets for extracted profile fields.
    """

    candidate_id: str
    resume_id: str
    name: str | None = None
    skills: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSnippet] = Field(default_factory=list)

