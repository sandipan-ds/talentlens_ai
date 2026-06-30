# Current Progress vs `WORKING_LOGIC.md`

This document maps every step of the canonical spec
[`WORKING_LOGIC.md`](WORKING_LOGIC.md) to its implementation status as of
2026-06-19. Use it as the single source of truth for "what's done vs what's
left" when planning the next session.

**Legend:** ✅ Shipped · 🟡 Partially shipped / scaffolded · ⬜ Planned

---

## Foundational Rules

| Spec rule | Status | Where |
|---|---|---|
| System is not a generic ATS / keyword matcher / RAG chatbot | ✅ | Architecture, scoring |
| Recruiter-controlled weights (0–10) | ✅ | `data/Job descriptions/<role>/<role>_WeightConfig_filled.json` |
| Recruiter-controlled `expected_years` per item | 🟡 | Default 10 in `graded_scorer.DEFAULT_EXPECTED_YEARS`; per-item field not yet exposed in UI |
| Weight normalization to 0–100 | ✅ | `scale_factor = 100 / max_score` in `src/scoring/graded_scorer.py` |
| Reproducible, auditable, explainable rankings | ✅ | `graded_scorer.evaluate_candidate` |
| LLM explains, never scores | ✅ | `src/hireintel_ai/llm/service.py`; `scripts/compare_two.py` |
| Ask for clarification, don't assume | ⬜ | No clarification loop yet |
| Document-Aware Chunking is the default | ✅ | `src/rag/chunker.py` |

---

## JD Pipeline (Steps 0–5 of `WORKING_LOGIC.md`)

| Step | Spec | Status | Where |
|---|---|---|---|
| JD validation & clarification | Reject ambiguous JDs | ⬜ | — |
| Green / Yellow / Red requirement classification | Tag each requirement | ⬜ | — |
| Recruiter follow-up questions for Yellow items | Ask, don't assume | ⬜ | — |
| Red items block scoring until clarified | Hard gate | ⬜ | — |
| Degree equivalence table per role | Confirm acceptable alternatives | ⬜ | — |
| Per-skill expected years (ask when missing) | "Expected Tableau experience?" | ⬜ | — |
| Recruiter weight assignment 0–10 | Done via form | ✅ | `src/ui/recruiter_weight_config.py` |
| Weight normalization to 100 | `scale_factor = 100 / max_score` | ✅ | `src/scoring/graded_scorer.py` |

---

## Resume Pipeline

| Step | Spec | Status | Where |
|---|---|---|---|
| Resume Upload (PDF, DOCX, text) | Multiple formats | ✅ | `src/resume_parsing/parser.py`, OCR fallback via `pypdfium2` |
| Resume Cleaning (headers, footers, templates, noise, duplicates) | Strip noise | 🟡 | Implicit via section parsing; no dedicated cleaning step |
| Document-Aware Chunking | One chunk per experience/education/project entry | ✅ | `src/rag/chunker.py` |
| Header Normalization | Synonym lookup + fallback classification → 7 canonical sections | ⬜ | Not yet implemented — current parser uses heading-anchored detection |
| Chunk Metadata Schema | `calculated_duration_months`, `experience_type`, `skills_asserted`, `parent_structure` | ⬜ | Not yet implemented — current metadata is simpler (title, company, dates, location) |
| Structured Candidate Profile Extraction | Deterministic extraction of degrees, certs, total exp, companies, dates | 🟡 | Partially handled by parser; not separated as its own deterministic record |
| Evidence Extraction | Linked to source text | ✅ | `char_span` in chunk records |
| Candidate Intelligence Report | Aggregated Skills + Experience + Education + Certs + Projects + Objective Scores + Evidence | 🟡 | Per-item evidence exists in `graded_scorer`; no aggregated "report" file |

---

## Candidate Evaluation (Steps 6–11 of `WORKING_LOGIC.md`)

