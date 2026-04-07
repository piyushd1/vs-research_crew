---
name: feature-development-implementation-tests-docs
description: Workflow command scaffold for feature-development-implementation-tests-docs in vc-research_crew.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /feature-development-implementation-tests-docs

Use this workflow when working on **feature-development-implementation-tests-docs** in `vc-research_crew`.

## Goal

Implements a new feature or major improvement, updates implementation, adds or updates tests, and updates documentation/readme.

## Common Files

- `my_agents/src/my_agents/controller.py`
- `my_agents/src/my_agents/runner.py`
- `my_agents/src/my_agents/tools/`
- `my_agents/src/my_agents/config/`
- `my_agents/src/my_agents/renderers/`
- `my_agents/tests/`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit or add implementation files in src/my_agents/ (e.g., controller.py, runner.py, tools/)
- Edit or add configuration files in src/my_agents/config/ (e.g., agents.yaml, llm.yaml, workflows/)
- Edit or add renderer or output files in src/my_agents/renderers/
- Edit or add test files in my_agents/tests/
- Edit or add documentation files in my_agents/README.md or my_agents/docs/

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.