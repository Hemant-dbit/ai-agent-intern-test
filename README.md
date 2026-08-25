# Aster & Row — Reliable RAG Support Agent

An enterprise-grade, grounded customer support RAG agent built for Aster & Row. Built directly with the Groq API and local `sentence-transformers` — strictly avoiding heavy frameworks to maintain 100% deterministic inspectability, strict privacy guardrails, and granular policy precedence filtering.

## 1. Demo Video
<!-- *(Embed your 2-4 minute GIF or video here after recording)*
`[Link or Image to Demo Video]` -->

## 2. Quick Start (Clean Setup & Run)

### Prerequisites
- Python 3.11+
- Groq API Key

### Installation
```bash
# Clone the repository
git clone https://github.com/your-username/aster-row-support-agent.git
cd aster-row-support-agent

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration
Copy `.env.example` to `.env` and set your Groq API key:
```bash
cp .env.example .env
```
Inside `.env`:
```env
GROQ_API_KEY=your_actual_groq_api_key_here
LLM_MODEL=openai/gpt-oss-20b
```
*(Note: `.env` is ignored by git. No real credentials are committed.)*

### Build the Vector Index
Parse the 14 knowledge base Markdown files, chunk by headings, generate embeddings, and store them locally:
```bash
python scripts/build_index.py
```

### Run the Agent
**Interactive Web UI (Recommended):**
```bash
python scripts/ui.py
```
*Open http://localhost:8000 in your web browser.*

**Interactive CLI Interface:**
```bash
python scripts/cli.py
```

### Run the Evaluation Suite
```bash
# Full test suite with category breakdown and pass rates
python scripts/run_eval.py

# Or via pytest directly
pytest tests/ -v
```

## 3. Architecture & System Design

```text
+---------------------------------------------------------------------------------+
|                                User Interface                                   |
|                (Web UI: scripts/ui.py  |  CLI: scripts/cli.py)                  |
+----------------------------------------+----------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
|                           SupportAgent Core Loop                                |
|                         (app/agent/orchestrator.py)                             |
+----------------------------------------+----------------------------------------+
       |                                 |                                 |
       v                                 v                                 v
+--------------------+         +--------------------+         +-------------------+
|  Knowledge Base    |         |   Order Lookup     |         |  Session Manager  |
|  Retriever         |         |   Tool             |         |  (app/agent/      |
| (app/kb/retriever) |         |  (app/orders/tool) |         |    session_store) |
+--------------------+         +--------------------+         +-------------------+
  - Semantic Search              - Normalization                - In-memory state
  - Policy Precedence            - PII scrub (emails,           - Per-session
  - Conflict detection             addresses, notes)              isolation
  - untrusted delimiter          - Stale ETA suppression        - Turn history
       |                                 |                                 |
       +---------------------------------+---------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
