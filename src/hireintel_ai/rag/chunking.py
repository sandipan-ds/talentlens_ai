"""Document-aware chunking placeholders for resume retrieval."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResumeChunk:
    """Retrieval chunk preserving resume structure.

    Attributes:
        chunk_id: Stable chunk identifier.
        resume_id: Source resume identifier.
        section: Resume section name.
        text: Chunk text.
    """

    chunk_id: str
    resume_id: str
    section: str
    text: str

