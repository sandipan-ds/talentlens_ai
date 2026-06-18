# Implementation Roadmap

## Overview
This roadmap defines the step-by-step execution plan for HireIntel AI, aligned with `AGENTS.md` and `docs/PROJECT_OVERVIEW.md`.

---

## Phase 0: Foundation & alignment
1. Confirm repository structure
   - Ensure `/docs` exists and contains required docs.
   - Treat `/docs` as source of truth.
2. Establish documentation process
   - Keep `PROJECT_OVERVIEW.md`, `SYSTEM_ARCHITECTURE.md`, `AI_ARCHITECTURE.md`, `AI_DESIGN_RATIONALE.md`, `MODEL_REGISTRY.md`, `PROMPT_LIBRARY.md`, `EVALUATION.md`, `RECRUITER_WORKFLOWS.md`, and `RELEASE_NOTES.md` synchronized with implementation.

---

## Phase 1: Job Description Intelligence
1. Build JD ingestion
   - Support PDF, DOCX, Text input.
2. Extract requirements
   - Required/Preferred skills
   - Experience
   - Education
   - Certifications
   - Industry experience
   - Leadership requirements
   - Technology stack
3. Store structured JD output
   - Use as hiring policy input for scoring and matching.

---

## Phase 2: Recruiter Weight Configuration
1. Create recruiter-configurable scoring policy
   - Support weights for skills and categories.
2. Ensure explicit policy
   - Recruiters assign points.
   - Policy becomes deterministic evaluation rules.

---

## Phase 3: Resume Parsing
1. Build resume ingestion and normalization
   - Support formats in `data/original`.
   - Use parsing + OCR if needed.
2. Extract structured candidate profiles
   - Name, contact, education, skills, certifications, languages, experience, projects, technologies, leadership indicators.
3. Capture evidence
   - Link each extracted field to source resume text for explainability.

---

## Phase 4: Candidate Evaluation Engine
1. Implement deterministic scoring
   - Use recruiter weights + structured profiles.
2. Produce evidence-backed scoring
   - Score value
   - Supporting evidence
   - Resume source snippets
3. Avoid black-box ranking
   - LLMs support extraction/summarization only.
   - Final scores must be auditable and reproducible.

---

## Phase 5: Candidate Ranking & Comparison
1. Rank candidates
   - Based on structured scores and weights.
2. Build comparison engine
   - Support questions such as:
     - Strongest React experience
     - Longest similar-role tenure
     - Most relevant projects
     - Why A ranked above B
3. Generate recruiter-friendly summaries
   - Concise, evidence-based, requirement-aligned.

---

## Phase 6: Resume Chat / RAG
1. Implement chunking strategy
   - Document-aware chunking by section.
   - Optional semantic chunking for large sections.
2. Build embedding and retrieval pipeline
   - Select embedding model and vector store.
   - Document decisions in `AI_DESIGN_RATIONALE.md` and `MODEL_REGISTRY.md`.
3. Ensure grounded conversational answers
   - Cite retrieved resume content.
   - If missing, respond with: “Information not found in candidate documents.”

---

## Phase 7: Evaluation & validation
1. Define metrics
   - Resume parsing: precision, recall, F1
   - Retrieval: Recall@K, Precision@K, MRR, nDCG
   - Generation: faithfulness, groundedness, relevancy
   - RAG: context recall, context precision
   - Ranking: Top-K accuracy, recruiter agreement
   - Hallucination: unsupported statements, hallucination rate
   - Business: screening efficiency, time saved, satisfaction
2. Validate and iterate
   - Measure performance
   - Refine parsing, retrieval, scoring

---

## Phase 8: Technology & deployment
1. Assemble stack
   - Backend: Python, FastAPI
   - Frontend: Streamlit
   - NLP: spaCy, NLTK, regex
   - LLM/embeddings: chosen models
   - Vector DB: chosen engine
2. Document implementation
   - Keep architecture and decision docs updated.
   - Add release notes for feature completion and bug fixes.

---

## Recommended execution order
1. Define documentation and architecture
2. Build JD extraction
3. Build weight configuration
4. Build resume parsing
5. Build scoring engine
6. Build ranking/comparison
7. Add RAG/chat
8. Evaluate and refine
9. Deploy and document
