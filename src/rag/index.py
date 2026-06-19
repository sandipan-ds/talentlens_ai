"""Build a local in-memory vector index over all chunk JSONL files.

The index is deliberately simple:

* No external vector DB dependency (FAISS / Qdrant etc.) — just numpy.
* Persisted to ``data/embeddings/index.npz`` so the retriever can load it
  on startup without re-embedding thousands of chunks.
* Stores chunk metadata (candidate_id, section, char_span, source_file) so
  retrieved hits can be cited back to the original resume.

For 5-10k chunks the in-memory approach is faster than any DB; if we ever
outgrow it we can swap :func:`VectorIndex.load` to read from FAISS without
changing the rest of the pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .embeddings import embed_texts


ROOT = Path(__file__).resolve().parents[2]
CHUNKS_DIR = ROOT / "data" / "chunks"
INDEX_DIR = ROOT / "data" / "embeddings"
INDEX_PATH = INDEX_DIR / "index.npz"
METADATA_PATH = INDEX_DIR / "chunks.jsonl"


@dataclass
class ChunkMetadata:
    """One chunk's metadata, kept alongside its vector in the index."""

    chunk_id: str
    candidate_id: str
    role_bucket: str
    source_file: str
    section: str
    chunk_index: int
    text: str
    char_span: List[int]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_jsonl(cls, raw: Dict[str, Any]) -> "ChunkMetadata":
        return cls(
            chunk_id=raw["chunk_id"],
            candidate_id=raw["candidate_id"],
            role_bucket=raw.get("role_bucket", ""),
            source_file=raw.get("source_file", ""),
            section=raw.get("section", ""),
            chunk_index=int(raw.get("chunk_index", 0)),
            text=raw.get("text", ""),
            char_span=list(raw.get("char_span", [0, 0])),
            metadata=dict(raw.get("metadata", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "candidate_id": self.candidate_id,
            "role_bucket": self.role_bucket,
            "source_file": self.source_file,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "char_span": self.char_span,
            "metadata": self.metadata,
        }


class VectorIndex:
    """In-memory vector index backed by numpy.

    Use :meth:`build` once to (re)build from disk, or :meth:`load` to read
    a persisted index. The retriever uses :meth:`search` to find the top-K
    most similar chunks to a query embedding.
    """

    def __init__(self) -> None:
        self.vectors: Optional[np.ndarray] = None  # shape: (n, dim)
        self.metadata: List[ChunkMetadata] = []

    # ------------------------- Build / persist -------------------------

    @classmethod
    def build(cls, chunks_dir: Path = CHUNKS_DIR, persist: bool = True) -> "VectorIndex":
        """Read all chunk JSONL files in ``chunks_dir`` and (optionally) persist."""
        index = cls()
        metadata: List[ChunkMetadata] = []
        texts: List[str] = []
        jsonl_files = sorted(chunks_dir.glob("*/*.jsonl"))
        if not jsonl_files:
            raise FileNotFoundError(f"No chunk JSONL files found under {chunks_dir}")
        for jsonl in jsonl_files:
            with jsonl.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    raw = json.loads(line)
                    meta = ChunkMetadata.from_jsonl(raw)
                    metadata.append(meta)
                    texts.append(meta.text)

        vectors = embed_texts(texts)
        index.vectors = vectors
        index.metadata = metadata
        if persist:
            index.save()
        return index

    def save(self, index_path: Path = INDEX_PATH, metadata_path: Path = METADATA_PATH) -> None:
        """Persist vectors and metadata to disk."""
        if self.vectors is None:
            raise RuntimeError("Index is empty — call build() first.")
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(index_path, vectors=self.vectors)
        with metadata_path.open("w", encoding="utf-8") as fh:
            for meta in self.metadata:
                fh.write(json.dumps(meta.to_dict(), ensure_ascii=False) + "\n")

    # ------------------------- Load ------------------------------------

    @classmethod
    def load(cls, index_path: Path = INDEX_PATH, metadata_path: Path = METADATA_PATH) -> "VectorIndex":
        """Load a previously persisted index."""
        if not index_path.exists() or not metadata_path.exists():
            raise FileNotFoundError(
                f"Index not found at {index_path} / {metadata_path}. Run build_index first."
            )
        index = cls()
        with np.load(index_path) as data:
            index.vectors = data["vectors"]
        with metadata_path.open("r", encoding="utf-8") as fh:
            index.metadata = [ChunkMetadata.from_jsonl(json.loads(line)) for line in fh if line.strip()]
        return index

    # ------------------------- Search ----------------------------------

    def search(self, query_vector, top_k: int = 10, role_bucket: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return top-K most similar chunks as a list of dicts with score."""
        if self.vectors is None:
            raise RuntimeError("Index is empty — call build() or load() first.")
        q = np.asarray(query_vector, dtype=np.float32)
        if q.ndim == 1:
            q = q[np.newaxis, :]
        # Cosine similarity (vectors are unit-norm from embed_texts).
        scores = (self.vectors @ q.T).ravel()
        # Optional role filter.
        if role_bucket:
            mask = np.array([m.role_bucket == role_bucket for m in self.metadata], dtype=bool)
            if not mask.any():
                return []
            scores = np.where(mask, scores, -np.inf)
        # Top-K indices.
        k = min(top_k, scores.size)
        # argpartition is O(n); we then sort the top-K slice for deterministic order.
        idx = np.argpartition(-scores, k - 1)[:k]
        idx = idx[np.argsort(-scores[idx])]
        hits: List[Dict[str, Any]] = []
        for i in idx:
            score = float(scores[i])
            if score == -np.inf:
                continue
            meta = self.metadata[int(i)]
            hits.append(
                {
                    "chunk_id": meta.chunk_id,
                    "candidate_id": meta.candidate_id,
                    "role_bucket": meta.role_bucket,
                    "source_file": meta.source_file,
                    "section": meta.section,
                    "chunk_index": meta.chunk_index,
                    "char_span": meta.char_span,
                    "text": meta.text,
                    "metadata": meta.metadata,
                    "score": score,
                }
            )
        return hits

    def __len__(self) -> int:
        return 0 if self.vectors is None else int(self.vectors.shape[0])
