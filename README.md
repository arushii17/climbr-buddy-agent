# Climbr Buddy — Autonomous Lead Research Agent

Climbr Buddy is an autonomous AI agent built to research and evaluate potential business leads for **Climbr Agency**.

Given a high-level natural-language goal, the agent creates an execution plan, searches the public web, reads discovery sources, extracts relevant companies, verifies official company websites, analyses evidence, scores leads, handles tool failures, and generates a structured research report.

The project was developed as part of an **Agentic AI Engineer Intern Take-Home Assignment** to demonstrate autonomous planning, tool orchestration, failure recovery, evidence-grounded reasoning, and structured output generation.

---

## Example Goal

```text
Find 3 early-stage SaaS companies that could be potential clients for
Climbr Agency. Research their public websites, identify evidence of their
digital presence or growth, and explain what potential opportunity may
exist for Climbr.
```

The agent converts this high-level goal into an execution plan and carries out the research autonomously.

---

## Key Features

- Natural-language goal input
- Autonomous execution planning
- Public web search
- Discovery-source research
- Company extraction from articles and startup lists
- Official website resolution and identity verification
- Website content extraction
- Evidence-grounded lead analysis
- Deterministic lead scoring
- Tool failure detection and recovery
- Structured Markdown and JSON reports
- Detailed execution logging
- Graceful fallback when an official website cannot be verified

---

## Agent Workflow

```text
High-Level Goal
      |
      v
+-------------------+
|      Planner      |
|  Generate steps   |
+-------------------+
      |
      v
+-------------------+
|    Web Search     |
| Discover sources  |
+-------------------+
      |
      v
+-------------------+
| Discovery Reader  |
| Read public pages |
+-------------------+
      |
      v
+---------------------+
| Company Extraction  |
| Find real companies |
+---------------------+
      |
      v
+----------------------+
| Company Resolver     |
| Verify official site |
+----------------------+
      |
      v
+----------------------+
| Website Reader       |
| Collect evidence     |
+----------------------+
      |
      v
+----------------------+
| Evidence Analysis    |
| Assess lead signals  |
+----------------------+
      |
      v
+----------------------+
| Lead Scorer          |
| Deterministic score  |
+----------------------+
      |
      v
+----------------------+
| Reporter             |
| Markdown + JSON      |
+----------------------+
```

If a tool fails during execution, the agent attempts recovery before continuing.

---

## Tooling

### 1. Web Search

The web search tool uses `ddgs` to discover public sources containing potentially relevant companies.

The search strategy is generated dynamically from the user's goal. Restrictive `site:` operators are removed programmatically so that discovery is not limited to individual websites.

### 2. Discovery Reader

Search results may point to startup lists, funding articles, directories, or company websites.

Instead of assuming that the search-result title is a company, Climbr Buddy reads discovery pages and extracts actual company names from their content.

### 3. Company Resolver

The resolver searches for the official website of each extracted company.

Potential domains are filtered and then verified using company identity and discovery context. If the official website cannot be verified confidently, the agent does not guess and instead falls back to the original discovery evidence.

### 4. Website Reader

The website reader retrieves publicly available website content using `requests` and `BeautifulSoup`.

The extracted text is cleaned before being passed to the evidence-analysis stage.

### 5. Lead Scorer

Lead scoring is deterministic rather than generated directly by the LLM.

The score considers signals including:

- Relevance to Climbr's target market
- Digital presence
- Growth signals
- Evidence of a potential service need
- Number of supporting evidence points
- Evidence confidence

Scores are bounded between 0 and 100.

---

## LLM Integration

Climbr Buddy uses the **Backboard SDK** as its LLM interface.

Current configuration:

```text
Provider: OpenRouter
Model: openai/gpt-4o-mini
```

The LLM is used for tasks such as:

- Planning
- Search-query generation
- Company extraction
- Company identity verification
- Evidence analysis
- Report generation

Deterministic Python logic is used where appropriate, including lead scoring, search-query sanitisation, domain filtering, and execution control.

---

## Failure Recovery

A core requirement of the project is demonstrating self-correction when a tool fails.

Climbr Buddy deliberately simulates a website timeout during execution.

Example recovery flow:

```text
website_reader called
        |
        v
Simulated timeout
        |
        v
Failure detected
        |
        v
Retry website_reader
        |
        v
Retry succeeds
        |
        v
Continue execution
```

If the retry also fails, the agent falls back to available discovery evidence rather than terminating the entire workflow.

Example execution log:

```text
[ERROR] Simulated website timeout triggered.
[RECOVERY] Detected timeout: Simulated timeout for failure-recovery demonstration.
[RECOVERY] Retrying website_reader without simulated failure.
[RECOVERY] Retry succeeded. Continuing execution.
```

---

## Evidence Grounding

Climbr Buddy is designed to avoid inventing business opportunities.

The evidence-analysis component is instructed to distinguish between:

