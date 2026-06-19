"""Schemas for job descriptions and extracted hiring requirements."""

from pydantic import BaseModel, Field

from hireintel_ai.schemas.evidence import EvidenceSnippet


class Requirement(BaseModel):
    """A single hiring requirement extracted from a job description.

    Attributes:
        name: Requirement label such as `Python` or `B.Tech`.
        category: Requirement category such as skill, education, or experience.
        required: Whether the JD presents this requirement as mandatory.
        evidence: Source evidence from the job description.
    """

    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    required: bool = True
    evidence: list[EvidenceSnippet] = Field(default_factory=list)


class JobDescription(BaseModel):
    """Structured job description used to generate scoring policy options.

    Attributes:
        job_id: Stable job identifier.
        title: Role title.
        raw_text: Original extracted JD text.
        requirements: Structured requirements extracted from the JD.
    """

    job_id: str
    title: str
    raw_text: str
    requirements: list[Requirement] = Field(default_factory=list)

