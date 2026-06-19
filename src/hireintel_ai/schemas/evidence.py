"""Evidence schemas for traceable resume and JD claims."""

from pydantic import BaseModel, Field


class EvidenceSnippet(BaseModel):
    """Source-backed evidence attached to extracted fields and scores.

    Attributes:
        document_id: Identifier of the source document.
        section: Resume or JD section where evidence was found.
        text: Source text supporting the extracted claim.
        page_number: Optional page number for PDF-like sources.
    """

    document_id: str
    section: str
    text: str = Field(min_length=1)
    page_number: int | None = None

