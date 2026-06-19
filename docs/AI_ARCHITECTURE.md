# AI Architecture

## Overview

This document is the source of truth for all AI-related architecture in the HireIntel AI platform. It defines the end-to-end workflows, chunking strategies, embedding pipelines, retrieval mechanisms, and RAG-based interactions.

---

## 1. Resume Ingestion Workflow

**Purpose:** Accept and store resume files, triggering downstream parsing and embedding.

```text
[Recruiter Upload] -> [API Gateway] -> [Resume Service] -> [Object Storage]
                                         |
                                         v
                                   [Message Queue] -> [Parsing Worker]
```

**Steps:**
1. Recruiter uploads resume (PDF, DOCX, or plain text)
2. File is validated and stored in Object Storage
3. A parsing job is enqueued asynchronously
4. Parsing Worker picks up the job and triggers the Resume Parsing Workflow

---

## 2. Resume Parsing Workflow

**Purpose:** Extract structured candidate profiles from unstructured resumes.

```text
[Raw Resume] -> [Parser Engine] -> [Structured Profile] -> [Document Database]
                                      |
                                      v
                               [Embedding Service]
                                      |
                                      v
                               [Vector Database]
```

**Techniques Used:**
- Document parsing (PyPDF2, python-docx)
- NLP-based section segmentation
- LLM-based information extraction (GPT, Claude, Gemini)

**Extracted Fields:**
- Candidate Name
- Contact Information
- Education (degree, institution, year)
- Skills (technical and soft)
- Certifications
- Languages Known
- Work Experience (company, role, duration, responsibilities)
- Projects (title, description, technologies)
- Technology Stack
- Leadership Experience

**Output:** Structured JSON profile persisted in the Document Database.

---

## 3. Job Description (JD) Processing Workflow

**Purpose:** Analyze and extract structured hiring requirements from job descriptions.

```text
[JD Upload] -> [Parser Engine] -> [Structured Requirements] -> [Document Database]
```

**Extracted Information:**
- Required Skills
- Preferred Skills
- Required Experience (years, role type)
- Education Requirements
- Certifications
- Industry Experience
- Leadership Requirements
- Technology Stack
- Location / Remote preferences

**Output:** Structured JD object stored and linked to the employer's account.

---

## 4. Recruiter Weight Configuration Workflow

**Purpose:** Allow recruiters to define scoring priorities for a specific role.

```text
[Extracted JD Requirements] -> [Present to Recruiter] -> [Recruiter Assigns Weights]
                                                               |
                                                               v
                                                    [Scoring Policy Generated]
                                                               |
                                                               v
                                                    [Persist in Document Database]
```

**Components of a Scoring Policy:**
- Point-based or percentage-based weights for each requirement
- Objective vs. subjective metric weighting
- Custom scoring rules (e.g., bonus for product company experience)

**Validation:**
- Total weights must sum to 100%
- Weights must be non-negative
- Minimum one objective metric is required

---

## 5. Candidate Evaluation Workflow

**Purpose:** Evaluate each candidate against the recruiter's scoring policy using evidence from their resume.

The platform ships **three independent scoring strategies** that produce ranked candidate lists. Recruiters select the strategy per role; the comparison view (`scripts/compare_scores.py`) shows rank deltas across strategies.

```text
[Structured Profile] + [Scoring Policy] + [Resume Chunks] + [JD Bullets]
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
[Keyword Scorer]       [Semantic Scorer]      [Hybrid Scorer]
   keyword_scorer.py     semantic_scorer.py     hybrid_scorer.py
        │                     │                     │
        ▼                     ▼                     ▼
data/scores/keyword/  data/scores/semantic/  data/scores/hybrid/
```

**Evaluation Dimensions:**
- Skill Match / Skill Coverage
- Relevant Experience (same role, technology, industry)
- Product Company Experience
- Education Alignment
- Certification Alignment
- Project Relevance
- Language Capabilities
- Leadership Experience
- Communication Quality (subjective)
- Resume Organization (subjective)

### 5.1 Keyword Scorer (deterministic)

Per the scoring guide (`data/Job descriptions/<role>/<role>_ScoringGuide.md`), each candidate's score on a recruiter-weighted item is **binary**: either the candidate has evidence for that item (full `importance` points) or not (0). Special handling:

- **Years of experience**: parsed from experience entries (`dates` fields), spans merged.
- **Bachelor's degree**: detected from education entries (`BE/BTech or equivalent` accepts BBA, BS, BSc, etc.).
- **Keyword match**: per-item keyword list scanned across the candidate's full profile text.

