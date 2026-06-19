# AI Design Rationale

## Overview

This document records the AI design decisions made in the HireIntel AI platform. Each decision includes alternatives considered, tradeoffs evaluated, final rationale, and future upgrade paths.

---

## 1. Chunking Strategy

### Decision
**Primary:** Document-Aware Chunking  
**Secondary:** Semantic Chunking within large sections

### Alternatives Considered
- **Recursive Chunking:** Fixed-size overlapping chunks regardless of document structure
- **Document-Aware Chunking:** Chunking based on resume sections (Education, Experience, Projects, etc.)
- **Semantic Chunking:** Splitting based on semantic boundaries using embeddings
- **Agentic Chunking:** Using an LLM agent to dynamically decide chunk boundaries

### Tradeoffs Evaluated

| Strategy | Structure Preservation | Retrieval Quality | Cost | Complexity |
|----------|------------------------|-------------------|------|------------|
| Recursive | Low | Medium | Low | Low |
| Document-Aware | High | High | Medium | Medium |
| Semantic | Medium | High | High | High |
| Agentic | Medium | Medium | Very High | Very High |

### Final Rationale
- Resumes have a well-defined, predictable structure (Education, Experience, Skills, etc.)
- Document-aware chunking preserves semantic coherence within each section
- Improves retrieval relevance since recruiters often query specific sections (e.g., "React experience")
- Avoids the high cost and latency of agentic or fully semantic approaches

### Future Upgrade Path
- Integrate semantic chunking within very large sections (e.g., resumes with 10+ years of experience)
- Evaluate hybrid approaches as embedding models improve

---

## 2. Embedding Model

### Decision
**Primary:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim, local, CPU-runnable)
**Alternative / upgrade:** BGE-M3 (multilingual)
**Fallback / future:** OpenAI `text-embedding-3-small`

### Alternatives Considered
- **all-MiniLM-L6-v2 (sentence-transformers):** Small (~80 MB), fast, strong English retrieval, runs on CPU
- **BGE-M3 (BAAI):** Multilingual, retrieval-optimized
- **E5 (Microsoft):** Sentence-level semantic similarity
- **Nomic Embed:** Open-source, recently released
- **OpenAI Embeddings:** Managed, high quality, but per-token API cost and data egress

### Tradeoffs Evaluated

| Model | Retrieval Quality | Cost | Latency | Multilingual | Open Source | Local Run |
|-------|-------------------|------|---------|--------------|-------------|-----------|
| MiniLM-L6-v2 | High | Free | Low (<200 chunks/sec on CPU) | No | Yes | Yes |
| BGE-M3 | High | Free | Medium | Yes | Yes | Yes |
| E5 | High | Free | Medium | Limited | Yes | Yes |
| Nomic | Medium | Free | Low | Yes | Yes | Yes |
| OpenAI | Very High | $$$ per 1M tokens | Low | Yes | No | No |

### Final Rationale
- The semantic scorer runs **per-candidate, per-JD-bullet**, so the embedding model is the hot path: latency and cost matter
- MiniLM-L6-v2 runs entirely on CPU and offline (no API key, no egress) — critical because resumes contain PII
- Quality on short English business text is well-validated (top of MTEB leaderboard for its size class)
- 384-dim vectors keep the in-memory index small (~6 MB for 4k chunks) — no external vector DB needed for the current scale

### Future Upgrade Path
- **BGE-M3** when we onboard multilingual candidates or non-English JDs
- **OpenAI text-embedding-3-small** if recruiters report recall@K issues and budget allows API egress
- Model swap is isolated to `src/rag/embeddings.DEFAULT_MODEL_NAME`; index must be rebuilt

---

## 3. Vector Database

### Decision
**Qdrant**

### Alternatives Considered
- **Qdrant:** Open-source, high-performance, supports filtering and hybrid search
- **ChromaDB:** Lightweight, easy to embed, developer-friendly
- **Pinecone:** Managed, scalable, but expensive for high-volume usage
- **FAISS:** Meta's library, very fast, but lacks native metadata filtering

