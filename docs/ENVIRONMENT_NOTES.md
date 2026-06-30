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
- **2026-06-19-PM:** `.venv` was missing `pydantic`, `pydantic-settings`, and `httpx` packages even though they are listed in `requirements.txt`. Fix: run `python -m pip install -r requirements.txt` inside the activated venv, or `python -m pip install pydantic pydantic-settings httpx` for the minimum required set. The graded per-item scorer (`scripts/evaluate_one.py`) and the LLM-powered explanations (`scripts/compare_two.py`) both require these packages.
- **2026-06-19-PM (Phase 4 cleanup):** The legacy `keyword_scorer.py`, `semantic_scorer.py`, `hybrid_scorer.py` modules were removed. The canonical scorer is `src/scoring/graded_scorer.py` (no extra dependencies beyond the standard library). The batch CLI (`python -m src.scoring.batch_score`) and the comparison CLI (`scripts/compare_two.py`) read from `data/scores/graded/`. If you previously had `data/scores/{keyword,semantic,hybrid}/` from an older run, those folders are no longer produced; rerun the batch CLI to regenerate the canonical output.
- **2026-06-19-PM (doc alignment):** `docs/WORKING_LOGIC.md` is now the canonical scoring/evaluation spec. `docs/CURRENT_PROGRESS.md` is the single status doc mapping every step of `WORKING_LOGIC.md` to ✅ / 🟡 / ⬜. All other docs defer to these two for scoring details.

**Prevention Strategy:**
- Add `.env.example` before introducing runtime configuration.
- Document external binaries such as Tesseract in setup instructions.
- Avoid committing raw candidate resumes or generated processing artifacts.
- Clear local pytest cache if cache warnings become noisy.
- Always sync `.venv` with `requirements.txt` after pulling new dependency declarations:
  ```powershell
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  ```