The keyword scorer is auditable: every component links to a `chunk_id` + `source_file` so recruiters can click through to the original PDF.

### 5.2 Semantic Scorer (cosine)

Each JD bullet (line under `## Key Responsibilities`, `## Required Skills`, etc.) is embedded with the chunking model. For each candidate, the bullet is matched against the candidate's own chunks (candidate-scoped, not global). The candidate's score on a bullet = `max cosine(bullet, candidate.chunks)`. The candidate's overall semantic score = `mean(bullet_score) × 100`.

This scorer catches synonyms and paraphrases the keyword scorer misses (e.g. "ML" ↔ "machine learning", "led 12 workshops" ↔ "requirement elicitation workshops").

### 5.3 Hybrid Scorer (blended)

`final_score = α × keyword_score + (1 - α) × semantic_score`, default `α = 0.5` (CLI flag `--alpha`).

The hybrid ranks candidates that are robust across both strategies highest, while giving partial credit to candidates strong in one strategy but weak in the other. Both per-component breakdowns are preserved so recruiters see *why* a candidate scored what they did under each lens.

### 5.4 Output Contract

All three strategies return the same shape per candidate:

```json
{
  "candidate_id": "cand_xxx",
  "role_bucket": "BusinessAnalyst",
  "source_file": "...",
  "raw_score": ...,
  "max_score": ...,
  "normalized_score": ...,
  "components": [
    { "category": "...", "item_name": "...", "importance": ..., "matched": true,
      "matched_weight": ..., "chunk_id": "...", "snippet": "...", "source_file": "...", "notes": "..." }
  ]
}
```

Hybrid additionally includes `keyword_score`, `semantic_score`, `final_score`, `alpha`, and both component lists.

---

## 6. Candidate Ranking Workflow

**Purpose:** Rank candidates deterministically based on evaluation scores.

```text
[All Evaluation Reports] -> [Normalization] -> [Weighted Aggregation] -> [Ranked List]
```

**Key Rules:**
- LLM does NOT directly determine rankings
- Rankings are derived from the deterministic Scoring Engine
- Ties are broken by highest objective score
- Rankings are reproducible given the same inputs

**Output:** Sorted candidate list with per-dimension scores and explanations.

---

## 7. Candidate Comparison Workflow

**Purpose:** Enable side-by-side or question-driven comparison of shortlisted candidates.

```text
[Recruiter Query] -> [Query Analysis] -> [Retrieve Candidate Profiles] -> [LLM Comparison]
```

**Examples:**
- Who has more React experience?
- Compare leadership experience across candidates.
- Why is Candidate A ranked higher than Candidate B?

**Grounding Constraint:** All comparisons must cite evidence from structured resume fields.

---

## 8. Summarization Workflow

**Purpose:** Generate recruiter-friendly summaries of candidates.

```text
[Structured Profile] -> [Summarization Engine] -> [Natural Language Summary]
```

**Components:**
- Highlight key strengths aligned with job requirements
- Flag potential gaps or concerns
- Cite specific evidence for claims

---

## 9. Chunking Architecture

**Purpose:** Divide resumes into semantically meaningful chunks for retrieval without losing structural context.

**Primary Strategy: Document-Aware Chunking**

Chunks are created based on resume sections (one chunk per evidence unit):

| Section | Chunk granularity |
|---|---|
| `summary` | One chunk per summary block |
| `experience` | **One chunk per experience entry** (title + company + dates + location + bullets) |
| `education` | **One chunk per education entry** |
| `projects` | **One chunk per project** |
| `skills` | One chunk (joined comma list) |
| `certifications` | One chunk (joined list) |
| `languages` | One chunk (joined list) |
| Other free-text sections | One chunk; sub-split on `\n\n` with overlap if > 1200 chars |

Chunks are emitted as JSONL files at `data/chunks/<role_bucket>/<candidate_id>.jsonl`. Each record contains:

```json
{
  "chunk_id": "cand_xxx__experience__0",
  "candidate_id": "cand_xxx",
  "role_bucket": "BusinessAnalyst",
  "source_file": "...",
  "section": "experience",
  "chunk_index": 0,
  "text": "Senior Data Scientist @ Acme | 2020 - Present\n- bullet 1\n- bullet 2 ...",
  "char_span": [800, 1300],
  "metadata": { "title": "...", "company": "...", "dates": "...", "location": "...", "bullet_count": 5 }
}
```

