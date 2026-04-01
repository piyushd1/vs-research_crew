---
name: feature-development-with-tests-and-docs
description: Workflow command scaffold for feature-development-with-tests-and-docs in vc-research_crew.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /feature-development-with-tests-and-docs

Use this workflow when working on **feature-development-with-tests-and-docs** in `vc-research_crew`.

## Goal

Implements a new feature or enhancement, updating both implementation and corresponding tests, sometimes with documentation.

## Common Files

- `my_agents/src/my_agents/controller.py`
- `my_agents/src/my_agents/configuration.py`
- `my_agents/src/my_agents/llm_policy.py`
- `my_agents/src/my_agents/evidence.py`
- `my_agents/src/my_agents/evals/judge.py`
- `my_agents/src/my_agents/integrations/linear_push.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit or add implementation files (e.g. controller.py, configuration.py, llm_policy.py, evidence.py, etc.)
- Update or add corresponding test files (e.g. tests/test_controller_flow.py, tests/test_configuration.py, tests/test_eval_benchmarks.py, etc.)
- Optionally update documentation (e.g. README.md)

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.