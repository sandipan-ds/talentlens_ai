"""Quick demo: run JD matching against the BusinessAnalyst Lead JD."""
from pathlib import Path

from src.rag.jd_match import match_jd


def main() -> None:
    jd_path = Path("data/Job descriptions/BusinessAnalyst/BusinessAnalyst_Lead_JD.md")
    result = match_jd(jd_path, role_bucket="BusinessAnalyst", top_k=5)

    print(f"JD file: {result['jd_file']}")
    print(f"Requirements extracted: {result['requirement_count']}")
    print(f"Candidates considered: {result['candidates_considered']}")
    print()
    print("=== Top 5 candidates ===")
    for i, m in enumerate(result["matches"], 1):
        print(
            f"  #{i}  {m['candidate_id']}  role={m['role_bucket']}  "
            f"best={m['best_score']:.3f}  avg={m['avg_score']:.3f}  "
            f"matched={m['requirements_matched']}/{m['requirements_total']}"
        )
        if m["evidence"]:
            e = m["evidence"][0]
            print(
                f"        evidence[{e['section']}, score={e['score']:.3f}]: "
                f"{e['snippet'][:100]}..."
            )
            print(
                f"        for requirement [{e['requirement_section']}]: "
                f"{e['requirement'][:80]}..."
            )


if __name__ == "__main__":
    main()
