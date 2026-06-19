"""Generate chunk JSONL files from all parsed profiles in ``data/processed``.

For each role folder, this script reads the structured profile JSONs
produced by :mod:`src.resume_parsing.batch_parse` and writes one
``data/chunks/<RoleBucket>/<candidate_id>.jsonl`` file containing the
chunk records (one JSON object per line). The output is ready to be
embedded and indexed by the retrieval pipeline.

Usage::

    python -m src.rag.batch_chunk
"""

import json
from pathlib import Path
from typing import List

from src.rag.chunker import ChunkRecord, chunk_profile


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
CHUNKS = ROOT / "data" / "chunks"


def _role_bucket_from_path(path: Path) -> str:
    """Return the role bucket (parent folder name) for a processed JSON."""
    return path.parent.name


def _chunk_profile_path(candidate_id: str, role_bucket: str) -> Path:
    safe_id = candidate_id or "cand_unknown"
    return CHUNKS / role_bucket / f"{safe_id}.jsonl"


def _write_chunks(role_bucket: str, candidate_id: str, chunks: List[ChunkRecord]) -> Path:
    out_path = _chunk_profile_path(candidate_id, role_bucket)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
    return out_path


def main() -> None:
    if not PROCESSED.exists():
        print(f"No processed profiles found at {PROCESSED}. Run batch_parse first.")
        return

    CHUNKS.mkdir(parents=True, exist_ok=True)

    total_files = 0
    total_chunks = 0
    for role_dir in sorted(p for p in PROCESSED.iterdir() if p.is_dir()):
        role_bucket = role_dir.name
        json_files = sorted(role_dir.glob("*.json"))
        if not json_files:
            continue
        print(f"Chunking {len(json_files)} profiles in {role_bucket}...")
        for profile_path in json_files:
            try:
                profile = json.loads(profile_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                print(f"  skip {profile_path.name}: {exc}")
                continue
            candidate_id = profile.get("candidate_id") or profile_path.stem
            chunks = chunk_profile(profile, role_bucket=role_bucket)
            _write_chunks(role_bucket, candidate_id, chunks)
            total_files += 1
            total_chunks += len(chunks)

    print(f"Chunking complete. {total_files} profiles -> {total_chunks} chunks.")


if __name__ == "__main__":
    main()