- Evidence that a company is relevant
- Evidence of digital presence
- Evidence of growth
- Evidence of an actual agency-service opportunity

For example, funding or rapid growth alone does not automatically imply that a company needs marketing services.

When the available evidence does not establish a concrete opportunity, the agent reports:

```text
No clear agency opportunity identified from available evidence.
```

---

## Example Result

One sample execution identified:

- Sherloq
- Melio
- Hona

The agent extracted these companies from public discovery sources, attempted to verify their official websites, analysed available evidence, scored the leads, and generated a final structured report.

For companies where an official website could not be confidently verified, the agent retained the discovery source instead of guessing a website.

---

## Project Structure

```text
climbr-buddy-agent/
│
├── agent/
│   ├── __init__.py
│   ├── executor.py
│   ├── llm.py
│   ├── planner.py
│   └── reporter.py
│
├── tools/
│   ├── __init__.py
│   ├── company_resolver.py
│   ├── lead_scorer.py
│   ├── search_tool.py
│   └── website_reader.py
│
├── utils/
│   ├── __init__.py
│   └── logger.py
│
├── tests/
│   └── test_scorer.py
│
├── outputs/
│   └── .gitkeep
│
├── app.py
├── config.py
├── conftest.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/arushii17/climbr-buddy-agent.git
cd climbr-buddy-agent
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Configuration

Create a `.env` file in the project root.

```env
BACKBOARD_API_KEY=your_backboard_api_key_here
BACKBOARD_PROVIDER=openrouter
BACKBOARD_MODEL=openai/gpt-4o-mini
```

The real `.env` file is excluded from Git through `.gitignore`.

Do not commit API keys or other secrets.

---

## Running the Agent

Run:

```bash
python app.py --max-leads 3
```

The CLI will ask for a high-level goal:

```text
Climbr Buddy — Autonomous Lead Research Agent

Enter your high-level goal:
>
```

Example:

```text
Find 3 early-stage SaaS companies that could be potential clients for
Climbr Agency. Research their public websites, identify evidence of their
digital presence or growth, and explain what potential opportunity may
exist for Climbr.
```

---

## Command-Line Options

Set the maximum number of leads:

```bash
python app.py --max-leads 5
```

Provide the goal directly:

```bash
python app.py --goal "Find 3 early-stage SaaS companies that could be potential clients for Climbr Agency." --max-leads 3
```

Disable the deliberately simulated failure:

```bash
python app.py --max-leads 3 --no-simulated-failure
```

---

## Output

Each successful execution generates:

```text
outputs/
├── lead_report_<timestamp>.md
└── lead_report_<timestamp>.json
```

The Markdown file contains the human-readable research report.

The JSON file contains the structured execution result for programmatic use.

The terminal also displays the execution log so that planning, tool calls, failures, recovery, and reporting remain observable.

---

## Testing

Run the test suite using:

```bash
pytest -v
```

The current tests validate the deterministic lead-scoring behaviour under different evidence and confidence conditions.

---

## Design Decisions

### LLM reasoning + deterministic control

The agent uses an LLM for tasks that require interpretation, such as planning, company extraction, and evidence analysis.

Deterministic Python logic is used for execution control, scoring, filtering, retries, and validation. This reduces dependence on unconstrained LLM output.

### Evidence-first lead generation

Search results are treated as discovery sources rather than automatically being treated as companies.

The agent reads these sources, extracts actual company names, resolves their websites, and then performs company-level research.

### Conservative website verification

A wrong company website can contaminate every downstream result. The resolver therefore prefers returning no verified website over selecting an uncertain match.

### Graceful degradation

A failure in one external tool should not necessarily terminate the entire task.

Where possible, Climbr Buddy retries the operation or falls back to already collected public evidence.

---

## Limitations

- Public web information may be incomplete or outdated.
- Some websites block automated HTTP requests.
- Company names can be ambiguous, making official-site verification difficult.
- Search quality depends on publicly indexed information.
- LLM-based extraction and analysis can still produce imperfect interpretations.
- A company's growth does not necessarily imply a need for agency services.
- Public evidence cannot reveal internal budgets, priorities, or purchasing intent.
- Lead scores are heuristic indicators rather than predictions of conversion.

---

## Future Improvements

With additional development time, the system could include:

- More robust company/entity resolution
- Multiple-source evidence verification
- Search-result deduplication and source-quality ranking
- Additional lead qualification signals
- CRM integration
- Persistent agent memory
- Parallel company research
- More comprehensive automated tests
- Human approval checkpoints before outreach
- Lead history and duplicate detection

---

## Tech Stack

- Python
- Backboard SDK
- OpenRouter
- GPT-4o-mini
- DDGS
- Requests
- BeautifulSoup
- python-dotenv
- Pytest

---

## Author

**Arushi Bhat**

B.Tech Computer Science & Engineering — Data Science  
The NorthCap University

GitHub: `arushii17`
