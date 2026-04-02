# MyAgents VC Research System

An India-first VC research and diligence system built on CrewAI. Runs multi-agent workflows to produce IC-ready investment memos, full diligence reports, and one-pager summaries.

## Key Features

- **3 Workflows:** sourcing, due_diligence, portfolio
- **3 Output Profiles:** ic_memo, full_report, one_pager
- **16 Specialist Agents** with VC-grade research frameworks
- **Deep Web Research** via Tavily (search, extract, comprehensive research)
- **RAG / Vector Store** using ChromaDB for semantic search over uploaded documents and cross-agent findings
- **India-First** source packs, scorecard weights, and regulatory focus for 15 sectors
- **Evidence Auditing** with conflict detection, circular reasoning checks, and score inflation flags
- **LLM-as-a-Judge Evaluation** with structured rubric scoring
- **Checkpoint/Resume** for long-running workflows
- **PDF Export** via WeasyPrint
- **Linear Integration** for issue tracking

## Supported Sectors

fintech, saas_ai, consumer, d2c, healthtech, deeptech, climate, agritech, edtech, logistics, marketplaces, proptech, cybersecurity, b2b_services

Common aliases are also supported (e.g., `healthcare` -> `healthtech`, `ecommerce` -> `d2c`, `payments` -> `fintech`).

## Architecture

```
Brief (YAML/JSON) -> Controller -> Specialist Agents (sequential) -> Evidence Registry
                                        |                              |
                                   Tools:                        Conflict Detection
                                   - Tavily Search/Extract       Score Inflation Check
                                   - Financial Signal Search     Circular Reasoning Check
                                   - RAG (ChromaDB)                    |
                                   - PDF/CSV Tools              Evidence Auditor (LLM)
                                   - India Source Registry             |
                                                                Report Synthesizer (LLM)
                                                                       |
                                                              Deterministic Renderer
                                                              (IC Memo / Full Report / One Pager)
                                                                       |
                                                              PDF Export + Linear Push + Eval
```

## Environment Setup

Copy `.env.example` to `.env` and add your API keys:

```env
# Required: LLM provider
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Recommended: Deep web research (significantly improves research quality)
TAVILY_API_KEY=your_tavily_api_key_here

# Optional: Financial signal search (Serper, used alongside Tavily)
SERPER_API_KEY=your_serper_api_key_here

# Optional: Linear issue tracking
LINEAR_API_KEY=your_linear_api_key_here
```

## LLM Configuration

Default config in `src/my_agents/config/llm.yaml`:

```yaml
provider: openrouter
model: openrouter/deepseek/deepseek-r1    # Best reasoning, very cheap
temperature: 0.2
max_tokens: 12000
```

### Model Selection Guide (OpenRouter)

| Model | Cost | Best For |
| --- | --- | --- |
| deepseek/deepseek-r1 | ~$0.55/M input | Research agents (reasoning + tool use) |
| qwen/qwen3-235b-a22b | ~$0.30/M input | Strong structured output, cheaper |
| deepseek/deepseek-v3.2 | ~$0.25/M input | Fast, cheapest, less reasoning |
| meta-llama/llama-3.3-70b-instruct | ~$0.20/M input | Eval judge (reliable JSON) |

Open-source models only by default. Set `allow_closed_models: true` in llm.yaml to use Claude/GPT-4o.

## Installation

```bash
cd my_agents
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

Or with `uv`:

```bash
cd my_agents
uv sync
cp .env.example .env
```

## Running

### Interactive Mode (simplest)

```bash
source .venv/bin/activate
my_agents
```

Prompts you for company name, sector, workflow, and report type.

### Quick Mode

```bash
my_agents --company "Razorpay" --workflow due_diligence --output-profile ic_memo
```

### With Brief File

```yaml
# brief.yaml
company_name: Example Fintech
website: https://example.com
sector: fintech
stage: seed
geography: India
one_line: API infrastructure for credit underwriting.
questions:
  - What is differentiated about the underwriting model?
  - Which India-specific regulatory risks matter most?
docs_dir: /path/to/data_room/   # Optional: PDFs and CSVs for RAG
```

```bash
my_agents --workflow due_diligence --brief brief.yaml --output-profile full_report --run-evals
```

### Resume a Failed Run

```bash
my_agents --resume runs/razorpay/2026-04-01_120000
```

### Evaluate an Existing Run

```bash
my_agents --eval-only-dir runs/razorpay/2026-04-01_120000
```

## Outputs

Each run creates a versioned folder under `runs/{company_slug}/{timestamp}/`:

| File | Description |
| --- | --- |
| `report.md` | Rendered report (markdown) |
| `report.html` | Rendered report (HTML) |
| `report.pdf` | PDF export (if WeasyPrint available) |
| `one_pager.html` | Self-contained one-pager (if one_pager profile) |
| `scorecard.json` | Dimension scores with evidence metrics |
| `sources.json` | Deduplicated source list |
| `findings_bundle.json` | Structured findings for all sections |
| `run_state.json` | Checkpoint/resume state |
| `findings/{agent}.json` | Individual agent findings |
| `eval_score.json` | LLM evaluation rubric (if --run-evals) |
| `eval_report.md/html` | Evaluation report |
| `report_validation.json` | Deterministic standards check |

## RAG / Document Analysis

When you provide a `docs_dir` with PDFs and CSVs, the system:

1. **Indexes all documents** into ChromaDB at run start (full content, not just first 3 pages)
2. **Agents query semantically** — the financial_researcher can ask "revenue breakdown" and find the right data from page 37
3. **Cross-agent knowledge** — after each agent completes, its findings are indexed so later agents can query prior work

This significantly improves report quality for companies with data rooms.

## Tools Available to Agents

| Tool | Description | Agents |
| --- | --- | --- |
| `tavily_search` | Deep web search | All non-internal agents |
| `tavily_extract` | Extract full page content from URL | All non-internal agents |
| `tavily_research` | Comprehensive multi-source research | financial, market, product, customer, gtm |
| `financial_signal_search` | Company-grounded financial signals (Serper) | financial_researcher, kpi_burn_analyst |
| `data_room_search` | Semantic search over docs + prior findings (ChromaDB) | All agents (when docs available) |
| `india_source_registry` | India-first source guidance | All agents |
| `pdf_excerpt` / `csv_preview` | Read uploaded documents | All agents (when docs_dir set) |

## Testing

```bash
.venv/bin/python -m pytest tests/ -v
```

58 tests covering: configuration, controller flow, renderers, report standards, runner, tools, RAG, Tavily, evals, sector coverage, quick mode, E2E smoke.

## Where Things Live

| Path | Purpose |
| --- | --- |
| `src/my_agents/main.py` | CLI entrypoint |
| `src/my_agents/controller.py` | Orchestration engine |
| `src/my_agents/runner.py` | Agent runner with JSON retry + salvage |
| `src/my_agents/config/agents.yaml` | Agent definitions with VC frameworks |
| `src/my_agents/config/workflows/` | Workflow task queues |
| `src/my_agents/config/llm.yaml` | LLM provider config |
| `src/my_agents/tools/` | CrewAI tools (Tavily, RAG, India sources) |
| `src/my_agents/renderers/` | Deterministic report renderers |
| `src/my_agents/evals/` | LLM-as-a-judge evaluation |
| `src/my_agents/evidence.py` | Evidence registry + conflict detection |
