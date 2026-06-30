# Troubleshooting

## Overview

This document records debugging findings that should be reusable in future sessions.

Each entry should include problem description, symptoms, root cause, investigation process, solution, and prevention strategy.

---

## Known Issues

### Pytest cache warning on Windows

**Date:** 2026-06-19

**Problem:** Running `pytest` produced a cache warning while trying to write node IDs.

**Symptoms:**
- Tests passed.
- Pytest emitted `PytestCacheWarning` for `.pytest_cache\v\cache\nodeids`.

**Root Cause:**
- The local `.pytest_cache` path appears to have a stale file or directory conflict.

**Investigation Process:**
- Ran the full test suite after adding the production package foundation.
- Confirmed all tests passed despite the cache warning.

**Solution:**
- No code change required.
- The cache can be cleared locally if the warning becomes noisy.

**Prevention Strategy:**
- Keep `.pytest_cache/` ignored.
- Treat pytest cache artifacts as disposable local runtime state.

---

### Documentation ignored by Git

**Date:** 2026-06-19

**Problem:** The repository requires documentation to be maintained as part of implementation, but `.gitignore` contained `docs/`.

**Symptoms:**
- New required documentation files would not appear as untracked files.
- Documentation changes could be missed during commits.

**Root Cause:**
- `.gitignore` incorrectly ignored the `docs/` directory.

**Investigation Process:**
- Reviewed `AGENTS.md` documentation requirements.
- Reviewed `.gitignore`.
- Compared required docs with files present under `docs/`.

**Solution:**
- Removed `docs/` from `.gitignore`.
- Added missing required documentation files.

**Prevention Strategy:**
- Keep `docs/` tracked.
- Do not add source-of-truth documentation folders to `.gitignore`.

---

### Legacy scorer imports after Phase 4 cleanup

**Date:** 2026-06-19 (PM)

**Problem:** After retiring the legacy `keyword / semantic / hybrid` triad, any code that still imported from `src.scoring.keyword_scorer`, `src.scoring.semantic_scorer`, `src.scoring.hybrid_scorer`, `src.scoring.evidence`, or `src.scoring.evaluate` would fail with `ModuleNotFoundError`.

**Symptoms:**
- `ModuleNotFoundError: No module named 'src.scoring.keyword_scorer'` (or similar).
- `ImportError: cannot import name 'CandidateScore' from 'src.scoring.evaluate'`.

**Root Cause:**
- The legacy modules were removed as part of the Phase 4 cleanup (DEC-010). The canonical scorer is `src/scoring/graded_scorer.py`.

**Investigation Process:**
- Ran `grep_search` for `from src.scoring.(keyword|semantic|hybrid|evidence|evaluate)` across the source tree.
- Found 0 matches — all consumers had been migrated.

**Solution:**
- Replace any legacy import with the canonical scorer:
  ```python
  from src.scoring.graded_scorer import (
      evaluate_candidate, evaluate_role, render_report, load_weights,
  )
  ```
- The CLI accepts `--strategy keyword|semantic|hybrid` only as a deprecated alias that prints a `DeprecationWarning` and forwards to `graded`.

**Prevention Strategy:**
- The single canonical scorer is the only ranking signal. New code must use `graded_scorer`.
- If you need to add a new scoring strategy, extend `graded_scorer` (e.g. add a new synonym, a new section priority, or a new tier dictionary) rather than introducing a parallel scorer.
