"""Document ingestion contracts shared by loaders and parsers."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadedDocument:
    """Normalized representation of an ingested document.

    Attributes:
        document_id: Stable document identifier.
        source_path: Original local or object-storage path.
        text: Extracted document text.
    """

    document_id: str
    source_path: Path
    text: str

