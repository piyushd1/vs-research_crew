```markdown
# vc-research_crew Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you how to contribute to the `vc-research_crew` Python codebase, which focuses on agent-based research workflows. You'll learn the project's coding conventions, how to structure your code and tests, and how to follow the main development workflows for adding features, updating documentation, refactoring, and more. The repository uses conventional commits, a clear file structure, and emphasizes maintaining both code and documentation quality.

---

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for all Python files and modules.
  ```
  # Good
  controller.py
  llm_policy.py

  # Bad
  Controller.py
  llmPolicy.py
  ```

- **Import Style:**  
  Use *relative imports* within modules.
  ```python
  # In my_agents/src/my_agents/controller.py
  from .configuration import Config
  ```

- **Export Style:**  
  Use *named exports* (explicitly define what is exported).
  ```python
  # In my_agents/src/my_agents/tools/custom_tool.py
  def custom_tool():
      pass

  __all__ = ["custom_tool"]
  ```

- **Commit Messages:**  
  Follow [Conventional Commits](https://www.conventionalcommits.org/):
  ```
  feat: add new agent evaluation workflow
  fix: correct bug in evidence aggregation
  docs: update skills documentation
  refactor: simplify controller logic
  chore: update dependencies
  ```

---

## Workflows

### Feature Development with Tests and Docs
**Trigger:** When adding or improving a feature  
**Command:** `/feature`

1. Edit or add implementation files (e.g., `controller.py`, `configuration.py`, etc.).
2. Update or add corresponding test files (e.g., `tests/test_controller_flow.py`).
3. Optionally update documentation (e.g., `README.md`).

**Example:**
```bash
# Add a new tool
vim my_agents/src/my_agents/tools/custom_tool.py

# Write its test
vim my_agents/tests/test_quick_mode.py

# Update docs if needed
vim my_agents/README.md
```

---

### Add or Update Sample Briefs and E2E Tests
**Trigger:** When adding new VC research scenarios and validating them end-to-end  
**Command:** `/add-brief`

1. Add or update `sample_briefs/*.yaml` files.
2. Add or update `tests/test_e2e_smoke.py` to cover new scenarios.

**Example:**
```bash
# Add a new research scenario
vim my_agents/sample_briefs/new_scenario.yaml

# Write or update the E2E smoke test
vim my_agents/tests/test_e2e_smoke.py
```

---

### Documentation Core Concepts Update with Translations
**Trigger:** When updating documentation for core concepts and translations  
**Command:** `/update-docs`

1. Edit docs in `docs/en/concepts/*.mdx`.
2. Edit or add translations in `docs/ar/concepts/*.mdx`, `docs/ko/concepts/*.mdx`, `docs/pt-BR/concepts/*.mdx`.
3. Update `docs/docs.json` to reflect changes.

**Example:**
```bash
# Update English docs
vim docs/en/concepts/skills.mdx

# Update Arabic translation
vim docs/ar/concepts/skills.mdx

# Update docs index
vim docs/docs.json
```

---

### Refactor or Code Health Cleanup with Tests
**Trigger:** When improving maintainability or removing obsolete code  
**Command:** `/refactor`

1. Edit or remove implementation files (e.g., remove functions, refactor classes).
2. Update or remove corresponding test files.

**Example:**
```bash
# Refactor main logic
vim my_agents/src/my_agents/main.py

# Remove obsolete test
rm my_agents/tests/test_obsolete.py
```

---

### Dependency or Lockfile Update
**Trigger:** When updating dependencies or fixing compatibility  
**Command:** `/update-deps`

1. Edit `pyproject.toml` or other dependency files.
2. Update `uv.lock` as needed.

**Example:**
```bash
# Add a new dependency
vim my_agents/pyproject.toml

# Update lockfile
uv pip sync
```

---

### Merge Main or Upstream into Feature Branch
**Trigger:** When syncing your branch with main or upstream  
**Command:** `/merge-main`

1. Merge `main` or `upstream` branch.
2. Resolve conflicts and update files across docs, src, and tests.

**Example:**
```bash
git checkout my-feature-branch
git merge main
# Resolve conflicts in docs, src, and tests as needed
```

---

## Testing Patterns

- **Test File Naming:**  
  Test files are named as `*_test.py` and placed in the `tests/` directory.
  ```
  my_agents/tests/test_controller_flow.py
  my_agents/tests/test_eval_benchmarks.py
  ```

- **Test Structure:**  
  Each test file targets a specific module or workflow.  
  Testing framework is not explicitly specified, but standard Python test patterns apply.

- **Example Test:**
  ```python
  # my_agents/tests/test_controller_flow.py
  def test_controller_initialization():
      from my_agents.controller import Controller
      ctrl = Controller()
      assert ctrl.is_ready()
  ```

---

## Commands

| Command      | Purpose                                                         |
|--------------|-----------------------------------------------------------------|
| /feature     | Start a new feature with tests and optional docs                |
| /add-brief   | Add or update sample briefs and end-to-end tests                |
| /update-docs | Update documentation and translations for core concepts         |
| /refactor    | Refactor code and update or remove related tests                |
| /update-deps | Update dependencies or lockfiles                                |
| /merge-main  | Merge main or upstream into your feature branch                 |
```
