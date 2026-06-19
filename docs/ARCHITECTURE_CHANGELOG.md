# Architecture Changelog

## Overview

This document records architecture changes that affect system structure, runtime behavior, AI workflows, storage, APIs, or deployment.

---

## 2026-06-19

### Added
- Established modular service-oriented architecture in `SYSTEM_ARCHITECTURE.md`.
- Established AI workflow architecture in `AI_ARCHITECTURE.md`.
- Established AI design rationale for chunking, embeddings, vector database, LLM usage, scoring, retrieval, RAG grounding, and evaluation.
- Added required governance docs for decisions, model registry, prompt library, evaluation, recruiter workflows, release notes, troubleshooting, and environment notes.
- Added production package foundation under `src/hireintel_ai/` with application entry points, shared config, schemas, ingestion, JD, resume, scoring, ranking, RAG, LLM, storage, and evaluation modules.
- Added test foundation under `tests/unit/`, `tests/integration/`, and `tests/fixtures/`.

### Changed
- Updated `AGENTS.md` architecture compliance references from missing legacy files to current source-of-truth docs.
- Updated the implementation roadmap to include production code foundation before feature implementation.
- Standardized the public product and production package naming on `HireIntel AI` / `hireintel_ai`.

### Risks
- The workspace folder is still named `talentlens_ai`, but product-facing docs and production package names now use `HireIntel AI` / `hireintel_ai`.
