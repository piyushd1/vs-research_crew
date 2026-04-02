# VC Research System Quality Overhaul — Design Document

**Date:** 2026-04-02
**Status:** Approved
**Scope:** Approach B+ — Expert prompts, better tools, RAG, reflection, report quality

---

## Problem Statement

The multi-agent VC research system has solid architecture (workflows, evidence registry, scorecard, renderers, checkpoint/resume) but produces poor research output:

- **Agent failures:** For less-known companies (e.g., Handpickd), all 8 agents fail completely — they enter search loops, never produce a final JSON answer, and get replaced with empty placeholders. Eval score: 14/100.
- **Shallow research:** Even for well-known companies (e.g., Ather Energy, score 64.4/100), findings are surface-level — generic observations rather than VC-grade analysis with specific data points and frameworks.
- **Weak reports:** Final rendered reports lack the depth, structure, and writing quality expected for IC meetings.

## Root Cause Analysis

| Issue | Root Cause |
|-------|-----------|
| All agents fail for smaller companies | Agents loop searching, `max_tokens=4096` too small for JSON output, no graceful partial extraction |
| Shallow findings | Agent prompts say "assess X" without explaining HOW — no research frameworks, checklists, or examples |
| No dimension scores produced | Agents don't understand the scoring rubric; prompts don't explain what 1-5 means |
| Weak citations | Only tool is 3 Serper queries; no deep web crawl or document semantic search |
| Poor report writing | Report synthesizer gets a JSON dump and generic instructions; no template for IC-ready prose |
| Evidence gaps for data room docs | PDFExcerptTool reads only first 3 pages; can't query a 50-page financial model |

---

## Design: 9 Components

### 1. Agent Runner & JSON Robustness

**Changes to `runner.py` and `crew.py`:**

- Increase `max_tokens` from 4096 to 12000 in LLM config (agents need room for detailed JSON)
- Set `max_iter=15` on CrewAI Agent (prevent 25-iteration search loops)
- Set `max_retry_limit=2` on Agent
- Add a "salvage" extraction step: when agent output isn't valid JSON but contains useful text, use regex + heuristics to extract claims, sources, and open questions into a partial `AgentFindingResult`
- In the retry prompt, include a concrete JSON example showing what a valid response looks like
- Better error messages in retry prompts — show exactly what was wrong with the previous attempt

**Changes to `schemas.py`:**
- Make `AgentFindingResult` fields more lenient — `confidence` defaults to 0.5 instead of requiring explicit values
- Add `partial: bool = False` field to mark salvaged results

### 2. Tavily Deep Research Tool

**New file: `tools/tavily_tool.py`**

A CrewAI `BaseTool` that wraps the Tavily API for:
- **Deep search** (`search_depth="advanced"`) — returns richer snippets than Serper
- **Content extraction** — given a URL, extracts full page content as markdown
- **Research mode** — comprehensive multi-source research on a topic

Three tools exposed to agents:
- `TavilySearchTool` — deep web search with India-focused queries
- `TavilyExtractTool` — extract full content from a specific URL (company website, regulatory filing)
- `TavilyResearchTool` — comprehensive research on a topic (used by financial_researcher, market_mapper)

**Integration in `tools/__init__.py`:**
- All agents get `TavilySearchTool` if `TAVILY_API_KEY` is set
- `financial_researcher`, `market_mapper`, `product_tech_researcher` also get `TavilyResearchTool`
- `TavilyExtractTool` given to all agents for deep-diving specific URLs
- Serper tools kept as fallback if Tavily key not set

### 3. RAG with ChromaDB for Document Analysis

**New file: `tools/rag_tool.py`**

Uses ChromaDB (already installed in venv) for semantic search over:
1. **Uploaded documents** — PDFs and CSVs from `docs_dir`, chunked and embedded at run start
2. **Prior agent findings** — each agent's findings get indexed after completion

**Architecture:**
- `DocumentIndexer` class: takes `docs_dir`, extracts text from all PDFs (full content, not just 3 pages) and CSVs, chunks into ~500-token segments, embeds with ChromaDB's default embedding model, stores in a per-run collection
- `FindingsIndexer`: after each agent completes, indexes its findings and summary
- `DataRoomSearchTool` (CrewAI BaseTool): agents query with natural language, get top-k relevant chunks with source attribution