### Tradeoffs Evaluated

| Database | Performance | Scalability | Metadata Filtering | Self-Hosted | Cost |
|----------|-------------|-------------|--------------------|-------------|------|
| Qdrant | High | High | Excellent | Yes | Free |
| ChromaDB | Medium | Medium | Good | Yes | Free |
| Pinecone | High | Very High | Good | No | High |
| FAISS | Very High | Medium | Poor | Yes | Free |

### Final Rationale
- Qdrant offers the best balance of performance, scalability, and metadata filtering
- Native support for hybrid search (sparse + dense) aligns with our retrieval architecture
- Self-hosted option gives full control over cost, security, and compliance
- Strong community and active development

### Future Upgrade Path
- Evaluate Pinecone for managed SaaS if in-house ops overhead increases
- Monitor ChromaDB as it matures for even lighter-weight deployments

---

## 4. Large Language Model (LLM)

### Decision
**Primary:** GPT-4 (OpenAI)  
**Fallback:** Claude (Anthropic)  
**Local/Private:** Llama 3 (Meta)

### Alternatives Considered
- **GPT-4 / GPT-4 Turbo (OpenAI):** Strong reasoning, extensive context window
- **Claude 3 (Anthropic):** Excellent long-context handling, strong instruction following
- **Gemini (Google):** Multimodal, competitive reasoning
- **Llama 3 (Meta):** Open-source, self-hostable, strong performance for size

### Tradeoffs Evaluated

| Model | Reasoning | Context Window | Cost | Privacy | Self-Hosted |
|-------|-----------|--------------|------|---------|-------------|
| GPT-4 | Excellent | 128K | High | Low | No |
| Claude 3 | Excellent | 200K | High | Low | No |
| Gemini | Strong | 1M | Medium | Low | No |
| Llama 3 | Strong | 128K | Low | High | Yes |

### Final Rationale
- GPT-4 offers the most consistent and robust performance across parsing, summarization, and comparison tasks
- Claude 3 serves as a fallback for long-document processing (very long resumes)
- Llama 3 available for private or fully self-hosted deployments where data cannot leave the environment
- Using a deterministic scoring engine reduces direct dependency on LLM reasoning for rankings, mitigating cost concerns

### Future Upgrade Path
- Evaluate GPT-5, Claude 4, or other next-generation models as they release
- Expand Llama-based deployment for fully offline, privacy-first use cases

---

## 5. Candidate Scoring Strategies

### Decision
Ship **three independent scoring strategies**, runnable side by side, defaulting to the hybrid blend:

| Strategy | File | Output folder | Use case |
|---|---|---|---|
| **Keyword** | `src/scoring/keyword_scorer.py` | `data/scores/keyword/` | Hard requirements, compliance, audit-first |
| **Semantic** | `src/scoring/semantic_scorer.py` | `data/scores/semantic/` | Synonym-heavy roles, soft-skill matches |
| **Hybrid** | `src/scoring/hybrid_scorer.py` | `data/scores/hybrid/` | Default; balances both |

The **LLM never determines final rankings** — it is restricted to extraction, summarization, comparison, and chat. All three scorers are deterministic given the same model + chunks.

### Alternatives Considered

| Approach | Explainability | Reproducibility | Cost | Synonym handling | Bias risk |
|----------|---------------|-----------------|------|-------------------|-----------|
| Keyword only | High | High | Low | Poor | Low |
| Semantic (cosine) only | Medium (numeric) | High (same model) | Low | Good | Low |
| LLM-direct ranking | Low | Low | High | Excellent | High |
| Hybrid (α-blend) | High (both lenses) | High | Low | Good | Low |
| ML-trained ranker | Medium | Medium | Medium | Good (depends on training) | Medium |

