"""Batch scoring CLI with strategy dispatch.

Strategies
----------

* ``keyword``  — deterministic keyword + heuristic scorer. Per-criterion
  binary match, normalized to 100. Pure recruiter weights. Fast, auditable.
* ``semantic`` — JD-bullet → candidate's chunks cosine similarity. Handles
  synonyms and paraphrases the keyword scorer misses. Slower (one embedding
  per JD bullet per candidate) but more semantically aware.
* ``hybrid``   — ``alpha * keyword + (1 - alpha) * semantic``. Default
  ``alpha = 0.5`` (equal blend).

Output folders (always one per strategy, never mixed)::

    data/scores/keyword/<role>_ranked.json
    data/scores/semantic/<role>_ranked.json
    data/scores/hybrid/<role>_ranked.json

Examples
--------

::

    # Keyword only (original Phase 4 behavior, unchanged)
    python -m src.scoring.batch_score \\
        --role BusinessAnalyst \\
        --weights "data/Job descriptions/BusinessAnalyst/BusinessAnalyst_WeightConfig_filled.json" \\
        --strategy keyword

    # Semantic only
    python -m src.scoring.batch_score \\
        --role BusinessAnalyst \\
        --jd "data/Job descriptions/BusinessAnalyst/BusinessAnalyst_Lead_JD.md" \\
        --strategy semantic

    # Hybrid
    python -m src.scoring.batch_score \\
        --role BusinessAnalyst \\
        --weights "data/Job descriptions/BusinessAnalyst/BusinessAnalyst_WeightConfig_filled.json" \\
        --jd "data/Job descriptions/BusinessAnalyst/BusinessAnalyst_Lead_JD.md" \\
        --strategy hybrid --alpha 0.5
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from src.scoring.hybrid_scorer import evaluate_role_hybrid
from src.scoring.keyword_scorer import evaluate_role
from src.scoring.semantic_scorer import evaluate_role_semantic


SCORES_ROOT = Path("data/scores")


def _default_output_path(strategy: str, role: str) -> Path:
    return SCORES_ROOT / strategy / f"{role}_ranked.json"


def _run_keyword(role: str, weights_path: Path, output_path: Path, top: int) -> int:
    print(f"[keyword]  scoring role '{role}' from {weights_path}")
    results = evaluate_role(role, weights_path, output_path=output_path)
    _print_top(results, top, score_key="normalized_score")
    return len(results)


def _run_semantic(role: str, jd_path: Path, output_path: Path, top: int) -> int:
    print(f"[semantic] scoring role '{role}' against JD {jd_path}")
    results = evaluate_role_semantic(role, jd_path, output_path=output_path)
    _print_top(results, top, score_key="normalized_score")
    return len(results)


def _run_hybrid(
    role: str,
    weights_path: Path,
    jd_path: Path,
    output_path: Path,
    top: int,
    alpha: float,
) -> int:
    print(f"[hybrid]   scoring role '{role}' alpha={alpha}")
    results = evaluate_role_hybrid(
        role_bucket=role,
        jd_path=jd_path,
        weight_config_path=weights_path,
        alpha=alpha,
        output_path=output_path,
    )
    _print_top(results, top, score_key="final_score")
    return len(results)


def _print_top(results: List[dict], top: int, score_key: str) -> None:
    print(f"-> wrote {len(results)} candidates")
    print()
    n = min(top, len(results))
    print(f"=== Top {n} candidates ===")
    for i, r in enumerate(results[:n], 1):
        cand = r["candidate_id"]
        role = r.get("role_bucket", "")
        score = r.get(score_key, 0.0)
        extra = ""
        if "keyword_score" in r and "semantic_score" in r:
            extra = f"  kw={r['keyword_score']:.1f}  sem={r['semantic_score']:.1f}"
        print(f"  #{i:2d}  {cand}  score={score:5.1f}/100{extra}  role={role}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch score candidates with keyword, semantic, or hybrid strategy.",
    )
    parser.add_argument("--role", required=True, help="Role bucket (e.g. BusinessAnalyst)")
    parser.add_argument(
        "--strategy",
        required=True,
        choices=["keyword", "semantic", "hybrid"],
        help="Scoring strategy to run.",
    )
    parser.add_argument(
        "--weights",
        type=Path,
        default=None,
        help="Path to recruiter weight config (required for keyword / hybrid).",
    )
    parser.add_argument(
        "--jd",
        type=Path,
        default=None,
        help="Path to JD markdown file (required for semantic / hybrid).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path. Defaults to data/scores/<strategy>/<role>_ranked.json.",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="Blend weight on keyword score (0=pure semantic, 1=pure keyword). Default 0.5.",
    )
    parser.add_argument("--top", type=int, default=10, help="Print top N candidates.")
    args = parser.parse_args()

    output_path: Path = args.output or _default_output_path(args.strategy, args.role)

    if args.strategy == "keyword":
        if not args.weights:
            parser.error("--weights is required for --strategy keyword")
        _run_keyword(args.role, args.weights, output_path, args.top)
    elif args.strategy == "semantic":
        if not args.jd:
            parser.error("--jd is required for --strategy semantic")
        _run_semantic(args.role, args.jd, output_path, args.top)
    else:  # hybrid
        if not args.weights or not args.jd:
            parser.error("--weights and --jd are required for --strategy hybrid")
        _run_hybrid(args.role, args.weights, args.jd, output_path, args.top, args.alpha)


if __name__ == "__main__":
    main()
