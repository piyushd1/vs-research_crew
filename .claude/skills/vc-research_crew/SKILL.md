```markdown
# vc-research_crew Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the core development patterns, coding conventions, and workflows used in the `vc-research_crew` Python codebase. The repository is designed for research automation and workflow management, with a strong emphasis on configuration-driven logic, modular design, and test-driven development. You'll learn how to add new features, update workflows, manage sector-specific logic, maintain code health, and write effective tests.

---

## Coding Conventions

**File Naming**
- Use `snake_case` for all Python files and directories.
  - Example: `controller.py`, `scorecard_weights.yaml`

**Import Style**
- Use **relative imports** within modules.
  - Example:
    ```python
    from .tools import data_loader
    from .config import configuration
    ```

**Export Style**
- Use **named exports** (explicit function/class definitions).
  - Example:
    ```python
    def run_workflow(...):
        ...
    ```

**Commit Messages**
- Follow **Conventional Commits**: `fix:`, `feat:`, `docs:`, `refactor:`, `chore:`
  - Example: `feat: add sector-specific scorecard logic`

---

## Workflows

### Feature Development, Implementation, Tests & Docs
**Trigger:** When adding a new feature or overhauling an existing system  
**Command:** `/new-feature`

1. Edit or add implementation files in `src/my_agents/` (e.g., `controller.py`, `runner.py`, `tools/`)
2. Edit or add configuration files in `src/my_agents/config/` (e.g., `agents.yaml`, `llm.yaml`, `workflows/`)
3. Edit or add renderer/output files in `src/my_agents/renderers/`
4. Edit or add test files in `my_agents/tests/`
5. Edit or add documentation in `my_agents/README.md` or `my_agents/docs/`

**Example:**
```python
# src/my_agents/controller.py
def new_feature_controller(...):
    ...
```
```yaml
# src/my_agents/config/agents.yaml
new_agent:
  type: research
  ...
```

---

### Add or Update Config-Driven Workflow
**Trigger:** When introducing or modifying a research workflow or process  
**Command:** `/new-workflow`

1. Edit or add workflow YAML files in `src/my_agents/config/workflows/`
2. Edit or add related config files (e.g., `agents.yaml`, `output_profiles/`)
3. Update `controller.py`, `runner.py`, or `schemas.py` to support new workflow logic
4. Edit or add renderer files if output format changes
5. Update or add tests to cover the new/changed workflow

**Example:**
```yaml
# src/my_agents/config/workflows/due_diligence.yaml
steps:
  - gather_data
  - analyze
  - summarize
```
```python
# src/my_agents/controller.py
def run_due_diligence(...):
    ...
```

---

### Add or Update Sector Scorecard or Source
**Trigger:** When supporting a new sector or updating scoring/source logic  
**Command:** `/add-sector`

1. Add or edit YAML files in `src/my_agents/config/scorecard/` or `src/my_agents/config/sources/`
2. Update `configuration.py` or `controller.py` to recognize new sectors
3. Update or add tests to validate sector coverage

**Example:**
```yaml
# src/my_agents/config/scorecard/fintech.yaml
weights:
  growth: 0.4
  risk: 0.3
  innovation: 0.3
```
```python
# src/my_agents/configuration.py
SECTORS = ["fintech", "healthtech", ...]
```

---

### Test-Driven Development: Add Tests for New or Changed Code
**Trigger:** When adding a new feature, fixing a bug, or changing configuration  
**Command:** `/add-test`

1. Edit or add test files in `my_agents/tests/` corresponding to the changed feature or module
2. Update `pytest.ini` or `conftest.py` if new test setup is required
3. Run tests to verify changes

**Example:**
```python
# my_agents/tests/test_controller.py
def test_new_feature_controller():
    assert new_feature_controller(...) == expected_result
```

---

### Code Health or Refactor: Cleanup Unused Code and Fix Defaults
**Trigger:** When cleaning up technical debt or removing obsolete code  
**Command:** `/cleanup-code`

1. Remove unused functions or files in `src/my_agents/`
2. Fix model defaults or configuration in `configuration.py`, `controller.py`, `schemas.py`, etc.
3. Update `pyproject.toml` if entry points or dependencies change
4. Update or add tests to confirm cleanup did not break functionality

**Example:**
```python
# src/my_agents/controller.py
# Remove unused function
# def old_unused_function(...): ...
```

---

## Testing Patterns

- **Test files** are named with the pattern `*_test.py` and located in `my_agents/tests/`.
- The testing framework is not explicitly specified, but `pytest` conventions are followed.
- Use assert statements to validate logic.
- Add or update `pytest.ini` or `conftest.py` for test configuration if needed.

**Example:**
```python
# my_agents/tests/test_runner.py
def test_run_workflow():
    result = run_workflow(...)
    assert result["status"] == "success"
```

---

## Commands

| Command        | Purpose                                                        |
|----------------|----------------------------------------------------------------|
| /new-feature   | Start a new feature, implementation, tests, and docs workflow  |
| /new-workflow  | Add or update a config-driven research workflow                |
| /add-sector    | Add or update sector scorecard or source logic                 |
| /add-test      | Add or update tests for new or changed code                    |
| /cleanup-code  | Remove unused code and fix model/config defaults               |
```