### Final Rationale
- **Three strategies = three independent ranking signals.** Recruiters can pick the strategy per role, and `scripts/compare_scores.py` shows rank deltas so they can see which candidates are robustly good vs. strategy-dependent
- The **hybrid default (`α = 0.5`)** gives recruiters the best of both: keyword catches hard requirements, semantic catches synonyms and paraphrases
- All strategies are **explainable per-component** — each score component links to a `chunk_id` + `source_file` so recruiters can click through to the original PDF
- Keyword is the cheapest and most auditable; semantic handles the "did the candidate really do this?" case keyword misses; hybrid is the safe production default

### Aggregation Rules

- **Keyword:** `raw / max_possible * 100`. Per-item binary match (full importance or 0). Special cases (years of experience, bachelor's detection) handled in `keyword_scorer._total_years_experience` and `_has_bachelor`.
- **Semantic:** `mean(max_cosine(bullet_i, candidate.chunks) for all i) * 100`. Bullets are equally weighted.
- **Hybrid:** `α * keyword_score + (1 - α) * semantic_score`. Per-component breakdowns preserved from both strategies.

### Future Upgrade Path
- Per-JD α configuration (recruiters tune blend weight per role)
- ML-trained reranker on top of cosine (cross-encoder for top-50 → top-5 precision)
- Confidence intervals on scores when using probabilistic features

---

## 6. Retrieval Strategy

### Decision
**Hybrid Search:** Sparse (BM25) + Dense (Vector) + Reranker

### Alternatives Considered
- **Sparse-Only (Keyword):** Fast, exact match, poor with synonyms
- **Dense-Only (Vector):** Good semantic understanding, misses exact terms
- **Hybrid (Sparse + Dense):** Balances exact matching and semantic understanding
- **Hybrid + Reranker:** Adds a reranking step to boost top-k precision

### Tradeoffs Evaluated

| Strategy | Exact Match | Semantic Match | Speed | Complexity |
|----------|-------------|----------------|-------|------------|
| Sparse-Only | Excellent | Poor | Fast | Low |
| Dense-Only | Poor | Excellent | Medium | Low |
| Hybrid | Good | Good | Medium | Medium |
| Hybrid + Reranker | Excellent | Excellent | Medium | High |

### Final Rationale
- Recruiters use both exact terms ("Python") and semantic concepts ("backend experience")
- Hybrid search satisfies both needs without sacrificing speed
- Reranking step significantly improves precision for RAG-based answers
- Supported natively by Qdrant, simplifying implementation

### Future Upgrade Path
- Evaluate ColBERT-style late interaction models for reranking
- Add query expansion or synonym injection to improve sparse retrieval

---

## 7. RAG Grounding Approach

### Decision
Strict Grounding — all answers must be derived from retrieved resume content. If no relevant chunk is found, respond: "Information not found in candidate documents."

### Alternatives Considered
- **Loose Grounding:** Allow general knowledge to augment retrieved content
- **Strict Grounding:** Only use retrieved content; no external knowledge
- **Citation Grounding:** Require specific quotes from source materials

### Final Rationale
- Prevents hallucination and protects candidate privacy
- Builds recruiter trust by ensuring every claim is evidence-based
- Aligns with legal and compliance requirements around candidate data

### Future Upgrade Path
- Add structured citation extraction (highlighting specific resume sections)
- Support cross-document synthesis when comparing candidates

---

## 8. Evaluation Framework

### Decision
Multi-level evaluation covering parsing, retrieval, generation, ranking, and business metrics.

### Metrics Choice
- **Parsing:** Precision, Recall, F1
- **Retrieval:** Recall@K, Precision@K, MRR, nDCG
- **Generation:** Faithfulness, Groundedness, Answer Relevancy, Completeness
- **Ranking:** Top-K Accuracy, Recruiter Agreement, Ranking Accuracy
- **Hallucination:** Hallucination Rate, Unsupported Statements
- **Business:** Screening Efficiency, Recruiter Time Saved, Recruiter Satisfaction

### Final Rationale
- End-to-end visibility into system performance is critical for an AI product
- Each metric ties directly to recruiter-facing outcomes
- Enables data-driven iteration and AI system improvement

### Future Upgrade Path
- Incorporate A/B testing framework for model and prompt changes
- Add automated regression pipelines triggered on code or model updates
