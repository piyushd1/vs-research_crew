```markdown
# vc-research_crew Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the core development patterns, coding conventions, and collaborative workflows used in the `vc-research_crew` Python codebase. You'll learn how to contribute new features, refactor code, add or update evaluation pipelines, localize documentation, and improve test coverage using structured, repeatable processes. The repository emphasizes maintainable code, clear commit messages, and robust testing practices.

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for all Python files.
  ```
  # Good
  agent_utils.py
  eval_benchmarks.py

  # Bad
  AgentUtils.py
  evalBenchmarks.py
  ```

- **Import Style:**  
  Use **relative imports** within packages.
  ```python
  # In my_agents/src/my_agents/agent_utils.py
  from .base_agent import BaseAgent
  ```

- **Export Style:**  
  Use **named exports** (i.e., define `__all__` or explicitly import in `__init__.py`).
  ```python
  # In __init__.py
  from .agent_utils import AgentUtils
  __all__ = ["AgentUtils"]
  ```

- **Commit Messages:**  
  Follow [Conventional Commits](https://www.conventionalcommits.org/) with these prefixes:
    - `feat`: New features
    - `fix`: Bug fixes
    - `docs`: Documentation changes
    - `refactor`: Code improvements/refactoring
    - `chore`: Maintenance tasks

  Example:
  ```
  feat: add agent evaluation pipeline for LLM-as-a-judge
  ```

## Workflows

### Feature Development with Tests and Docs
**Trigger:** When adding a new feature with tests and documentation  
**Command:** `/feature`

1. Implement or modify feature logic in `src/` files.
2. Add or update tests in `tests/` files.
3. Update or add documentation in `README.md` or `docs/`.

**Example:**
```python
# src/my_agents/new_feature.py
def new_feature():
    pass
```
```python
# tests/test_new_feature.py
from my_agents.new_feature import new_feature

def test_new_feature():
    assert new_feature() is None
```
Update `README.md` with usage instructions.

---

### Refactor or Code Health Sweep
**Trigger:** When cleaning up, refactoring, or improving code health  
**Command:** `/refactor`

1. Refactor or remove code in `src/` files.
2. Update or remove related test files.
3. Update configuration or project files if needed.

**Example:**
```python
# Refactor function in src/my_agents/agent_utils.py
def improved_function():
    # improved logic
    pass
```
Update or remove corresponding tests in `tests/`.

---

### Add or Update Evaluation Pipeline
**Trigger:** When implementing or improving evaluation/judging pipelines  
**Command:** `/add-eval-pipeline`

1. Add or update evaluation logic in `src/my_agents/evals/` and related files.
2. Update CLI/main entrypoints as needed.
3. Add or update tests for evaluation logic.

**Example:**
```python
# src/my_agents/evals/new_eval.py
def evaluate_agent(agent):
    # evaluation logic
    pass
```
Update `main.py` to include new evaluation hooks.

---

### Documentation Localization Update
**Trigger:** When updating or adding documentation and translations  
**Command:** `/update-docs`

1. Edit or add `.mdx` files in `docs/en/`, `docs/ar/`, `docs/ko/`, `docs/pt-BR/`.
2. Update `docs/docs.json` for navigation.
3. Update or add cross-references as needed.

**Example:**
```mdx
<!-- docs/en/concepts/new_feature.mdx -->
# New Feature
Description in English.
```
Update `docs/docs.json` to include the new page.

---

### Test Addition or Update
**Trigger:** When adding or improving test coverage  
**Command:** `/add-test`

1. Add or update test files in `tests/`.
2. Add sample data or configuration if needed.

**Example:**
```python
# tests/test_new_feature.py
def test_new_feature():
    assert True
```
Add sample YAML to `sample_briefs/` if required.

---

## Testing Patterns

- **Test File Naming:**  
  All test files use the pattern `*_test.py` and are located in `my_agents/tests/`.

- **Test Structure:**  
  Tests are written as functions, typically using `assert` statements.
  ```python
  # my_agents/tests/test_eval_benchmarks.py
  def test_eval_benchmark():
      result = eval_benchmark()
      assert result is not None
  ```

- **Sample Data:**  
  Place any sample YAML data in `my_agents/sample_briefs/` for use in tests.

- **Test Framework:**  
  No specific framework detected, but compatible with `pytest` conventions.

## Commands

| Command            | Purpose                                                       |
|--------------------|---------------------------------------------------------------|
| /feature           | Start a new feature with tests and documentation              |
| /refactor          | Refactor or clean up code and update related tests/config     |
| /add-eval-pipeline | Add or update evaluation (LLM-as-a-judge) pipelines and tests |
| /update-docs       | Add or update documentation and translations                  |
| /add-test          | Add or improve test coverage                                  |
```
