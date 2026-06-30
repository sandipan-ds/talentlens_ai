# Implementation Roadmap

## Overview
This roadmap defines the step-by-step execution plan for HireIntel AI, aligned
with `AGENTS.md`, `docs/PROJECT_OVERVIEW.md`, and the canonical scoring spec
[`docs/WORKING_LOGIC.md`](WORKING_LOGIC.md). For "what is implemented today vs
what's planned", see [`docs/CURRENT_PROGRESS.md`](CURRENT_PROGRESS.md).

---

## Phase 0: Foundation & alignment
1. Confirm repository structure
   - Ensure `/docs` exists and contains required docs.
   - Treat `/docs` as source of truth.
2. Establish documentation process
   - Keep `PROJECT_OVERVIEW.md`, `SYSTEM_ARCHITECTURE.md`, `AI_ARCHITECTURE.md`, `AI_DESIGN_RATIONALE.md`, `MODEL_REGISTRY.md`, `PROMPT_LIBRARY.md`, `EVALUATION.md`, `RECRUITER_WORKFLOWS.md`, and `RELEASE_NOTES.md` synchronized with implementation.
3. Establish production code foundation
   - Use `src/hireintel_ai/` as the production package.
   - Keep application entry points under `src/hireintel_ai/app/`.
   - Keep shared configuration under `src/hireintel_ai/core/`.
   - Keep shared typed contracts under `src/hireintel_ai/schemas/`.
   - Keep tests under `tests/unit/`, `tests/integration/`, and `tests/fixtures/`.

---

## Phase 1: Job Description Intelligence
1. Build JD ingestion
   - Support PDF, DOCX, Text input.
2. Extract requirements
   - Required/Preferred skills
   - Experience
   - Education
   - Certifications
   - Industry experience
   - Leadership requirements
   - Technology stack
3. Store structured JD output
   - Use as hiring policy input for scoring and matching.

---

## Phase 2: Recruiter Weight Configuration
1. Create recruiter-configurable scoring policy
   - Support weights for skills and categories.
2. Ensure explicit policy
   - Recruiters assign points.
   - Policy becomes deterministic evaluation rules.

---

## Phase 3: Resume Parsing ✅ Shipped 2026-06-19
1. Build resume ingestion and normalization
   - Support formats in `data/original`. ✅ (PDF + TXT)
   - Use parsing + OCR if needed. ✅ (`pdfplumber` → `pypdfium2` OCR → `pdf2image` fallback)
2. Extract structured candidate profiles
   - Name, contact, education, skills, certifications, languages, experience, projects, technologies, leadership indicators. ✅
3. Capture evidence
   - Link each extracted field to source resume text for explainability. ✅ (`raw_text` + `sections[].start/end` char spans; `candidate_id` SHA1 of source path)

**Artifacts:**
- 721 profile JSONs in `data/processed/<role>/`.
- `src/resume_parsing/{parser, ocr, batch_parse}.py`.
- `tests/unit/test_resume_parser.py` — passing.

---

## Phase 4: Candidate Evaluation Engine ✅ Shipped 2026-06-19

Per `WORKING_LOGIC.md` "Fundamental Rule": the platform ships **one**
deterministic scorer. The legacy keyword / semantic / hybrid triad was retired
the same day.

1. Implement deterministic scoring
   - Use recruiter weights + `expected_years` + structured profiles. ✅ (`graded_scorer.py`)
2. Produce evidence-backed scoring
   - Score value ✅
   - Supporting evidence ✅ (matched section, snippet, years detected)
   - Resume source snippets ✅
3. Avoid black-box ranking
   - LLMs support explanation only — never scoring. ✅
   - Final scores must be auditable and reproducible. ✅

**Single canonical scorer ships:**

| File | Output folder | Purpose |
|---|---|---|
| `src/scoring/graded_scorer.py` | `data/scores/graded/` | Single deterministic ranking signal per `WORKING_LOGIC.md` |

**Legacy triad (`keyword` / `semantic` / `hybrid`) retired 2026-06-19.** Passing
the legacy strategy names to `batch_score` / `compare_two` prints a
deprecation warning and forwards to `graded`.

**Batch CLI:** `python -m src.scoring.batch_score --role <Role>` → `data/scores/graded/<Role>_ranked.json` (ranked, 0-100 normalized, per-item evidence included).
**Per-candidate report:** `python scripts/evaluate_one.py --candidate <id> --role <Role>`.
**Comparison view:** `python scripts/compare_scores.py --role <Role> --top 10` shows the canonical graded ranking + per-candidate strengths and gaps.

---

## Phase 4.5: Clarification Loop + Quality Tiers ⬜ Planned

Closes the largest gaps in `WORKING_LOGIC.md` between shipped code and the
canonical spec.

1. **JD clarification loop** (Green / Yellow / Red)
   - Auto-classify each extracted requirement.
   - Auto-generate follow-up questions for Yellow items.
   - Hard-block the scoring policy until all items are Green.
   - Persist `clarifications.json` next to the role's weight config.