| Step | Spec | Status | Where |
|---|---|---|---|
| Skill Presence | Boolean match | ✅ | `graded_scorer._search_profile` |
| Skill Years of Experience (total) | Years near alias | ✅ | `graded_scorer._detect_years_in_text` |
| Skill Depth (rubric-bound LLM) | LLM judge against recruiter rubric | ⬜ | Not yet implemented — code-only synonym match is the current fallback |
| Relevant Experience (rubric-bound LLM) | Same-role / industry / leadership via LLM judge | ⬜ | Not yet implemented — synonym+regex is the current fallback |
| Same Role Experience | Role-specific | 🟡 | Alias match only (`business analyst`, `business analysis`); rubric-bound LLM scoring planned |
| Education (Degree Match) | Binary or tier-based | 🟡 | Binary only; tier-based planned |
| Education (Institution Quality) | IIT / NIT / Tier-1 / regional | ⬜ | — |
| Certifications (Match) | Name match | ✅ | Synonym dict |
| Certifications (Provider Reputation) | AWS / Microsoft / Google vs unknown | ⬜ | — |
| Projects (rubric-bound LLM) | Relevance + depth via LLM judge | ⬜ | Not yet implemented — mention-only heuristic is the current fallback |
| Location | Location match | 🟡 | Alias exists in profile but no scorer rule yet |
| Languages | Language match | 🟡 | Same |
| Communication Quality | Resume structure signals | ⬜ | Documented in `AI_ARCHITECTURE.md`, no rule |
| Resume Organization | Same | ⬜ | Documented in `AI_ARCHITECTURE.md`, no rule |
| Section-Routed Evidence Retrieval | Exact label match on canonical sections | ⬜ | Not yet implemented — current scorer uses structured-profile search, not section-routed chunks |
| Header Normalization | Synonym lookup + fallback classification | ⬜ | Not yet implemented — current parser uses heading-anchored detection |
| Per-item raw score = `min(importance, years / expected × importance)` | Years-proportional (code-only mode) | ✅ | `graded_scorer.evaluate_candidate` |
| Partial credit (mentioned, no years) | `importance × 0.3` | ✅ | `graded_scorer.evaluate_candidate` |
| Total normalized to 100 | `total_raw × scale_factor` | ✅ | `graded_scorer.evaluate_candidate` |
| Per-item evidence (section, snippet, years, reason) | Mandatory | ✅ | `ItemEvaluation` dataclass |
| Cached rubric reasoning for score explanation | Store sub-scores + cited evidence at scoring time | ⬜ | Not yet implemented |
| Score Explanation Using RAG | Retrieve → ground → narrate | ⬜ | LLM service scaffolded (`hireintel_ai/llm/service.py`) but only candidate-comparison narrative exists; no per-item score explanation method implemented |

---

## Candidate Ranking

| Rule | Status | Where |
|---|---|---|
| Sort by deterministic total | ✅ | `batch_score._ranked_rows` |
| Tie-breaks by matched item count | 🟡 | Documented; rule not yet in code |
| LLM never ranks | ✅ | Enforced by design |
| Cosine similarity is a supporting signal only | 🟡 | Vector index exists (`data/embeddings/index.npz`); recruiter-facing cosine match UI not built |

---

## Resume Chat

| Step | Status |
|---|---|
| Document-Aware Chunking for retrieval | ✅ |
| RAG-grounded answers | ⬜ (LLM service scaffolded; no resume-chat method implemented; `scripts/resume_chat.py` CLI not built) |
| Strict grounding prompt (no hallucination) | ⬜ (prompt spec exists in `PROMPT_LIBRARY.md` RESUME-CHAT-001; not implemented in code) |
| "Information not found in candidate documents." fallback | ⬜ (string appears only in docs; not in any `.py` file) |

---

## Candidate Comparison

| Step | Status | Where |
|---|---|---|
| Side-by-side comparison | ✅ | `scripts/compare_two.py` |
| Evidence-backed "Why A above B" | ✅ | Deterministic score deltas + component breakdown |
| LLM explanation grounded in retrieved content | 🟡 | `LlmService.explain_candidate_score` generates a comparison narrative when LLM is configured; not grounded in retrieved resume content (uses scorer output, not RAG) |

---

## Hiring Recommendations

| Step | Status |
|---|---|
| Generate evidence-backed recommendation text | ⬜ (planned for Phase 8) |

---

## Quality-Based Evaluation (Spec §"Quality-Based Evaluation")

| Tier | Status |
|---|---|
| Institution quality tiers | ⬜ (planned) |
| Certification provider reputation | ⬜ (planned) |
| Recruiter-controlled tier definitions | ⬜ (planned) |

---

## Evaluation & Validation (Phase 7)

| Metric family | Status |
|---|---|
| Resume Parsing: Precision / Recall / F1 | ⬜ |
| Retrieval: Recall@K / Precision@K / MRR / nDCG | ⬜ |
| Generation: Faithfulness / Groundedness / Answer Relevancy | ⬜ |
| Ranking: Top-K Accuracy / Recruiter Agreement / Ranking Accuracy | ⬜ |
| Hallucination Rate | ⬜ |
| Business: Screening Efficiency / Recruiter Time Saved | ⬜ |

---

## Next Recommended Unit of Work

**Phase 4.5 — Clarification loop + Quality tiers** (closes the biggest spec gaps):

1. Per-item `expected_years` field in weight-config (UI-exposed).
2. `clarifications.json` per role listing Green / Yellow / Red items and auto-generated questions.
3. Recruiter UI to answer questions before scoring policy is locked.
4. Tier dictionary for institutions and certification providers; scorer consumes it.
5. Aggregate `candidate_intelligence_report.json` from `graded_scorer` output.

This unblocks **Phase 7 — Evaluation** (we can finally ground-truth the scorer against recruiter-confirmed expectations) and **Phase 8 — Deployment** (the UI has a complete data flow to wire up).

---

## How this doc relates to others

- `WORKING_LOGIC.md` is the **canonical spec** (the "what should it do").
- This doc is the **status snapshot** (the "what does it do today").
- `IMPLEMENTATION_ROADMAP.md` is the **execution plan** (the "what do we build next").
- `ARCHITECTURE_CHANGELOG.md` is the **history** (the "what changed and when").