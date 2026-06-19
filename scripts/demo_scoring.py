"""Show the component breakdown for the top-ranked BusinessAnalyst candidate."""
import json
from pathlib import Path

from src.scoring.evidence import explain_candidate
from src.scoring.evaluate import CandidateScore


def main() -> None:
    ranked_path = Path("data/scores/BusinessAnalyst_ranked.json")
    if not ranked_path.exists():
        print(f"{ranked_path} not found. Run batch_score first.")
        return
    ranked = json.loads(ranked_path.read_text(encoding="utf-8"))

    top = ranked[0]
    score = CandidateScore(
        candidate_id=top["candidate_id"],
        role_bucket=top["role_bucket"],
        raw_score=top["raw_score"],
        max_score=top["max_score"],
        normalized_score=top["normalized_score"],
        scale_factor=top["scale_factor"],
        components=[
            # Re-hydrate components minimally for the explanation helper.
            type("C", (), c)() for c in top["components"]
        ],
        source_file=top.get("source_file"),
    )

    print(f"=== Top candidate: {top['candidate_id']} ===")
    print(f"Score: {top['normalized_score']:.1f}/100  "
          f"(raw {top['raw_score']:.1f} / {top['max_score']:.1f})")
    print(f"Matched: {top['matched_components']} / {top['total_components']}")
    print()
    print("=== Component breakdown ===")
    for c in top["components"]:
        flag = "OK " if c["matched"] else "-- "
        print(
            f"  {flag} [{c['category']:18s}] {c['item_name']:36s} "
            f"imp={c['importance']:>2}  earned={c['matched_weight']:>5.1f}"
        )
        if c["matched"]:
            print(f"        notes : {c['notes']}")
            if c.get("chunk_id"):
                print(f"        chunk : {c['chunk_id']}")
            if c.get("source_file"):
                print(f"        source: {c['source_file']}")
        print()
    print("=== Plain-text explanation ===")
    print(explain_candidate(score))


if __name__ == "__main__":
    main()