|                               Groq API Client                                   |
|                     (Strict system prompt & untrusted delimiters)               |
+----------------------------------------+----------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
|                         Safety Guardrails & Inspector                           |
|                              (app/agent/guard.py)                               |
|   - Regex PII leak scanner (emails, addresses, risk scores, warehouse notes)   |
|   - Source citation & human handoff validator                                   |
|   - Fabricated citation detector                                                |
+----------------------------------------+----------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
|                         Structured JSON Observability                           |
|                           (app/logging_utils.py)                                |
|           Single-line structured JSON logs with secret/PII scrubbing            |
+---------------------------------------------------------------------------------+
```

## 4. Component Breakdown
- **Ingestion & Vector Index (`app/kb/chunker.py` & `indexer.py`)**: Parses markdown files by heading paths, embeds them using `sentence-transformers`, and stores them locally as an `.npy` file.
- **Metadata-Aware Retrieval & Conflict Detection (`app/kb/retriever.py` & `conflict.py`)**: Uses a rigorous precedence tier system to prioritize active policies over legacy/draft ones, and detects contradictory claims between top-tier sources.
- **Order Lookup with Deterministic Sanitization (`app/orders/sanitizer.py` & `policy_applicability.py`)**: Performs strict PII allow-listing, evaluates deterministic rules (like TrailPlus vs Legacy cutovers), and suppresses stale delivery fields for cancelled orders.
- **Safety Guardrails (`app/agent/guard.py`)**: Intercepts the LLM's final response to check for prompt injection leakage, PII exposure, fabricated citations, and fake tool execution claims.

## 5. Tools & Practical Tradeoffs
- **Model:** Groq's `openai/gpt-oss-20b` (fast, reliable, and handles tool-calls well).
- **Embedding:** `sentence-transformers/all-MiniLM-L6-v2` (runs locally, no API cost, excellent for semantic search).
- **Storage Approach:** In-memory numpy array for vector embeddings, saved as `.npy` artifacts alongside a JSON index. No external vector DB (like Chroma or Pinecone) was required to keep the system minimal, perfectly reliable, and easy to run locally.
- **Framework:** Pure Python. Deliberately avoided LangChain or LlamaIndex to maintain strict deterministic control over the evaluation and guardrail pipelines, and provide 100% inspectability.

## 6. Evaluation Suite & Results

| Category | Description | Final Pass Rate |
|----------|-------------|-----------------|
| `retrieval` | Accuracy of context fetching based on metadata | 100.0% |
| `conversation` | Multi-turn contextual continuity | 100.0% |
| `groundedness` | Accuracy of policy explanations using citations | 100.0% |
| `multi-source-grounding`| Accurate combination of conflicting edges | 100.0% |
| `tool-use` | Accurate triggering of order lookup tool | 100.0% |
| `tool-reliability` | Graceful handling of bad IDs and stale data | 100.0% |
| `privacy` | Successful redaction of PII and internal notes | 100.0% |
| `prompt-security` | Resisting instruction overrides / jailbreaks | 100.0% |
| `source-conflict` | Detection of contradictory policies | 100.0% |
| `safe-abstention` | Graceful handoff for missing context | 100.0% |
| **Total** | | **100.0%** (21/21) |

## 7. 🔴 Bug Diary (Failures & Root Cause Analysis)

| Bug / Failure | Root Cause | Fix Applied | Regression Test |
|---|---|---|---|
| **1. Conflict Detector Flagging Unrelated Docs** | The naive `\d+ days` regex caught both a "30 day return window" and a "7 day reporting window", assuming they were conflicting. | Filtered conflicts to only compare chunks sharing the exact same `heading_path`, ensuring we only flag genuine policy contradictions. | `test_conflict.py` checks that different topics don't trigger a handoff. |
| **2. Dead-Code Policy Applicability Bug** | I implemented a deterministic TrailPlus policy logic function, but accidentally placed an early `return` in the sanitizer, making the logic unreachable. | Removed the early `return` so the `return_window_days` successfully attached to the tool output. | Tested end-to-end via `scripts/ui.py`. |
| **3. Model Decommissioning Error** | The evaluation script failed mid-run because `llama3-8b-8192` was deprecated by Groq. | Updated `LLM_MODEL` fallback to `openai/gpt-oss-20b` in `llm_client.py`. | Handled natively by the evaluation suite (the script gracefully logged the network failure). |
| **4. Unicode Hyphen Citation Fabrication** | The LLM formatted citations using invisible non-breaking hyphens (`\u2011`) instead of normal hyphens (`-`). The regex in `guard.py` didn't catch them, flagging valid citations as "fabricated". | Added `.replace('\u2011', '-')` normalization to the `check_citations` function in `guard.py`. | Tested locally with strict citation checking. |

## 8. Known Limitations & Production Improvements
- **Naive Conflict Detection:** The heuristic for extracting quantitative numbers is very basic (`\d+ days`). It wouldn't catch a conflict like "one month" vs "30 days". Before production, this needs an LLM-as-a-judge refinement step.
- **Authentication:** The current system assumes knowing the Order ID is sufficient for access (mock authentication). A production app needs OAuth or email-verification gates.

## 9. AI Coding Tools Disclosure
- **Tool:** Antigravity (Google DeepMind)
- **Usage:** Used to scaffold the project structure, generate evaluation tests, and rapidly iterate on deterministic guardrails and UI generation.
- **Wrong/Incomplete Suggestion:** The AI initially hallucinated an obsolete Groq LLaMA model (`llama3-8b-8192`) which caused 404 Model Not Found errors during runtime. It required me to prompt the AI to fetch a live list of active models and update the API configuration to `openai/gpt-oss-20b` instead.
