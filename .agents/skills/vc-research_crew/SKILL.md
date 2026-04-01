```markdown
# vc-research_crew Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the core development patterns, coding conventions, and workflows used in the `vc-research_crew` Python codebase. The repository is organized for collaborative agent and tool development, with a focus on modular skills, clear documentation, and robust testing. It leverages conventional commit messages, snake_case file naming, and a set of repeatable workflows for adding features, updating documentation, and maintaining code quality.

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for all Python files and modules.
  ```
  # Good
  controller.py
  one_pager_renderer.py

  # Bad
  Controller.py
  onePagerRenderer.py
  ```

- **Import Style:**  
  Use relative imports within packages.
  ```python
  # Good
  from .configuration import Config
  from .evals import judge

  # Bad
  import configuration
  from my_agents.evals import judge
  ```

- **Export Style:**  
  Use named exports; avoid wildcard imports.
  ```python
  # Good
  def my_function():
      pass

  __all__ = ["my_function"]
  ```

- **Commit Messages:**  
  Follow [Conventional Commits](https://www.conventionalcommits.org/):
  - Prefixes: `feat`, `fix`, `docs`, `refactor`, `chore`
  - Example:  
    ```
    feat: add linear integration for push notifications
    fix: correct evidence schema validation
    docs: update agent capabilities documentation
    ```

## Workflows

### add-ecc-bundle-or-skill
**Trigger:** When onboarding or updating a new skill/bundle for `vc-research_crew` in the ECC system  
**Command:** `/add-ecc-bundle`

1. Add or update `.claude/commands/*.md` for feature development or refactoring.
2. Add or update `.claude/skills/vc-research_crew/SKILL.md` with skill documentation.
3. Add or update `.agents/skills/vc-research_crew/SKILL.md` for agent-specific skill docs.
4. Add or update `.agents/skills/vc-research_crew/agents/openai.yaml` for agent configuration.
5. Update `.claude/ecc-tools.json` and `.claude/identity.json` as needed.
6. Update or add `.codex/agents/*.toml` (e.g., `docs-researcher`, `explorer`, `reviewer`).
7. Update `.codex/AGENTS.md` and `.codex/config.toml`.
8. Update `.claude/homunculus/instincts/inherited/vc-research_crew-instincts.yaml`.

**Example:**
```bash
/add-ecc-bundle
# Then follow the steps above to update all relevant files.
```

---

### feature-development-with-tests-and-docs
**Trigger:** When adding a new feature or refactoring code, ensuring tests and docs are updated  
**Command:** `/feature-dev`

1. Modify implementation files (e.g., `controller.py`, `configuration.py`, etc.).
2. Update or add corresponding test files (e.g., `tests/test_controller_flow.py`).
3. Update or add documentation (e.g., `README.md`, `SKILL.md`, or docs/*).
4. Update project configuration if needed (e.g., `pyproject.toml`, `uv.lock`).

**Example:**
```python
# src/my_agents/controller.py
def new_feature():
    pass

# tests/test_controller_flow.py
def test_new_feature():
    assert new_feature() is None
```

---

### documentation-and-translation-update
**Trigger:** When improving or adding documentation, including translations  
**Command:** `/update-docs`

1. Edit or add documentation files in `docs/en/concepts/*.mdx`.
2. Add or update translations in `docs/ar/concepts/*.mdx`, `docs/ko/concepts/*.mdx`, `docs/pt-BR/concepts/*.mdx`.
3. Update `docs/docs.json` to reflect new or changed docs.

**Example:**
```bash
/update-docs
# Then edit docs/en/concepts/skills.mdx and docs/ar/concepts/skills.mdx as needed.
```

---

### refactor-or-cleanup-with-tests
**Trigger:** When cleaning up code, removing unused functions, or refactoring for maintainability  
**Command:** `/refactor`

1. Modify or remove implementation files to clean up or refactor code.
2. Update or remove related test files to match code changes.
3. Update configuration files if necessary.

**Example:**
```python
# Before
def unused_function():
    pass

# After (removed unused_function)
```
Update or remove `tests/test_controller_flow.py` if it referenced the removed function.

---

## Testing Patterns

- **Test File Naming:**  
  Test files follow the pattern `*_test.py` and are located in the `tests/` directory.
  ```
  tests/test_controller_flow.py
  tests/test_configuration.py
  ```

- **Test Framework:**  
  The specific test framework is not specified, but tests are written as standalone functions, compatible with `pytest`.

- **Test Example:**
  ```python
  # tests/test_controller_flow.py
  def test_controller_initialization():
      controller = Controller()
      assert controller is not None
  ```

## Commands

| Command           | Purpose                                                        |
|-------------------|----------------------------------------------------------------|
| /add-ecc-bundle   | Add or update an ECC bundle or skill for `vc-research_crew`    |
| /feature-dev      | Start feature development with tests and documentation         |
| /update-docs      | Update or add documentation and translations                   |
| /refactor         | Refactor codebase and update/remove related tests              |
```
