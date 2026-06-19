# Recruiter Workflows

## Overview

This document describes how recruiters interact with HireIntel AI across job setup, resume processing, candidate evaluation, ranking, comparison, chat, and hiring recommendations.

---

## Workflow 1: Job Description Upload

1. Recruiter creates or selects a job.
2. Recruiter uploads a job description as PDF, DOCX, or text.
3. The platform validates the file and stores the original document.
4. The job description is sent for requirement extraction.

---

## Workflow 2: Requirement Extraction

1. The parser extracts structured hiring requirements.
2. Extracted requirements include required skills, preferred skills, experience, education, certifications, industry background, and technology stack.
3. Each requirement should retain supporting evidence from the job description.
4. Recruiter reviews and corrects extracted requirements before scoring policy creation.

---

## Workflow 3: Recruiter Weight Configuration

1. The platform presents extracted requirements to the recruiter.
2. Recruiter assigns weights based on hiring priorities.
3. The platform validates that weights are non-negative and sum to the required total.
4. The finalized scoring policy is stored and applied consistently to all candidates for the job.

---

## Workflow 4: Resume Upload

1. Recruiter uploads one or more candidate resumes.
2. The platform validates supported file types.
3. Original files are stored in object storage.
4. Parsing jobs are queued for asynchronous processing.

---

## Workflow 5: Resume Parsing

1. Resume text is extracted from PDF, DOCX, text, or OCR when needed.
2. The parser extracts structured candidate profile fields.
3. Evidence references are attached to extracted fields where possible.
4. Structured profiles are stored for scoring, ranking, comparison, and RAG.

---

## Workflow 6: Candidate Evaluation

1. The deterministic scoring engine loads the scoring policy and candidate profile.
2. Each requirement is evaluated against extracted resume evidence.
3. The platform produces score values, explanations, evidence snippets, and score breakdowns.
4. LLMs may explain results but must not directly calculate final rankings.

---

## Workflow 7: Candidate Ranking

1. The platform aggregates candidate evaluation scores.
2. Candidates are sorted by deterministic total score.
3. Tie breakers prioritize objective score before subjective score.
4. Recruiters view ranked candidates with score explanations.

---

## Workflow 8: Candidate Comparison

1. Recruiter selects candidates or asks a comparison question.
2. The system retrieves structured profile evidence.
3. The response compares candidates using grounded evidence.
4. Claims must cite candidate profile fields or resume sections.

---

## Workflow 9: Resume Chat

1. Recruiter asks a question about a candidate or group of candidates.
2. The RAG pipeline retrieves relevant resume chunks.
3. The LLM answers only from retrieved evidence.
4. If evidence is missing, the response is: "Information not found in candidate documents."

---

## Workflow 10: Hiring Recommendation

1. The platform combines ranked candidates, evaluation reports, and recruiter policy.
2. The recommendation engine generates an evidence-backed recommendation.
3. The recommendation must not contradict deterministic rankings.
4. Recruiters receive strengths, gaps, and source-backed justification.

