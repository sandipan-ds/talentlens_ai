"""Batch scoring CLI — the single canonical scorer.

Per ``docs/WORKING_LOGIC.md`` and ``docs/AI_DESIGN_RATIONALE.md`` §5,
HireIntel AI uses **one** deterministic scorer (``graded_scorer``).
The legacy ``keyword`` / ``semantic`` / ``hybrid`` strategies are
deprecated; passing them prints a warning and forwards to the
canonical scorer so old scripts keep working.

Output
------
    data/scores/graded/<role>_ranked.json

Each row has the shape returned by
``scoring.graded_scorer.CandidateEvaluation.to_dict()``:

    {
      "candidate_id": "...",
      "role":         "...",
      "total_raw":    <float, sum of per-item raw scores>,
      "total_max":    <float, sum of per-item importance>,
      "total":        <float, 0-100 normalized>,
      "categories":   [<CategoryEvaluation>, ...]
    }

Example
-------

::

    python -m src.scoring.batch_score \\
        --role BusinessAnalyst

    # Legacy alias still works (with a deprecation warning):
    python -m src.scoring.batch_score \\
        --role BusinessAnalyst --strategy keyword
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import List

from src.scoring.graded_scorer import (
    DEFAULT_EXPECTED_YEARS,
    evaluate_role as graded_evaluate_role,
)


SCORES_ROOT = Path("data/scores")


def _default_output_path(role: str) -> Path:
    return SCORES_ROOT / "graded" / f"{role}_ranked.json"


def _ranked_rows(evaluations) -> List[dict]:
    """Convert a list of CandidateEvaluation into ranked JSON rows.

    Candidates are sorted by ``total`` descending so the output file
    is already ordered by rank — downstream consumers can read it
    positionally without re-sorting.
    """
    ranked = sorted(
        (e.to_dict() for e in evaluations),
        key=lambda r: r["total"],
        reverse=True,
    )
    for i, row in enumerate(ranked, 1):
        row["rank"] = i
    return ranked


def _run_graded(
    role: str,
    profile_dir: Path,
    weights_path: Path,
    output_path: Path,
    top: int,
    default_expected_years: int,
) -> int:
    print(f"[graded]   scoring role '{role}' from {profile_dir}")
    print(f"[graded]   weights       : {weights_path}")
    print(f"[graded]   default years : {default_expected_years}")
    evaluations = graded_evaluate_role(
        role=role,
        profile_dir=profile_dir,
        weights_path=weights_path,
        default_expected_years=default_expected_years,
    )
    ranked = _ranked_rows(evaluations)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(ranked, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _print_top(ranked, top)
    print(f"-> wrote {len(ranked)} candidates to {output_path}")
    return len(ranked)


def _print_top(rows: List[dict], top: int) -> None:
    n = min(top, len(rows))
    print()
    print(f"=== Top {n} candidates ===")
    for row in rows[:n]:
        print(
            f"  #{row['rank']:>2d}  {row['candidate_id']}  "
            f"score={row['total']:5.1f}/100  "
            f"(raw {row['total_raw']:.1f} / {row['total_max']:.1f})  "
            f"role={row['role']}"
        )


def _warn_deprecated_strategy(strategy: str) -> None:
    msg = (
        f"--strategy {strategy!r} is deprecated; HireIntel AI now ships a single "
        f"deterministic scorer (graded_scorer). Forwarding to --strategy graded."
    )
    warnings.warn(msg, DeprecationWarning, stacklevel=2)
    print(f"WARNING: {msg}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Batch score candidates with the canonical deterministic scorer "
            "(scoring.graded_scorer)."
        ),
    )
    parser.add_argument("--role", required=True, help="Role bucket (e.g. BusinessAnalyst)")
    parser.add_argument(
        "--strategy",
        choices=["graded", "keyword", "semantic", "hybrid"],
        default="graded",
        help=(
            "Scoring strategy. Only 'graded' is supported; the legacy values "
            "are kept as deprecated aliases."
        ),
    )
    parser.add_argument(
        "--weights",
        type=Path,
        default=None,
        help=(
            "Path to recruiter weight config. "
            "Defaults to data/Job descriptions/<role>/<role>_WeightConfig_filled.json."
        ),
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=None,
        help="Directory of structured profiles. Defaults to data/processed/<role>.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path. Defaults to data/scores/graded/<role>_ranked.json.",
    )
    parser.add_argument(
        "--default-years",
        type=int,
        default=DEFAULT_EXPECTED_YEARS,
        help="Default expected years when an item has none (WORKING_LOGIC Step 5).",
    )
    parser.add_argument("--top", type=int, default=10, help="Print top N candidates.")
    args = parser.parse_args()

    if args.strategy != "graded":
        _warn_deprecated_strategy(args.strategy)

    profile_dir = args.profile_dir or Path("data/processed") / args.role
    weights_path = args.weights or (
        Path("data/Job descriptions") / args.role / f"{args.role}_WeightConfig_filled.json"
    )
    output_path = args.output or _default_output_path(args.role)

    if not profile_dir.exists():
        parser.error(f"--profile-dir not found: {profile_dir}")
    if not weights_path.exists():
        parser.error(f"--weights not found: {weights_path}")

    _run_graded(
        role=args.role,
        profile_dir=profile_dir,
        weights_path=weights_path,
        output_path=output_path,
        top=args.top,
        default_expected_years=args.default_years,
    )


if __name__ == "__main__":
    main()