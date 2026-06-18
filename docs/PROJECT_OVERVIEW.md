# HireIntel AI – Explainable Candidate Intelligence Platform

## Project Overview

HireIntel AI is an AI-powered Candidate Intelligence Platform designed to help recruiters screen, evaluate, rank, compare, and interact with job applicants in a transparent and explainable manner.

Unlike traditional ATS systems that rely on keyword matching or black-box scoring, HireIntel AI allows recruiters to define their own hiring priorities and scoring weights. The platform then evaluates candidates using evidence extracted from resumes, generates recruiter-friendly summaries, provides explainable rankings, and enables conversational exploration of candidate profiles through Retrieval-Augmented Generation (RAG).

The goal is to reduce recruiter workload, improve screening consistency, and provide transparent, evidence-based hiring recommendations.

---

# Problem Statement

Recruiters often review hundreds of resumes for a single position.

Current recruitment workflows suffer from:

* Manual resume screening
* Inconsistent candidate evaluation
* Black-box AI recommendations
* Limited transparency in candidate ranking
* Difficulty comparing multiple candidates
* Time-consuming resume reviews

HireIntel AI addresses these challenges by combining NLP, LLMs, Explainable AI, and RAG-based candidate intelligence.

---

# Key Differentiators

Unlike generic ATS systems and resume chatbots, HireIntel AI provides:

* Recruiter-controlled scoring policies
* Explainable candidate rankings
* Evidence-based candidate evaluation
* Deterministic scoring engine
* Resume-grounded AI reasoning
* Candidate comparison engine
* Conversational candidate intelligence
* Transparent hiring recommendations
* Multi-level AI evaluation framework

---

# End-to-End Workflow

```text
Job Description Upload
          │
          ▼
Requirement Extraction
          │
          ▼
Recruiter Weight Configuration
          │
          ▼
Resume Upload
          │
          ▼
Resume Parsing
          │
          ▼
Structured Candidate Profiles
          │
          ▼
Deterministic Scoring Engine
          │
          ▼
Candidate Ranking
          │
          ▼
Candidate Summaries
          │
          ▼
Candidate Comparison
          │
          ▼
Resume Chat (RAG)
          │
          ▼
Hiring Recommendations
```

---

# Phase 1: Job Description Intelligence

## Objective

Understand hiring requirements before evaluating candidates.

## Input

* Job Description (PDF, DOCX, Text)

## Information Extracted

* Required Skills
* Preferred Skills
* Required Experience
* Education Requirements
* Certifications
* Industry Experience
* Leadership Requirements
* Technology Stack

## Example

```text
Required Skills:
HTML
CSS
JavaScript
React

Experience:
6+ Years

Education:
B.Tech

Preferred:
NIT / IIT
```

---

# Phase 2: Recruiter Weight Configuration

## Objective

Allow recruiters to define what matters most for a particular role.

Instead of AI deciding candidate importance, recruiters assign weights.

## Example

```text
HTML                10 Points
CSS                  5 Points
JavaScript          10 Points
React               10 Points

Same Role Experience 10 Points
Industry Experience  5 Points

Education            3 Points
Certifications       2 Points
```

These weights become the hiring policy for candidate evaluation.

---

# Phase 3: Resume Parsing

## Objective

Convert unstructured resumes into structured candidate profiles.

## Information Extracted

* Candidate Name
* Contact Information
* Education
* Skills
* Certifications
* Languages Known
* Work Experience
* Projects
* Technology Stack
* Leadership Experience

## Techniques

* NLP
* LLM-based Information Extraction
* Resume Structure Analysis
* Document Parsing

---

# Phase 4: Candidate Evaluation Engine

## Objective

Objectively evaluate candidates using recruiter-defined scoring policies.

The platform does not generate black-box scores.

Every score must be supported by evidence.

---

## Example Candidate Evaluation

### Total Score: 87 / 100

### Skills

HTML

Score: 10 / 10

Reason:
6 years of HTML experience identified.

---

CSS

Score: 5 / 10

Reason:
3 years of CSS experience identified.

---

React

Score: 9 / 10

Reason:
5 years of React experience identified.

---

### Experience

Same Role Experience

Score: 9 / 10

Reason:
5 years in similar role.

---

Technology Alignment

Score: 8 / 10

Reason:
Worked extensively with required technology stack.

---

### Education

Score: 7 / 10

Reason:
B.Tech from recognized institution.

---

### Projects

Score: 9 / 10

Reason:
Multiple projects aligned with target role.

---

# Candidate Evaluation Dimensions

The platform evaluates:

* Skill Match
* Skill Coverage
* Relevant Experience
* Technology Stack Experience
* Industry Experience
* Product Company Experience
* Leadership Experience
* Education Alignment
* Certification Alignment
* Project Relevance
* Language Capabilities
* Communication Quality
* Resume Organization

