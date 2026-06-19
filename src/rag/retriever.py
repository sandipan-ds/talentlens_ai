"""High-level retriever API used by Phase 4 (scoring) and Phase 6 (RAG chat).

Wraps :class:`VectorIndex` and provides convenience methods that take text
queries directly, embed them with the configured model, and return ranked
chunk hits.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .embeddings import DEFAULT_MODEL_NAME, embed_texts
from .index import INDEX_PATH, METADATA_PATH, VectorIndex


# Singleton — the index is read-only after first build and is shared
# across queries. This avoids re-loading the vectors on every call.
_INDEX: Optional[VectorIndex] = None


def get_index() -> VectorIndex:
    """Return the process-wide vector index, loading from disk on first call."""
    global _INDEX
    if _INDEX is None:
        _INDEX = VectorIndex.load(INDEX_PATH, METADATA_PATH)
    return _INDEX


def rebuild_index() -> VectorIndex:
    """Force-rebuild the on-disk index from ``data/chunks/``."""
    global _INDEX
    _INDEX = VectorIndex.build()
    return _INDEX


def retrieve(
    query: str,
    top_k: int = 10,
    role_bucket: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Embed ``query`` and return the top-K most similar chunks.

    Args:
        query: Free-text requirement or question.
        top_k: Number of hits to return.
        role_bucket: Optional filter, e.g. ``"BusinessAnalyst"``.

    Returns:
        List of hit dicts, each containing ``chunk_id``, ``candidate_id``,
        ``role_bucket``, ``source_file``, ``section``, ``chunk_index``,
        ``char_span``, ``text``, ``metadata``, ``score``.
    """
    index = get_index()
    if not query or not query.strip():
        return []
    vectors = embed_texts([query])
    return index.search(vectors[0], top_k=top_k, role_bucket=role_bucket)


def retrieve_for_candidate(
    query: str,
    candidate_id: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Restrict retrieval to chunks belonging to a single candidate.

    Useful when Phase 6 RAG chat answers a recruiter question about a
    specific candidate ("Has Alice led a team of 5+?") so the answer is
    grounded in that resume only.
    """
    index = get_index()
    if not query or not query.strip():
        return []
    vectors = embed_texts([query])
    all_hits = index.search(vectors[0], top_k=top_k * 5)  # over-fetch
    return [h for h in all_hits if h["candidate_id"] == candidate_id][:top_k]