**Integration in controller.py:**
- At run start: if `docs_dir` exists, index all documents
- After each agent completes: index findings
- Tool added to all agents when docs_dir is provided or when prior findings exist

**Quality impact:**
- Financial researcher can query "What is the revenue breakdown by segment?" and get data from page 37 of a 50-page model
- Risk analyst can query "What financial risks were identified?" and get precise prior findings
- Citations become specific: "Per uploaded pitch deck, page 12: ARR grew 3x..."

### 4. Expert Agent Prompts with VC Frameworks

**Changes to `agents.yaml` and `controller.py` `_build_specialist_prompt()`:**

Each specialist gets a detailed research playbook injected into its prompt. Examples:

**financial_researcher prompt framework:**
```
FINANCIAL ANALYSIS FRAMEWORK:
1. Revenue quality: What is the revenue model? Recurring vs transactional? Concentration risk?
2. Unit economics: CAC, LTV, contribution margin, payback period. If not available, what proxies exist?
3. Burn & runway: Monthly burn rate, cash position, months of runway. If not public, what can be inferred from funding history and team size?
4. Growth trajectory: Revenue growth rate, user/customer growth, retention/churn signals
5. Capital efficiency: Revenue per employee, gross margin trajectory

SCORING RUBRIC (1-5):
- 5: Strong unit economics with clear path to profitability, diversified revenue
- 4: Good growth with improving economics, some gaps in data
- 3: Early revenue with unclear economics, limited data available
- 2: Pre-revenue or deeply negative economics with high burn
- 1: No revenue signal, unclear business model

RED FLAGS: Revenue concentration >50% in one customer, burn multiple >3x, negative gross margins, declining growth rate
GREEN FLAGS: Net revenue retention >120%, CAC payback <18 months, improving gross margins quarter-over-quarter

WHEN DATA IS SPARSE:
- State explicitly what you could NOT find
- Use proxies: team size × avg salary = rough burn estimate; funding rounds = implied valuation trajectory
- Mark all inferred data with confidence <0.5
- List specific open questions for the IC
```

Similar frameworks for every specialist — market_mapper gets Porter's Five Forces + TAM/SAM/SOM, founder_signal_analyst gets a founder assessment rubric, etc.

**Changes to `agents.yaml`:**
- Expand `backstory` for each agent with domain expertise framing
- Add `prompt_notes` with specific research instructions
- Add `failure_guidance` — what to do when data is sparse (critical for fixing the "loop until timeout" problem)

### 5. Research Planning & Self-Critique (Reflection)

**Research planning (added to `_build_specialist_prompt()`):**

Before the main research task, each agent prompt starts with:
```
STEP 1 - RESEARCH PLAN (think before you search):
Before using any tools, outline your research plan:
- What are the 3-5 most important questions to answer for this dimension?
- What sources are most likely to have this data?
- What will you do if the primary sources don't have the data?

STEP 2 - EXECUTE (max 4-6 tool calls):
Execute your plan. Do NOT repeat queries. If a source doesn't have what you need, move on.

STEP 3 - SELF-CRITIQUE (before submitting):
Before producing your final JSON, check:
□ Every claim has a specific source citation (not "various sources" or "industry reports")
□ Confidence scores reflect actual evidence strength (don't default everything to 0.8)
□ Open questions list everything you couldn't verify
□ Dimension scores use the rubric above, not gut feel
□ No claims are copied from the brief — only new research
```

**Stronger evidence auditor:**

The evidence_auditor prompt gets upgraded to:
- Specifically check for claims without citations
- Check for circular reasoning (agent citing the brief as evidence)
- Check for dimension score inflation (all 4s and 5s without supporting evidence)
- Produce targeted re-investigation flags when gaps are critical

### 6. Report Synthesizer & Renderer Improvements

**Report synthesizer prompt rewrite:**

The current prompt just says "Synthesize the VC diligence record into a structured findings bundle." The new prompt includes:

- **Section templates** — what each section should contain and how long it should be
- **Writing style guide** — "Write like a senior VC analyst. Lead with the conclusion, then evidence. No marketing language. Specific data points over generalizations."
- **Minimum requirements** — each section must have at least 2 specific data points and 1 citation

**Renderer improvements (`ic_memo_renderer.py`, `full_report_renderer.py`):**