---

# Communication & Resume Quality Assessment

The platform evaluates communication quality based on resume structure rather than visual design.

Evaluation Criteria:

* Clarity
* Organization
* Chronological consistency
* Information hierarchy
* Readability
* Professional communication
* Achievement presentation

The system does not reward or penalize resume length by itself.

A longer resume can score highly if well structured.

A shorter resume can score poorly if poorly organized.

---

# Candidate Ranking

## Objective

Rank candidates based on recruiter-defined priorities.

## Important Principle

Large Language Models do not determine candidate rankings.

Rankings are generated using:

* Recruiter-defined weights
* Structured candidate profiles
* Deterministic scoring formulas

This ensures:

* Reproducibility
* Explainability
* Auditability

---

# Candidate Comparison Engine

Recruiters can compare shortlisted candidates.

Example Questions:

* Which candidate has the strongest React experience?
* Which candidate has worked longest in a similar role?
* Which candidate has the most relevant projects?
* Why is Candidate A ranked above Candidate B?

The system provides evidence-backed comparisons.

---

# Candidate Intelligence Summaries

The platform generates recruiter-friendly summaries.

Example:

> Candidate has 5 years of experience as a Front-End Developer with expertise in HTML, CSS, JavaScript, and React. Has worked on multiple large-scale web applications and demonstrates strong alignment with the target role requirements.

---

# Resume Chat (RAG)

## Objective

Enable conversational exploration of candidate information.

Example Questions:

* Does this candidate have NLP experience?
* What projects demonstrate machine learning expertise?
* Has this candidate worked with cloud technologies?
* Summarize leadership experience.
* What certifications does this candidate possess?

All responses must be grounded in retrieved resume content.

---

# RAG Architecture

## Chunking Strategy

Primary Strategy:

* Document-Aware Chunking

Optional Enhancement:

* Semantic Chunking within large sections

Examples:

* Education
* Experience
* Projects
* Skills
* Certifications

This preserves resume structure and improves retrieval quality.

---

## Embedding Pipeline

Possible Embedding Models:

* BGE-M3
* E5
* Nomic
* OpenAI Embeddings

Selection rationale is documented separately in:

AI_DESIGN_RATIONALE.md

---

## Vector Database

Potential options:

* Qdrant
* ChromaDB
* Pinecone
* FAISS

Final selection is documented in:

MODEL_REGISTRY.md

---

# AI Evaluation Framework

The platform evaluates performance at multiple levels.

## Resume Parsing

Metrics:

* Precision
* Recall
* F1 Score

---

## Retrieval Evaluation

Metrics:

* Recall@K
* Precision@K
* Mean Reciprocal Rank (MRR)
* nDCG

---

## Generation Evaluation

Metrics:

* Faithfulness
* Groundedness
* Answer Relevancy
* Completeness

---

## RAG Evaluation

Metrics:

* Context Recall
* Context Precision
* Faithfulness
* Answer Relevancy

---

## Candidate Ranking Evaluation

Metrics:

* Top-K Accuracy
* Recruiter Agreement
* Ranking Accuracy

---

## Hallucination Evaluation

Metrics:

* Unsupported Statements
* Hallucination Rate

---

## Business Evaluation

Metrics:

* Screening Efficiency
* Recruiter Time Saved
* Recruiter Satisfaction
* Shortlisting Accuracy

---

# AI Design Principles

## Explainability Over Black-Box Scoring

Every recommendation must be explainable.

---

## Recruiter-Controlled Priorities

Recruiters decide what matters.

The AI applies those priorities consistently.

---

## Evidence-Based Reasoning

All evaluations must reference extracted resume evidence.

---

## Grounded AI Responses

All conversational responses must be grounded in retrieved resume content.

---

## Reproducible Rankings

Candidate rankings must be deterministic and auditable.

---

## Transparent Hiring Recommendations

Every recommendation must include supporting evidence.

---

# Technology Stack

## NLP

* spaCy
* NLTK
* Regex

## LLMs

* GPT
* Claude
* Gemini
* Open-source LLMs

## Embeddings

* BGE-M3
* E5
* Nomic

## Vector Databases

* Qdrant
* ChromaDB
* Pinecone

## Backend

* Python
* FastAPI

## Frontend

* Streamlit

---

# Skills Demonstrated

* Natural Language Processing (NLP)
* Information Extraction
* Explainable AI (XAI)
* Large Language Models (LLMs)
* Retrieval-Augmented Generation (RAG)
* Prompt Engineering
* Vector Databases
* Semantic Search
* Candidate Ranking Systems
* Recommendation Systems
* AI Evaluation Frameworks
* Applied AI Product Design
* End-to-End GenAI Application Development
* Recruitment Intelligence Systems