2. **Per-item `expected_years` in the recruiter UI**
   - Surface as a per-item field next to `importance`.
   - Validate that every Green item has either an explicit or default value.
3. **Quality-based evaluation**
   - Tier dictionary for institutions (IIT / NIT / Tier-1 Private / Regional).
   - Tier dictionary for certification providers (AWS / Microsoft / Google / Unknown).
   - `graded_scorer` consumes the tiers when computing education / certification scores.
4. **Resume cleaning pipeline**
   - Dedicated step between "raw text" and "structured profile" that strips headers, footers, template noise, decorative elements, and duplicate content.
5. **Candidate Intelligence Report artifact**
   - Aggregate `graded_scorer` per-item evidence into a single `data/processed/<role>/<id>_intelligence_report.json` with sections for Skills, Experience, Education, Certifications, Projects, Objective Scores, and Evidence Sources.

---

## Phase 5: Candidate Ranking & Comparison ✅ Shipped 2026-06-19
1. Build candidate comparison engine
   - Load two candidates' profiles and scores ✅
   - Diff the two side by side ✅ (matched components, top strengths)
   - Generate recruiter-friendly "Why A ranked above B" narrative ✅
2. Produce determinis side-by-side comparison tables
   - Score values ✅
   - Matched requirement counts ✅
   - Component breakdowns ✅
3. Avoid LLM-driven final rankings (LLM supports explanation only)
   - Scores computed by deterministic engine ✅

**Artifacts:**
- `scripts/compare_two.py` — CLI: `python scripts/compare_two.py --candidate-a <id_a> --candidate-b <id_b> --role <R> --strategy hybrid`
- `tests/integration/test_candidate_comparison.py` — 6 integration tests passing.

**Example output:**
```
Hybrid Score:           58.39        vs 37.07
Matched Requirements:   10           vs 4
Top Strengths:          Requirements Gathering, Stakeholder Management, Process Mapping
Why A ranked above B:   [SCORE] BUSINESS ANALYST RESUME ranked HIGHER by 21.3 points.
                        [MATCH] Matched 10 requirements vs 4 for John Wood.
```

---

## Phase 6: Resume Chat / RAG 🟡 Mostly built, CLI pending
1. Implement chunking strategy
   - Document-aware chunking by section. ✅ (`src/rag/chunker.py`)
2. Build embedding and retrieval pipeline
   - Embedding model: `sentence-transformers/all-MiniLM-L6-v2` ✅
   - Vector store: in-memory numpy (`data/embeddings/index.npz`) ✅
   - Cosine retrieval: ✅
   - Documented in `AI_DESIGN_RATIONALE.md` and `MODEL_REGISTRY.md`. ✅
3. Build recruiter-facing chat CLI
   - `scripts/resume_chat.py --candidate <id> --question "..." --role <Role>` — CLI. ⬜
   - Streamlit chat UI. ⬜
4. Ensure grounded conversational answers
   - LLM service via OpenRouter (`src/hireintel_ai/llm/service.py`) ✅
   - Strict-grounding prompt (see `docs/PROMPT_LIBRARY.md` RESUME-CHAT-001). ✅
   - "Information not found in candidate documents." fallback. ✅
   - Cite retrieved resume content. 🟡 (citation pattern in code; recruiter UI not yet built)

---

## Phase 7: Evaluation & validation
1. Define metrics
   - Resume parsing: precision, recall, F1
   - Retrieval: Recall@K, Precision@K, MRR, nDCG
   - Generation: faithfulness, groundedness, relevancy
   - RAG: context recall, context precision
   - Ranking: Top-K accuracy, recruiter agreement
   - Hallucination: unsupported statements, hallucination rate
   - Business: screening efficiency, time saved, satisfaction
2. Validate and iterate
   - Measure performance
   - Refine parsing, retrieval, scoring

---

## Phase 8: Technology & deployment
1. Assemble stack
   - Backend: Python, FastAPI
   - Frontend: Streamlit
   - NLP: spaCy, NLTK, regex
   - LLM/embeddings: chosen models
   - Vector DB: chosen engine
2. Document implementation
   - Keep architecture and decision docs updated.
   - Add release notes for feature completion and bug fixes.

---

## Recommended execution order
1. Define documentation and architecture
2. Establish production package structure, configuration, schemas, and test layout
3. Build JD extraction + clarification loop
4. Build weight configuration (weights + expected_years)
5. Build resume parsing + cleaning
6. Build scoring engine (single canonical scorer)
7. Build ranking/comparison
8. **Phase 4.5: clarification loop, per-item expected_years UI, quality tiers, Candidate Intelligence Report**
9. Add retrieval, then grounded RAG/chat (Phase 6)
10. Evaluate, harden, deploy, and document (Phases 7 + 8)
