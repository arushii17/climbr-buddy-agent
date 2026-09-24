# Climbr Buddy — Design Decisions, Limitations & Future Improvements

## Overview

Climbr Buddy is an autonomous lead-research agent designed to accept a high-level business goal and independently plan and execute the steps required to identify potential leads for Climbr Agency. The system combines LLM-based reasoning with deterministic Python components so that tasks requiring interpretation remain flexible while execution, scoring, validation, and recovery remain controlled and observable.

## Key Design Decisions

### 1. LLM Reasoning with Deterministic Control

Backboard is used as the LLM interface for planning, search-query generation, company extraction, website verification, evidence analysis, and final report generation. Deterministic Python logic handles tool orchestration, query sanitisation, domain filtering, retries, lead scoring, and output persistence.

This separation was intentional: the LLM handles tasks requiring semantic interpretation, while predictable operations are kept deterministic to reduce unnecessary variability.

### 2. Evidence-First Lead Discovery

Search results are treated as discovery sources rather than immediately as leads. The agent reads startup lists, funding articles, and other public pages before extracting actual company names from their content.

Each company is then independently researched. This prevents article titles, publishers, or directories from being incorrectly treated as potential leads.

### 3. Conservative Company Verification

After discovering a company, the agent attempts to resolve its official website. Candidate domains are filtered and the company identity is verified using the company name and discovery context.

If an official website cannot be confidently verified, the agent does not guess. Instead, it falls back to the original discovery evidence and records that the website was not verified.

### 4. Self-Correction and Failure Recovery

The system deliberately induces a timeout during a website-reader call to demonstrate failure handling. The agent detects and logs the error, retries the tool without the simulated failure, and continues execution when successful.

If the retry also fails, the agent degrades gracefully by using previously collected discovery evidence instead of terminating the entire workflow.

### 5. Grounded Analysis and Scoring

Lead analysis separates evidence of business relevance, digital presence, growth, and a potential agency-service need. Growth or funding alone is not treated as proof that a company requires agency services.

Lead scores are calculated using deterministic rules rather than being generated directly by the LLM. This makes scoring more transparent and reproducible.

## Limitations

The quality of the research depends on publicly available and indexed web information. Some websites may block automated requests, and ambiguous company names can make official-site verification difficult. Public information also cannot reveal internal budgets, priorities, or purchasing intent.

Although prompts and deterministic validation reduce unsupported claims, LLM-based extraction and analysis can still produce imperfect interpretations. The current lead-scoring model is heuristic and should therefore be treated as a research prioritisation signal rather than a prediction of conversion.

## With More Time

I would extend the system with multi-source evidence verification, stronger entity resolution, source-quality ranking, broader automated testing, and parallel company research. I would also add persistent lead history and duplicate detection, CRM integration, and a human-approval step before any outreach action.

These improvements would move Climbr Buddy from an autonomous research prototype toward a more robust production lead-intelligence workflow.