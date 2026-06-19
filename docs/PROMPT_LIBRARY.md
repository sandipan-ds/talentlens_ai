# Prompt Library

## Overview

This document stores production prompt specifications for HireIntel AI.

Each production prompt must include a prompt ID, purpose, inputs, outputs, constraints, known limitations, and version history. Prompt changes must be versioned because prompt behavior affects parsing quality, evidence grounding, and recruiter-facing explanations.

---

## Prompt Index

| Prompt ID | Purpose | Status |
| --- | --- | --- |
| JD-EXTRACT-001 | Extract structured hiring requirements from a job description | Planned |
| RESUME-PARSE-001 | Extract a structured candidate profile from resume content | Planned |
| CANDIDATE-SUMMARY-001 | Generate an evidence-based recruiter summary | Planned |
| CANDIDATE-COMPARE-001 | Compare candidates using structured evidence | Planned |
| RESUME-CHAT-001 | Answer recruiter questions using retrieved resume chunks | Planned |
| HIRING-RECOMMENDATION-001 | Generate evidence-backed hiring recommendation text | Planned |

---

## JD-EXTRACT-001

**Purpose:** Extract role requirements from a job description.

**Inputs:**
- Raw job description text
- Optional role title
- Optional employer-provided constraints

**Outputs:**
- Required skills
- Preferred skills
- experience requirements
- education requirements
- certifications
- industry requirements
- leadership requirements
- technology stack

**Constraints:**
- Do not infer requirements that are not present in the JD.
- Separate required and preferred requirements.
- Preserve evidence snippets for each extracted requirement.

**Known Limitations:**
- Ambiguous job descriptions may require recruiter confirmation.

**Version History:**
- v0.1: Initial planned prompt specification.

---

## RESUME-PARSE-001

**Purpose:** Extract structured candidate profile information from resume text.

**Inputs:**
- Resume text
- Document metadata
- Optional section boundaries

**Outputs:**
- candidate identity fields
- contact fields
- education
- skills
- work experience
- projects
- certifications
- languages
- evidence references

**Constraints:**
- Do not invent missing fields.
- Preserve evidence for every extracted field where possible.
- Treat resume content as sensitive PII.

**Known Limitations:**
- OCR quality may affect extraction accuracy.

**Version History:**
- v0.1: Initial planned prompt specification.

---

## RESUME-CHAT-001

**Purpose:** Answer recruiter questions using retrieved resume content.

**Inputs:**
- Recruiter question
- Retrieved resume chunks
- Candidate metadata allowed for display

**Outputs:**
- Grounded answer
- Source section references
- Missing-information response when evidence is unavailable

**Constraints:**
- Answer only from retrieved content.
- If evidence is missing, respond: "Information not found in candidate documents."
- Do not speculate.

**Known Limitations:**
- Retrieval failures may cause valid resume information to be unavailable to the prompt.

**Version History:**
- v0.1: Initial planned prompt specification.

