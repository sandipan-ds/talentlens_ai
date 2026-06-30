# Model Registry

## Overview

This document tracks production AI models, model-adjacent components, and deterministic evaluation strategies for HireIntel AI.

All model changes must be documented here before implementation, and significant AI architecture changes must also update `AI_DESIGN_RATIONALE.md`, `AI_ARCHITECTURE.md`, and `DECISIONS.md`.

---

## Current Registry

| Component | Current Selection | Status | Purpose |
| --- | --- | --- | --- |
| Active LLM | OpenRouter `minimax/minimax-m3` | **Active** | Candidate comparison narrative (`scripts/compare_two.py`); score explanation scaffold (`src/hireintel_ai/llm/service.py`). Resume chat and rubric-bound evidence scoring are **planned** but not yet implemented. |
| Primary LLM (production upgrade) | GPT-4 | Proposed | Resume parsing support, JD extraction support, summaries, comparisons, explanations |
| Fallback LLM (production upgrade) | Claude 3 | Proposed | Long-context fallback for large resumes and document-heavy comparison tasks |
| Private / Local LLM | Llama 3 | Proposed | Privacy-first deployment option where candidate data cannot leave controlled infrastructure |
| **Embedding Model** | **`sentence-transformers/all-MiniLM-L6-v2`** | **Active** | **Chunk and JD-bullet embeddings; 384-dim, CPU-runnable, ~80 MB, no API key** |
| Alternative Embedding Model | BGE-M3 | Future | Multilingual upgrade path; CPU-runnable but larger |
| Cloud Embedding Option | OpenAI `text-embedding-3-small` | Future | Highest quality but per-token API cost; data egress concern |
| Reranker | None yet | Future | Optional cross-encoder reranker for top-K precision boost (pool-level search only) |
| **Chunking Strategy** | **Document-Aware (section-based, one chunk per experience/education/project)** | **Active** | **Preserves resume structure; supports sub-split at 1200 chars with 120 char overlap** |
| **Header Normalization** | **Synonym lookup table + fallback classification (7 canonical sections)** | **Active** | **Maps heterogeneous resume headers to canonical section labels at parse time** |
| **Vector Storage** | **In-memory numpy (`data/embeddings/index.npz`)** | **Active** | **4k chunks × 384 dims ≈ 6 MB; trivial to load; switchable to Qdrant without API changes** |
| Planned Vector Database | Qdrant | Future | When scale exceeds single-machine memory or we need hosted multi-user |
| **Per-Candidate Evidence Retrieval** | **Section-Routed (exact label match on canonical sections, no embeddings)** | **Active** | **Fetches full mapped section content per requirement for rubric-bound LLM scoring** |
| **Cross-Candidate Pool Retrieval** | **Dense cosine over in-memory index** | **Active** | **Used by JD matching (triage) and resume chat (RAG); never used for per-candidate scoring** |
| **Keyword Scoring Strategy** | **Deprecated — see `graded_scorer`** | **Legacy** | **Superseded by the single deterministic scorer below** |
| **Semantic Scoring Strategy** | **Deprecated — see `graded_scorer`** | **Legacy** | **Superseded by the single deterministic scorer below** |
| **Hybrid Scoring Strategy** | **Deprecated — see `graded_scorer`** | **Legacy** | **Superseded by the single deterministic scorer below** |
| **Code-Only Scoring** | **`src/scoring/graded_scorer.py`: per-item `min(importance, candidate_years / expected_years × importance)`, normalized to 0-100** | **Active** | **Scores total experience, skill presence/years, degree match, cert match — no LLM** |
| **Rubric-Bound LLM Evidence Scoring** | **LLM judge scores against recruiter-defined rubric; weight application in code** | **Planned** | **Scores skill depth, relevant/same-role/leadership experience, project complexity; LLM never sees weight or computes aggregation** |
| **Candidate Ranking Strategy** | **Sort by the deterministic scorer's normalized total; ties broken by per-item matched count** | **Active** | **LLM never determines final ranking** |

---

## Chunking Configuration

| Parameter | Value | Source |
| --- | --- | --- |
| Max chunk size | 1200 chars | `src/rag/chunker.MAX_CHUNK_CHARS` |
| Sub-split overlap | 120 chars | `src/rag/chunker.SPLIT_OVERLAP_CHARS` |
| Sub-split rule | paragraph breaks (`\n\n`) then hard sentence split | `src/rag/chunker._emit_section_chunks` |
| Per-experience chunking | one chunk per entry (title + company + dates + location + bullets) | `src/rag/chunker.chunk_profile` |
| Per-education chunking | one chunk per entry | `src/rag/chunker.chunk_profile` |
| Chunk ID format | `{candidate_id}__{section}__{index}` | e.g. `cand_xxx__experience__2` |

## Scoring Configuration

| Parameter | Value | Source |
| --- | --- | --- |
| Default expected years (when config omits) | 10 | `src/scoring/graded_scorer.DEFAULT_EXPECTED_YEARS` |
| Per-item score rule | `min(importance, candidate_years / expected_years × importance)` | `src/scoring/graded_scorer.evaluate_candidate` |
| Partial credit (mentioned, no years) | `importance × 0.3` | `src/scoring/graded_scorer.evaluate_candidate` |
| Total normalization | `total_raw × (100 / max_score)` from the weight config's `scale_factor` | `src/scoring/graded_scorer.evaluate_candidate` |
| Section priority | experience.entries → skills → education.entries → certifications → projects → summary | `src/scoring/graded_scorer._search_profile` |
| Summary-years fallback | only for items in non-Education / non-Certification categories | `src/scoring/graded_scorer._is_experience_item` |
| Synonym dictionary | `src/scoring/graded_scorer._SYNONYMS` (curated, with regex word boundaries) | `src/scoring/graded_scorer._aliases_for` |

---

## Change Control

Before changing any model, retrieval strategy, reranker, chunking approach, or scoring methodology:

1. Add or update an entry in `DECISIONS.md`.
2. Update `AI_DESIGN_RATIONALE.md`.
3. Update this registry.
4. Update `AI_ARCHITECTURE.md` when workflow impact exists.
5. Update `EVALUATION.md` with required validation metrics.

