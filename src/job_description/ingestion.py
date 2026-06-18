"""Load and normalize job description files."""

from pathlib import Path


def load_job_description(path: Path) -> str:
    """Read job description content from a file."""
    return path.read_text(encoding="utf-8")