The `char_span` references offsets into the profile's `raw_text`, so RAG answers can cite the exact substring.

**Sub-split rule:** any chunk longer than `MAX_CHUNK_CHARS = 1200` is split on paragraph boundaries (`\n\n`) with `SPLIT_OVERLAP_CHARS = 120` overlap, ensuring no chunk exceeds the embedding model's comfortable context.

**Chunk Metadata:**
- Section type (e.g. "experience", "education")
- Document hierarchy (parent section, chunk index within section)
- Stable `candidate_id` (sha1 of source file path, 12 hex chars)
- `char_span` into raw resume text (citation-ready)
- Per-section `metadata` (title, company, dates, etc. for experience)

---

## 10. Embedding Architecture

**Purpose:** Generate vector representations for resume chunks to enable semantic search.

**Pipeline:**
```text
[Resume Chunk] -> [Embedding Model] -> [Vector] -> [Vector Index]
```

**Embedding Models Used:**
- Primary: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, ~80 MB, CPU-runnable, no API key)
- Alternative / future: BGE-M3 (multilingual) — see `MODEL_REGISTRY.md` for upgrade path

**Processing:**
- Chunks are batched (batch size 64) for efficient inference
- Embeddings are L2-normalized so dot product == cosine similarity
- Vectors are persisted to `data/embeddings/index.npz` (compressed numpy)
- Chunk metadata is persisted to `data/embeddings/chunks.jsonl`
- Re-built on demand via `python -m src.rag.build_index`

---

## 11. Retrieval Architecture

**Purpose:** Retrieve the most relevant resume content in response to recruiter queries.

**Retrieval Strategy: Dense Cosine over In-Memory Vector Index**

```text
[Recruiter / JD Bullet] -> [Embed] -> [Cosine over data/embeddings/index.npz] -> [Top-K Chunks]
```

**Used in two contexts:**

1. **JD ↔ Resume matching** (`src/rag/jd_match.py`) — recruiter-facing top-K candidates per JD.
2. **Semantic scoring** (`src/scoring/semantic_scorer.py`) — JD bullet ↔ candidate's own chunks (candidate-scoped, see § 5.2).

**Configuration:**
- Top-K chunks retrieved: 5–10 (configurable per call)
- Similarity threshold: minimum cosine to count as a "match" (default 0.30, configurable)
- Optional `role_bucket` filter on retrieval

---

## 12. RAG Workflow

**Purpose:** Answer recruiter questions with grounded, resume-based information.

```text
[Recruiter Question] -> [Retrieval] -> [Context Assembly] -> [Prompt Construction] -> [LLM]
                                                                              |
                                                                              v
                                                                      [Grounded Answer]
```

**Prompt Construction:**
- System prompt: "You are a helpful recruiting assistant. Answer based ONLY on the provided context."
- User prompt includes: question + top-k retrieved chunks

**Constraints:**
- If no relevant chunk is found, respond: "Information not found in candidate documents."
- Never hallucinate or infer beyond the provided context
- Cite specific resume sections when applicable

---

## 13. Hiring Recommendation Workflow

**Purpose:** Generate transparent, evidence-based hiring recommendations.

```text
[Ranked Candidates] + [Evaluation Reports] -> [LLM Recommendation Engine] -> [Hiring Recommendation]
```

**Output Includes:**
- Recommended candidate(s) with ranking justification
- Key qualifications and potential concerns
- Comparison with other top candidates
- Explicit statement of evidence sources (e.g., "Based on 5 years of relevant experience...")

**Constraints:**
- Recommendations must not contradict the deterministic ranking
- All claims must be supported by extraction results
- Uncertainty must be clearly communicated

---

## 14. AI Component Interaction Summary

```text
                                ┌──────────────────────┐
                                │   Recruiter (UI)     │
                                └──────────┬───────────┘
                                           │
              ┌────────────┬───────────────┼───────────────┬────────────┐
              │            │               │               │            │
              ▼            ▼               ▼               ▼            ▼
        [JD Upload] [Weight Config]  [Resume Upload]  [Evaluations]  [Chat/Compare]
              │            │               │               │            │
              ▼            ▼               ▼               ▼            ▼
        [JD Parser]  [Policy Store]  [Resume Parser]  [Scoring Engine]  [RAG Engine]
              │            │               │               │            │
              ▼            ▼               ▼               ▼            ▼
        [Vector DB]  [Doc DB]       [Vector DB]    [Doc DB]       [Vector DB]
```

All AI workflows are modular, logged, and designed to be explainable and auditable.
