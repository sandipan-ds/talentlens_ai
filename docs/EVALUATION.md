# Evaluation

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

## Candidate Ranking Evaluation

**Goal:** Measure whether deterministic ranking aligns with recruiter-defined scoring policies and expert review.

**Metrics:**
- top-k accuracy
- recruiter agreement
- ranking accuracy
- tie-break correctness
- score reproducibility

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

