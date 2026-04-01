---
name: add-ecc-bundle
description: Workflow command scaffold for add-ecc-bundle in vc-research_crew.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-ecc-bundle

Use this workflow when working on **add-ecc-bundle** in `vc-research_crew`.

## Goal

Adds a new ECC bundle for an agent or skill, including commands, skills, identity, and configuration files.

## Common Files

- `.claude/commands/*.md`
- `.claude/skills/vc-research_crew/SKILL.md`
- `.agents/skills/vc-research_crew/SKILL.md`
- `.agents/skills/vc-research_crew/agents/openai.yaml`
- `.claude/identity.json`
- `.claude/ecc-tools.json`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Create or update .claude/commands/*.md (e.g., add-ecc-bundle-or-skill.md, feature-development.md, refactoring.md, feature-development-with-tests-and-docs.md)
- Create or update .claude/skills/vc-research_crew/SKILL.md
- Create or update .agents/skills/vc-research_crew/SKILL.md
- Create or update .agents/skills/vc-research_crew/agents/openai.yaml
- Create or update .claude/identity.json

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.