# Evaluation

> **Source of truth for scoring, evaluation, and ranking:**
> [`WORKING_LOGIC.md`](WORKING_LOGIC.md). For "what is implemented today vs
> what's planned", see [`CURRENT_PROGRESS.md`](CURRENT_PROGRESS.md).

## Overview

This document defines how HireIntel AI will measure AI quality, scoring reliability, retrieval performance, hallucination risk, and business impact.

Evaluation is required before promoting AI behavior, model changes, prompt changes, scoring changes, or retrieval changes into production.

---

## Resume Parsing Evaluation

**Goal:** Measure whether unstructured resumes are converted into accurate structured candidate profiles.

**Metrics:**
- Precision
- Recall
- F1 score
- field-level extraction accuracy
- evidence-link coverage

**Target Fields:**
- candidate name
- contact information
- education
- skills
- certifications
- languages
- work experience
- projects
- technology stack
- leadership indicators

---

## Job Description Extraction Evaluation

**Goal:** Measure whether hiring requirements are extracted correctly from job descriptions.

**Metrics:**
- required skill precision and recall
- preferred skill precision and recall
- experience requirement accuracy
- education requirement accuracy
- requirement evidence coverage

---

## Retrieval Evaluation

**Goal:** Measure whether recruiter questions retrieve the right resume evidence.

**Metrics:**
- Recall@K
- Precision@K
- Mean Reciprocal Rank
- nDCG
- context recall
- context precision

---

## Generation Evaluation

**Goal:** Measure quality of summaries, comparisons, chat answers, and recommendation text.

**Metrics:**
- faithfulness
- groundedness
- answer relevancy
- completeness
- unsupported statement rate

---

## Candidate Scoring Evaluation (per-item, per `WORKING_LOGIC.md`)

**Goal:** Measure whether the deterministic scorer awards the correct per-item score for the correct reason.

### Code-Only Scoring Metrics

- **Skill Presence Precision/Recall** — does the scorer correctly mark a skill as present vs absent?
- **Skill Coverage Precision/Recall** — for JD items with N synonyms, does the scorer match all of them?
- **Years Detection MAE** — mean absolute error between `candidate_years` and ground-truth years.
- **Per-item Score Accuracy** — fraction of items where the awarded raw score equals the ground truth within ±0.5.
- **Evidence Section Precision** — fraction of matched items where the cited profile section is the most informative one.
- **Snippet Faithfulness** — fraction of snippets that contain the matched keyword (no fabricated text).
- **Score Reproducibility** — same inputs → same score, byte-for-byte.

### Rubric-Bound LLM Evidence Scoring Metrics

- **Rubric Adherence** — fraction of LLM sub-scores that fall within the rubric-defined point anchors (does the LLM score against the recruiter rubric, not its own internal scale?).
- **Extraction Completeness** — did the LLM extract all relevant evidence from the mapped section(s) before scoring? (Recall of evidence extraction.)
- **LLM Judge Consistency** — same evidence + same rubric → same sub-score across repeated calls (test-retest reliability).
- **Weight Blindness** — verify that the LLM never receives the requirement's weight during scoring (audit prompt construction).
- **No-Aggregation Compliance** — verify that the LLM never computes the final weighted contribution (audit prompt + output schema).
- **Double-Count Detection** — verify that overlapping experience (e.g. 6 years Python on cluster systems + 6 years managing recommendation projects) is not summed to 12 years.
- **Sub-score Calibration** — correlation between LLM sub-scores and recruiter-expert ground-truth sub-scores on a labeled dataset.

## Candidate Ranking Evaluation

**Goal:** Measure whether deterministic ranking aligns with recruiter-defined scoring policies and expert review.

**Metrics:**
- top-k accuracy
- recruiter agreement
- ranking accuracy
- tie-break correctness
- score reproducibility

**Ground truth:** for each role, hand-score the top-N candidates against the recruiter's locked scoring policy, then compare to the deterministic scorer's output.

---

## Hallucination Evaluation

**Goal:** Ensure recruiter-facing answers do not invent candidate information.

**Metrics:**
- hallucination rate
- unsupported statements
- missing-evidence handling accuracy

Expected missing-information response:

```text
Information not found in candidate documents.
```

---

## Business Evaluation

**Goal:** Measure whether the platform improves recruiting workflows.

**Metrics:**
- screening efficiency
- recruiter time saved
- recruiter satisfaction
- shortlisting accuracy
- explanation usefulness

---

## Evaluation Artifacts

Evaluation datasets and outputs should be stored under `data/processed/evaluation_results/` or a future secure evaluation storage path. Candidate PII must not be written to logs or public artifacts.