- Add a "Company Snapshot" section at the top with key metrics table
- Add formatting for data tables (revenue, key metrics)
- Increase target word ranges: IC memo from 700-1600 to 1200-2500, full report from 1400-3200 to 2500-5000
- Add section word count targets so each section gets appropriate depth

**Fallback bundle improvements:**

The `_build_fallback_bundle()` method currently just concatenates agent summaries. Upgrade to:
- Merge findings from all agents into coherent section narratives
- Deduplicate and consolidate overlapping findings
- Ensure every section has actual content, not "X not available"

### 7. Model Recommendations for OpenRouter

**Research for best cheap thinking models:**

Update `llm.yaml` with recommended models and add a `models` section:

For research agents (need reasoning + tool use):
- Primary: `deepseek/deepseek-r1` (strong reasoning, cheap)
- Alternative: `qwen/qwen3-235b-a22b` (good at structured output)

For synthesis/eval agents (need writing quality):
- `deepseek/deepseek-r1` or `meta-llama/llama-3.3-70b-instruct`

Add model selection guidance in the config with cost/quality tradeoffs.

### 8. Tool Orchestration & Selection

**Smarter tool selection in `tools/__init__.py`:**

Current: all agents get the same tools. New: agent-specific toolkits:

| Agent | Tools |
|-------|-------|
| financial_researcher | FinancialSignalSearch, TavilyResearch, DataRoomSearch, PDFExcerpt, CSVPreview |
| market_mapper | TavilySearch, TavilyResearch, IndiaSourceRegistry |
| product_tech_researcher | TavilySearch, TavilyExtract, DataRoomSearch |
| founder_signal_analyst | TavilySearch, IndiaSourceRegistry |
| customer_competition_analyst | TavilySearch, TavilyExtract |
| india_regulatory_legal_analyst | TavilySearch, TavilyExtract, IndiaSourceRegistry |
| risk_red_team_analyst | DataRoomSearch (query prior findings) |
| investment_analyst | DataRoomSearch (query prior findings) |
| valuation_scenarios_analyst | DataRoomSearch, FinancialSignalSearch |

### 9. Documentation

**Update `README.md`** with:
- Updated architecture diagram
- Setup instructions (API keys: OPENROUTER, TAVILY, SERPER)
- Model selection guidance
- Example run walkthrough
- Eval interpretation guide

**New `docs/ARCHITECTURE.md`:**
- Component diagram
- Data flow from brief → agents → findings → synthesis → report
- Tool integration map
- How to add new agents or sectors

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `runner.py` | Modified | Salvage extraction, better retry prompts, JSON example |
| `crew.py` | Modified | Agent config (max_iter, max_retry_limit) |
| `schemas.py` | Modified | Lenient defaults, partial flag |
| `tools/tavily_tool.py` | **New** | Tavily search/extract/research tools |
| `tools/rag_tool.py` | **New** | ChromaDB RAG for docs and findings |
| `tools/__init__.py` | Modified | Agent-specific toolkit selection |
| `tools/custom_tool.py` | Modified | Minor cleanup |
| `config/agents.yaml` | Modified | Expanded backstories, prompt_notes, failure_guidance |
| `config/llm.yaml` | Modified | Model recommendations, increased max_tokens |
| `controller.py` | Modified | RAG integration, improved prompts, better fallback bundle |
| `renderers/ic_memo_renderer.py` | Modified | Richer formatting, section depth |
| `renderers/full_report_renderer.py` | Modified | Data tables, word count targets |
| `config/output_profiles/*.yaml` | Modified | Updated word ranges |
| `report_standards.py` | Modified | Updated validation thresholds |
| `evals/judge.py` | Modified | Updated eval prompt for new quality bar |
| `evidence.py` | Modified | Stronger audit checks |
| `README.md` | Modified | Full documentation update |
| `docs/ARCHITECTURE.md` | **New** | Architecture documentation |

## Success Criteria

1. No agent should fail completely for any company — worst case is partial findings with explicit gaps
2. Eval scores should average >65/100 for well-known companies, >45/100 for obscure ones
3. Reports should contain specific data points, not just generic observations
4. Every claim in the report should have a traceable citation
5. IC memo should be 1200-2500 words; full report should be 2500-5000 words
