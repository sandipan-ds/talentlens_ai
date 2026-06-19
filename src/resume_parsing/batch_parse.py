"""Batch parse resumes from `data/original/` and save structured profiles.

Usage:
    python src/resume_parsing/batch_parse.py

This will write JSON profiles to `data/processed/<role>/<filename>.json`.
"""

import json
import traceback
from pathlib import Path

from src.resume_parsing.parser import parse_resume


ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "data" / "original"
PROCESSED = ROOT / "data" / "processed"


def main():
    if not ORIGINAL.exists():
        print(f"No original resume folder found at {ORIGINAL}")
        return

    PROCESSED.mkdir(parents=True, exist_ok=True)

    roles = [p for p in ORIGINAL.iterdir() if p.is_dir()]
    for role_dir in sorted(roles):
        out_dir = PROCESSED / role_dir.name
        out_dir.mkdir(parents=True, exist_ok=True)
        files = sorted([f for f in role_dir.iterdir() if f.is_file()])
        print(f"Parsing {len(files)} files in {role_dir.name}...")
        for f in files:
            try:
                profile = parse_resume(f)
                out_file = out_dir / (f.stem + ".json")
                with out_file.open("w", encoding="utf-8") as fh:
                    json.dump(profile, fh, ensure_ascii=False, indent=2)
            except Exception as exc:  # pragma: no cover - operational
                print(f"Failed to parse {f}: {exc}")
                traceback.print_exc()

    print("Batch parsing complete.")


if __name__ == "__main__":
    main()
