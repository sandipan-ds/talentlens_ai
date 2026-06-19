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
