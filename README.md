# India-First VC Research Agents

This repository now packages a customized CrewAI project for venture capital research and diligence.

The runnable project lives in [`my_agents/`](/Users/piyushdev/Documents/Agents/crewAI/my_agents). That app is built for:

- India-first VC workflows
- multi-agent due diligence and research
- deterministic report generation
- open-source LLMs only by default
- configurable model backends such as OpenRouter OSS models or local Ollama models

## What This Repo Contains

- [`my_agents/`](/Users/piyushdev/Documents/Agents/crewAI/my_agents): the shareable VC research app
- [`my_agents/src/my_agents/config/agents.yaml`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/config/agents.yaml): specialist VC agent roles
- [`my_agents/src/my_agents/config/workflows/`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/config/workflows): sourcing, due diligence, and portfolio workflows
- [`my_agents/src/my_agents/config/llm.yaml`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/config/llm.yaml): OSS-only model policy and default model settings

## Supported Workflows

- `sourcing`
- `due_diligence`
- `portfolio`

## Supported Outputs

- `ic_memo`
- `full_report`
- `one_pager`

## Model Policy

This project defaults to open-source models only.

By default:

- closed models are rejected
- OpenRouter can be used with open-source models
- Ollama can be used for fully local models
- no embeddings or optional integrations are required unless you explicitly configure them

## Install

Clone the repo, then install the app from the `my_agents` folder:

```bash
cd my_agents
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

If you prefer `uv`:

```bash
cd my_agents
uv sync
cp .env.example .env
```

## Configure

For OpenRouter with an OSS model, add your key to [`my_agents/.env.example`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/.env.example) and save it as `.env`:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

For local Ollama, no API key is required by default.

Model selection lives in [`my_agents/src/my_agents/config/llm.yaml`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/src/my_agents/config/llm.yaml).

## Run

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

Then run:

```bash
cd my_agents
.venv/bin/python -m my_agents.main \
  --workflow due_diligence \
  --brief /absolute/path/to/brief.yaml \
  --output-profile ic_memo \
  --approve-mode auto
```

## Outputs

Each run writes a timestamped folder under `my_agents/runs/{company_slug}/{timestamp}/` with:

- `report.md`
- `report.pdf` for memo/full report runs
- `one_pager.html` for one-pager runs
- `scorecard.json`
- `sources.json`
- `findings_bundle.json`
- `run_state.json`

## Notes

- The app is intentionally configured for open-source model usage unless you explicitly change the policy.
- Linear integration is disabled by default.
- The project README inside [`my_agents/README.md`](/Users/piyushdev/Documents/Agents/crewAI/my_agents/README.md) contains more detailed app-level guidance.
