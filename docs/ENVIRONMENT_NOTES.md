# Environment Notes

## Overview

This document records environment and setup findings for HireIntel AI.

Use this document for Python installation issues, dependency conflicts, IDE issues, build failures, runtime configuration issues, local service setup, and OCR/runtime dependencies.

---

## Current Environment Observations

**Date:** 2026-06-19

**Environment:**
- Windows development workspace
- Python project with Streamlit, FastAPI, OCR, PDF parsing, and AI dependencies

**Notes:**
- OCR utilities depend on `pytesseract`, which requires the Tesseract OCR executable to be installed separately on the machine.
- Resume data may contain PII and should remain outside commits.
- `.venv/`, `data/`, `.history/`, `.checkpoints/`, and local cache directories should remain ignored.
- `docs/` must remain tracked because documentation is part of implementation governance.
- `pytest` currently passes, but local `.pytest_cache/` may emit a Windows cache warning if stale cache artifacts conflict with pytest writes.

**Prevention Strategy:**
- Add `.env.example` before introducing runtime configuration.
- Document external binaries such as Tesseract in setup instructions.
- Avoid committing raw candidate resumes or generated processing artifacts.
- Clear local pytest cache if cache warnings become noisy.
