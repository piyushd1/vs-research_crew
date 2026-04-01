```markdown
# vc-research_crew Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches the core development patterns, coding conventions, and collaborative workflows used in the `vc-research_crew` Python codebase. The repository is organized for modular agent/skill development, with a focus on maintainability, clear documentation, and robust testing. You'll learn how to contribute new features, refactor code, manage ECC bundles, and update multilingual documentation, all while following established conventions.

---

## Coding Conventions

**File Naming**
- Use `snake_case` for all Python files.
  - Example: `controller_flow.py`, `test_e2e_smoke.py`

**Import Style**
- Use **relative imports** within packages.
  - Example:
    ```python
    from .configuration import AgentConfig
    from ..utilities.helpers import parse_brief
    ```

**Export Style**
- Use **named exports** (explicitly define what is exported).
  - Example:
    ```python
    __all__ = ["AgentController", "AgentConfig"]
    ```

**Commit Messages**
- Follow [Conventional Commits](https://www.conventionalcommits.org/) with these prefixes:
  - `feat`, `fix`, `docs`, `refactor`, `chore`
- Example:
  ```
  feat(controller): add async task dispatch support
  fix(configuration): resolve env var parsing bug
  ```

---

## Workflows

### ECC Bundle Addition

**Trigger:** When onboarding a new skill/agent or updating ECC bundle metadata  
**Command:** `/add-ecc-bundle`

1. Add or update command documentation in `.claude/commands/*.md` (e.g., `feature-development.md`).
2. Add or update identity and tool metadata:
    - `.claude/identity.json`
    - `.claude/ecc-tools.json`
3. Add or update the skill documentation:
    - `.claude/skills/vc-research_crew/SKILL.md`
    - `.agents/skills/vc-research_crew/SKILL.md`
4. Configure the agent:
    - `.agents/skills/vc-research_crew/agents/openai.yaml`
5. Update instincts and agent configs:
    - `.claude/homunculus/instincts/inherited/vc-research_crew-instincts.yaml`
    - `.codex/agents/*.toml`
    - `.codex/AGENTS.md`
    - `.codex/config.toml`

**Example:**
```bash
# Add a new ECC bundle for a skill
/add-ecc-bundle
```

---

### Feature or Refactor with Tests and Docs

**Trigger:** When adding a new feature, refactoring, or fixing code in `my_agents`  
**Command:** `/feature-dev`

1. Edit or create implementation files in `my_agents/src/my_agents/` (e.g., `controller.py`, `llm_policy.py`).
2. Add or update tests in `my_agents/tests/` (e.g., `test_controller_flow.py`).
3. Update supporting files as needed (`pyproject.toml`, `pytest.ini`, etc.).
4. Optionally, update documentation (`my_agents/README.md`).

**Example:**
```python
# src/my_agents/controller.py
def run_controller():
    pass

# tests/test_controller_flow.py
def test_run_controller():
    assert run_controller() is None
```

---

### Core Library Feature or Refactor with Tests

**Trigger:** When adding or refactoring features in the core `crewai` library  
**Command:** `/core-feature-dev`

1. Edit implementation files in `lib/crewai/src/crewai/` (e.g., `llm.py`, `agent/core.py`).
2. Add or update tests in `lib/crewai/tests/` (e.g., `test_llm.py`).
3. Update or add test cassettes in `lib/crewai/tests/cassettes/` if needed.
4. Optionally, update configuration files (`pyproject.toml`).

**Example:**
```python
# src/crewai/llm.py
class LLM:
    def generate(self, prompt):
        return "output"

# tests/test_llm.py
def test_generate():
    llm = LLM()
    assert llm.generate("test") == "output"
```

---

### Documentation Multilingual Update

**Trigger:** When updating or adding documentation in multiple languages  
**Command:** `/update-docs-all-langs`

1. Edit or add documentation in:
    - `docs/en/concepts/*.mdx`
    - `docs/ar/concepts/*.mdx`
    - `docs/ko/concepts/*.mdx`
    - `docs/pt-BR/concepts/*.mdx`
2. Update `docs/docs.json` to reflect new or changed docs.

**Example:**
```markdown
<!-- docs/en/concepts/agent-capabilities.mdx -->
# Agent Capabilities
Agents can perform tasks autonomously...
```

---

## Testing Patterns

- Test files are named with the pattern `*_test.py` and placed alongside or in dedicated `tests/` directories.
- Testing framework is **unknown**, but structure is compatible with `pytest`.
- Tests are written as functions prefixed with `test_`.
- Example:
    ```python
    # tests/test_e2e_smoke.py
    def test_end_to_end_flow():
        result = main()
        assert result.success
    ```

---

## Commands

| Command                | Purpose                                                        |
|------------------------|----------------------------------------------------------------|
| /add-ecc-bundle        | Add or update an ECC bundle for a new skill/agent              |
| /feature-dev           | Implement or refactor a feature in my_agents with tests/docs   |
| /core-feature-dev      | Implement or refactor a feature in the core crewai library     |
| /update-docs-all-langs | Update or add documentation in all supported languages         |

---
```