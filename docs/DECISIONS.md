# Decisions

## Overview

This document records significant product, architecture, AI, data, and implementation decisions.

Every major architecture or AI change must be documented here before implementation, then reflected in the affected source-of-truth documents.

---

## Decision Log

| ID | Date | Decision | Status | Related Docs |
| --- | --- | --- | --- | --- |
| DEC-001 | 2026-06-19 | Use documentation-first development with `docs/` as source of truth. | Accepted | `AGENTS.md`, `PROJECT_OVERVIEW.md` |
| DEC-002 | 2026-06-19 | Use deterministic scoring for final candidate scores and rankings. | Accepted | `AI_ARCHITECTURE.md`, `AI_DESIGN_RATIONALE.md`, `MODEL_REGISTRY.md` |
| DEC-003 | 2026-06-19 | Use document-aware chunking as the primary resume chunking strategy. | Accepted | `AI_ARCHITECTURE.md`, `AI_DESIGN_RATIONALE.md`, `MODEL_REGISTRY.md` |
| DEC-004 | 2026-06-19 | Use Qdrant as the proposed vector database. | Superseded | `AI_DESIGN_RATIONALE.md`, `MODEL_REGISTRY.md` |
| DEC-005 | 2026-06-19 | Use BGE-M3 as the proposed primary embedding model. | Superseded | `AI_DESIGN_RATIONALE.md`, `MODEL_REGISTRY.md` |
| DEC-006 | 2026-06-19 | Use an in-memory numpy vector index until scale demands a hosted vector DB. | Accepted | `MODEL_REGISTRY.md`, `AI_ARCHITECTURE.md` |
| DEC-007 | 2026-06-19 | Use `sentence-transformers/all-MiniLM-L6-v2` as the active embedding model (CPU-runnable, no API key, PII-safe). | Accepted | `AI_DESIGN_RATIONALE.md`, `MODEL_REGISTRY.md` |
| DEC-008 | 2026-06-19 | Ship three independent scoring strategies (keyword, semantic, hybrid) runnable side by side; default production strategy is hybrid with `α = 0.5`. | Accepted | `AI_ARCHITECTURE.md`, `AI_DESIGN_RATIONALE.md`, `MODEL_REGISTRY.md` |
| DEC-009 | 2026-06-19 | Use `pypdfium2` (no Poppler required) as the primary OCR fallback renderer for image-only PDFs. | Accepted | `AI_ARCHITECTURE.md`, `MODEL_REGISTRY.md` |

---

## Decision Template

```text
## DEC-XXX: Title

Date:
Status:

Context:

Decision:

Alternatives Considered:

Consequences:

Related Documents:
```

---

## DEC-006: In-memory numpy vector index (defer Qdrant)

**Date:** 2026-06-19
**Status:** Accepted

**Context:** We needed a vector store for ~4k chunks to enable retrieval for both JD matching and semantic scoring. `Qdrant` was previously proposed but introduces a separate service to deploy, monitor, and secure.

**Decision:** Persist chunk vectors to `data/embeddings/index.npz` (compressed numpy). Load on first retrieval. Keep Qdrant as the planned upgrade when scale exceeds single-machine memory or we need hosted multi-user concurrency.

**Alternatives Considered:**
- **Qdrant:** Best long-term option, but operational overhead before we have users.
- **ChromaDB:** Lighter than Qdrant but still a service.
- **FAISS:** Fast but poor metadata filtering.

**Consequences:**
- Zero infra dependencies to run locally / on a single machine.
- 6 MB on disk for 4k chunks × 384 dims; trivial to load.
- Trivial to swap to Qdrant later — `src/rag/index.py.VectorIndex` is the only abstraction to replace.

**Related Documents:** `MODEL_REGISTRY.md`, `AI_ARCHITECTURE.md`

---

## DEC-007: MiniLM-L6-v2 as primary embedding model (defer BGE-M3)

**Date:** 2026-06-19
**Status:** Accepted

**Context:** BGE-M3 was previously proposed. After scoping the v1 system to English-only JDs and resumes with ~4k chunks, we evaluated latency, cost, and PII constraints.

**Decision:** Use `sentence-transformers/all-MiniLM-L6-v2` (384-dim, ~80 MB, CPU-runnable, no API key) as the active embedding model. Keep BGE-M3 as the planned upgrade path for multilingual candidates.

**Alternatives Considered:**
- **BGE-M3:** Multilingual, larger model.
- **OpenAI `text-embedding-3-small`:** Highest quality, but per-token API cost and PII egress.
- **E5 / Nomic:** Comparable to MiniLM but with weaker English retrieval.

**Consequences:**
- Fully offline, no API key, no candidate data egress — strong PII story.
- One embedding call per (JD bullet × candidate) at scoring time → fast enough for our scale.
- Model swap is isolated to `src/rag/embeddings.DEFAULT_MODEL_NAME`.

**Related Documents:** `AI_DESIGN_RATIONALE.md`, `MODEL_REGISTRY.md`

---

## DEC-008: Three scoring strategies (keyword, semantic, hybrid) with `α = 0.5` default

**Date:** 2026-06-19
**Status:** Accepted

**Context:** Keyword-only scoring is fast and auditable but misses synonyms. LLM-direct ranking is prohibited by `AGENTS.md`. We needed a way to add synonym awareness without giving up explainability or reproducibility.

**Decision:** Ship three independent scorers, each writing to its own output folder:
- `keyword_scorer.py` — deterministic binary match against recruiter weights.
- `semantic_scorer.py` — JD-bullet cosine vs candidate's chunks (mean × 100).
- `hybrid_scorer.py` — `α × keyword + (1-α) × semantic`, default `α = 0.5`.

Recruiters select the strategy per role. `scripts/compare_scores.py` shows rank deltas across strategies.

**Alternatives Considered:**
- Single keyword scorer (insufficient synonym coverage).
- Single semantic scorer (less explainable, recruiter loses direct weight control).
- LLM-direct ranking (rejected by `AGENTS.md`).
- Per-JD α (more complex; deferred to future iteration).

**Consequences:**
- Same JSON shape across all three strategies → single UI renderer.
- Each score component still links to `chunk_id` + `source_file` for evidence.
- Recruiters get three ranking signals per role and can compare them directly.
- Storage: 3 ranked JSONs per role (~50 KB each); negligible.

**Related Documents:** `AI_ARCHITECTURE.md`, `AI_DESIGN_RATIONALE.md`, `MODEL_REGISTRY.md`

---

## DEC-009: pypdfium2 as primary OCR fallback renderer

**Date:** 2026-06-19
**Status:** Accepted

**Context:** Image-only PDFs in `data/original/WebDesigning/` failed to extract text via `pdfplumber`. OCR fallback via `pdf2image` requires Poppler to be installed on the host — fragile for local dev.

**Decision:** Use `pypdfium2` (which bundles PDFium) as the primary PDF→image renderer for the OCR fallback. Keep `pdf2image` as a secondary fallback when `pypdfium2` is unavailable.

**Alternatives Considered:**
- `pdf2image` only (requires Poppler install).
- `PyMuPDF` (mupdf-based; similar trade-offs to pdfium but heavier dependency).

**Consequences:**
- Zero host-system dependencies for OCR fallback in most cases.
- Same `pytesseract` text extraction layer regardless of renderer.
- Documented in `src/resume_parsing/ocr.py`.

**Related Documents:** `AI_ARCHITECTURE.md`, `MODEL_REGISTRY.md`


