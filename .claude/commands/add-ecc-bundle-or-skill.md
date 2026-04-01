---
name: add-ecc-bundle-or-skill
description: Workflow command scaffold for add-ecc-bundle-or-skill in vc-research_crew.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-ecc-bundle-or-skill

Use this workflow when working on **add-ecc-bundle-or-skill** in `vc-research_crew`.

## Goal

Adds a new ECC bundle or skill for vc-research_crew, including commands, skills, agent configs, and tool metadata.

## Common Files

- `.claude/commands/feature-development-with-tests-and-docs.md`
- `.claude/commands/feature-development.md`
- `.claude/commands/refactoring.md`
- `.claude/skills/vc-research_crew/SKILL.md`
- `.agents/skills/vc-research_crew/SKILL.md`
- `.agents/skills/vc-research_crew/agents/openai.yaml`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Add or update .claude/commands/*.md (feature-development, refactoring, etc.)
- Add or update .claude/skills/vc-research_crew/SKILL.md
- Add or update .agents/skills/vc-research_crew/SKILL.md
- Add or update .agents/skills/vc-research_crew/agents/openai.yaml
- Add or update .claude/ecc-tools.json

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.