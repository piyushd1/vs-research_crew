# MyAgents VC Research System

This project is now a config-driven, India-first VC research system built on CrewAI.

It supports 3 workflows:
- `sourcing`
- `due_diligence`
- `portfolio`

It supports 3 output profiles:
- `ic_memo`
- `full_report`
- `one_pager`

The app is designed around open-source LLMs only by default. Closed models are not allowed unless you explicitly change the model policy in [`config/llm.yaml`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/config/llm.yaml).

It is ready to share as a normal CrewAI project: someone can clone this repo, install from [`requirements.txt`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/requirements.txt), add their key to [`.env.example`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/.env.example), and run the customized VC agent workflows.

## Where Things Live

- CLI entrypoint: [`src/my_agents/main.py`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/main.py)
- Workflow controller: [`src/my_agents/controller.py`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/controller.py)
- Agent definitions: [`src/my_agents/config/agents.yaml`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/config/agents.yaml)
- Workflow queues and checkpoints:
  - [`src/my_agents/config/workflows/sourcing.yaml`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/config/workflows/sourcing.yaml)
  - [`src/my_agents/config/workflows/due_diligence.yaml`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/config/workflows/due_diligence.yaml)
  - [`src/my_agents/config/workflows/portfolio.yaml`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/config/workflows/portfolio.yaml)
- Output renderers: [`src/my_agents/renderers`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/renderers)

## Open-Source LLM Configuration

Default config is in [`src/my_agents/config/llm.yaml`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/config/llm.yaml).

Current default:

```yaml
provider: openrouter
model: openrouter/deepseek/deepseek-v3.2
base_url: https://openrouter.ai/api/v1
api_key_env: OPENROUTER_API_KEY
temperature: 0.2
max_tokens: 4096
open_source_only: true
allow_closed_models: false
```

You can change this to another OSS model.

Examples:

OpenRouter OSS model:

```yaml
provider: openrouter
model: openrouter/meta-llama/llama-3.3-70b-instruct
base_url: https://openrouter.ai/api/v1
api_key_env: OPENROUTER_API_KEY
open_source_only: true
allow_closed_models: false
```

Ollama local model:

```yaml
provider: ollama
model: llama3.1:8b
base_url: http://localhost:11434
open_source_only: true
allow_closed_models: false
```

## Environment

Copy [`.env.example`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/.env.example) to `.env` and only add the keys you want to use. The app auto-loads `my_agents/.env` at runtime.

For an OpenRouter-backed open-source model:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

For a fully local Ollama setup, no `.env` key is required by default.

This project does not require embeddings or any closed-model provider out of the box. If you later choose to add embeddings, configure an OSS-compatible embedding model explicitly.

Linear is disabled by default. If you decide to use it later, enable it in [`src/my_agents/config/integrations.yaml`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/config/integrations.yaml) and set `LINEAR_API_KEY`.

## Installation

For a new machine:

```bash
cd /path/to/cloned/repo/my_agents
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

If you prefer `uv`, this also works:

```bash
cd /path/to/cloned/repo/my_agents
uv sync
cp .env.example .env
```

## Running

Create a brief file like this:

```yaml
company_name: Example Fintech
website: https://example.com
sector: fintech
stage: seed
geography: India
one_line: API infrastructure for credit underwriting.
questions:
  - What is differentiated about the underwriting model?
  - Which India-specific regulatory risks matter most?
```

If you use `docs_dir`, v1 accepts only `PDF` and `CSV` files.

From the project folder:

```bash
cd /Users/piyushdev/Documents/Agents/crewAI/my_agents
/Users/piyushdev/Documents/Agents/crewAI/my_agents/.venv/bin/python -m my_agents.main \
  --workflow due_diligence \
  --brief /absolute/path/to/brief.yaml \
  --output-profile ic_memo \
  --approve-mode auto
```

You can override the default sector-based source pack with `--sources-profile`, for example `--sources-profile fintech`.

For a one-pager:

```bash
/Users/piyushdev/Documents/Agents/crewAI/my_agents/.venv/bin/python -m my_agents.main \
  --workflow sourcing \
  --brief /absolute/path/to/brief.yaml \
  --output-profile one_pager
```

For resume:

```bash
/Users/piyushdev/Documents/Agents/crewAI/my_agents/.venv/bin/python -m my_agents.main \
  --resume /absolute/path/to/runs/acme-ventures/2026-01-02_030405
```

## Outputs

Each run creates a versioned folder under `runs/{company_slug}/{timestamp}/` with:
- `report.md`
- `report.pdf` for `ic_memo` and `full_report` when the host machine has WeasyPrint system libraries available
- `one_pager.html` for `one_pager`
- `scorecard.json`
- `sources.json`
- `findings_bundle.json`
- `run_state.json`
- `findings/{agent_name}.json`
