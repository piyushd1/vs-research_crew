```markdown
# vc-research_crew Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill provides a comprehensive guide to contributing to the `vc-research_crew` Python codebase. It covers coding conventions, commit patterns, and the main workflows for feature development, core library updates, ECC bundle management, and documentation updates. The repository is structured for collaborative, test-driven development, with a focus on modularity and clarity.

## Coding Conventions

- **File Naming:** Use `snake_case` for all Python files.
  - Example: `controller.py`, `test_controller_flow.py`
- **Import Style:** Use relative imports within packages.
  - Example:
    ```python
    from .configuration import Config
    from ..integrations.linear_push import LinearPush
    ```
- **Export Style:** Use named exports; avoid wildcard imports.
  - Example:
    ```python
    __all__ = ["Controller", "Config"]
    ```
- **Commit Messages:** Follow [Conventional Commits](https://www.conventionalcommits.org/) with prefixes:
  - `feat`, `fix`, `docs`, `refactor`, `chore`
  - Example: `feat: add evidence aggregation to controller`
- **Code Structure:** Organize code into logical modules (e.g., `my_agents/src/my_agents/`, `lib/crewai/src/crewai/`).

## Workflows

### ECC Bundle Addition or Update
**Trigger:** When onboarding or updating the `vc-research_crew` ECC bundle and its configuration  
**Command:** `/add-ecc-bundle`

1. Add or update `.claude/commands/*.md` files (e.g., feature-development, refactoring).
2. Add or update `.claude/skills/vc-research_crew/SKILL.md`.
3. Add or update `.agents/skills/vc-research_crew/SKILL.md`.
4. Add or update `.agents/skills/vc-research_crew/agents/openai.yaml`.
5. Add or update `.claude/ecc-tools.json` and `.claude/identity.json`.
6. Add or update `.codex/agents/*.toml` and `.codex/AGENTS.md`.
7. Update `.codex/config.toml` as needed.
8. Add or update `.claude/homunculus/instincts/inherited/vc-research_crew-instincts.yaml`.

**Example:**
```bash
/add-ecc-bundle
```

---

### Feature Development with Tests and Docs
**Trigger:** When adding or refactoring features in `my_agents` and ensuring they are tested  
**Command:** `/feature-dev`

1. Modify implementation files in `my_agents/src/my_agents/` (e.g., `controller.py`, `configuration.py`).
2. Update or add corresponding test files in `my_agents/tests/` (e.g., `test_controller_flow.py`).
3. Optionally update `pyproject.toml` or related configuration.
4. Optionally update documentation files (`README.md`, `SKILL.md`).

**Example:**
```python
# my_agents/src/my_agents/controller.py
class Controller:
    def run(self):
        pass

# my_agents/tests/test_controller_flow.py
def test_controller_runs():
    ctrl = Controller()
    assert ctrl.run() is None
```
```bash
/feature-dev
```

---

### Core Library Feature or Refactor with Tests
**Trigger:** When adding, refactoring, or fixing features in the CrewAI core library and ensuring correctness with tests  
**Command:** `/core-feature`

1. Modify implementation files in `lib/crewai/src/crewai/` (e.g., `llm.py`, `agent/core.py`).
2. Update or add test files in `lib/crewai/tests/` (e.g., `test_llm.py`, `test_agent.py`).
3. Optionally update `pyproject.toml` or related config.
4. Optionally update cassettes or test fixtures.

**Example:**
```python
# lib/crewai/src/crewai/llm.py
class LLM:
    def complete(self, prompt):
        return "response"

# lib/crewai/tests/test_llm.py
def test_llm_complete():
    llm = LLM()
    assert llm.complete("Hello") == "response"
```
```bash
/core-feature
```

---

### Documentation Multilingual Update
**Trigger:** When adding or updating documentation for core concepts in multiple languages  
**Command:** `/update-docs`

1. Modify or add documentation files in `docs/en/concepts/`, `docs/ar/concepts/`, `docs/ko/concepts/`, `docs/pt-BR/concepts/`.
2. Update `docs/docs.json` for navigation.

**Example:**
```markdown
<!-- docs/en/concepts/skills.mdx -->
# Skills
Skills are modular capabilities for agents.
```
```bash
/update-docs
```

## Testing Patterns

- **Test File Naming:** Use `*_test.py` or `test_*.py` for test files.
  - Example: `test_controller_flow.py`, `test_llm.py`
- **Test Framework:** Not explicitly specified; use standard Python testing frameworks (e.g., `pytest` or `unittest`).
- **Test Location:** Place tests in `tests/` directories adjacent to the code under test.
- **Test Example:**
  ```python
  def test_example():
      assert 1 + 1 == 2
  ```

## Commands

| Command           | Purpose                                                        |
|-------------------|----------------------------------------------------------------|
| /add-ecc-bundle   | Add or update the ECC bundle and related configuration files   |
| /feature-dev      | Start feature development with tests and documentation         |
| /core-feature     | Add/refactor core library features with corresponding tests    |
| /update-docs      | Update or add multilingual documentation                      |
```
