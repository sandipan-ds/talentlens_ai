"""Embedding model wrapper for chunk and JD text.

We pick a small, fast, locally-runnable sentence-transformer as the primary
embedding model so the pipeline works without an external API key.

Default model: ``sentence-transformers/all-MiniLM-L6-v2``

* 384-dim embeddings
* ~80 MB download
* Runs on CPU; ~200 chunks/sec on a modern laptop
* Strong semantic matching for short English business text

The model is downloaded on first use into ``$HF_HOME`` (defaults to
``~/.cache/huggingface``). It is loaded once and reused across requests via
the module-level ``get_embedder()`` factory.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedder(model_name: str = DEFAULT_MODEL_NAME):
    """Return a cached SentenceTransformer instance.

    Using ``lru_cache`` ensures we only load the model weights from disk
    once per process, even when ``embed_texts`` is called many times by the
    indexer, retriever, and tests.
    """
    from sentence_transformers import SentenceTransformer

    # Allow override via env so production deployments can swap to a stronger
    # model without touching code.
    chosen = os.environ.get("HIREINTEL_EMBED_MODEL", model_name)
    return SentenceTransformer(chosen)


def embed_texts(texts: List[str], model_name: str = DEFAULT_MODEL_NAME, batch_size: int = 64):
    """Embed a list of strings into a 2-D numpy array of shape (n, dim).

    Empty / whitespace-only inputs are replaced with a single space so the
    encoder does not crash on degenerate inputs. The original ordering is
    preserved.
    """
    safe = [(t.strip() or " ") for t in texts]
    embedder = get_embedder(model_name)
    import numpy as np

    vectors = embedder.encode(
        safe,
        batch_size=batch_size,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True,  # unit-norm → dot product == cosine
    )
    return np.asarray(vectors, dtype=np.float32)


def cosine_similarity(a, b):
    """Cosine similarity between two equally-shaped 1-D or 2-D arrays.

    Returns a 1-D array if both inputs are 1-D, otherwise a 2-D matrix
    where ``result[i, j]`` is the cosine similarity between ``a[i]`` and
    ``b[j]``.
    """
    import numpy as np

    a_arr = np.asarray(a, dtype=np.float32)
    b_arr = np.asarray(b, dtype=np.float32)
    if a_arr.ndim == 1:
        a_arr = a_arr[np.newaxis, :]
    if b_arr.ndim == 1:
        b_arr = b_arr[np.newaxis, :]
    # Embeddings produced by ``normalize_embeddings=True`` are already
    # unit-norm, so dot product == cosine. We re-normalize defensively in
    # case the user swapped in a non-normalizing model.
    a_norm = a_arr / np.clip(np.linalg.norm(a_arr, axis=1, keepdims=True), 1e-12, None)
    b_norm = b_arr / np.clip(np.linalg.norm(b_arr, axis=1, keepdims=True), 1e-12, None)
    return a_norm @ b_norm.T
