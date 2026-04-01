```markdown
# vc-research_crew Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the core development patterns, coding conventions, and collaborative workflows used in the `vc-research_crew` Python codebase. You'll learn how to add features, refactor code, optimize performance, write and update tests, and contribute documentation—including translations—using clear, repeatable steps and standardized commands.

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for all Python files.  
  _Example:_  
  ```
  controller.py
  llm_policy.py
  test_controller_flow.py
  ```

- **Import Style:**  
  Use **relative imports** within packages.  
  _Example:_  
  ```python
  from .renderers import MarkdownRenderer
  from .tools import summarize_text
  ```

- **Export Style:**  
  Use **named exports** (explicit function, class, or variable names).  
  _Example:_  
  ```python
  def run_controller():
      ...

  class LLMPolicy:
      ...
  ```

- **Commit Messages:**  
  Use **conventional commit** prefixes: `feat`, `fix`, `docs`, `refactor`, `chore`.  
  _Example:_  
  ```
  feat: add support for multi-agent workflows
  fix: correct evidence aggregation bug in controller
  docs: update README with new usage example
  ```

## Workflows

### Feature Development with Tests and Docs
**Trigger:** When adding a new capability, workflow, or feature  
**Command:** `/feature`

1. Edit or create implementation files in `src/` (e.g., `controller.py`, `llm_policy.py`, `renderers/`, `tools/`).
2. Update or add corresponding test files in `tests/` (e.g., `test_controller_flow.py`).
3. Update documentation or configuration files if needed (e.g., `README.md`, `pyproject.toml`, `pytest.ini`).
4. Add or update sample data or config (e.g., `sample_briefs/`).
5. Commit all related changes together.

_Code Example:_
```python
# my_agents/src/my_agents/controller.py
def new_feature():
    pass

# my_agents/tests/test_controller_flow.py
def test_new_feature():
    assert new_feature() is None
```

---

### Refactor or Code Health with Tests
**Trigger:** When cleaning up, optimizing, or modernizing code while ensuring test coverage  
**Command:** `/refactor`

1. Edit or remove code in `src/` (e.g., remove unused functions, update class structure).
2. Update or add corresponding test files in `tests/`.
3. Update configuration or dependency files if needed (e.g., `pyproject.toml`).
4. Commit all related changes together.

---

### Performance Optimization
**Trigger:** When improving runtime efficiency of a function or workflow  
**Command:** `/optimize`

1. Edit implementation files to optimize code (e.g., add caching, refactor loops).
2. Update or add tests to verify performance or correctness.
3. Commit all related changes together.

_Code Example:_
```python
# my_agents/src/my_agents/controller.py
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_computation(x):
    ...
```

---

### Add or Update Tests
**Trigger:** When increasing test coverage or verifying new/changed behavior  
**Command:** `/test`

1. Create or update test files in `tests/`.
2. Edit implementation files if necessary to support testing.
3. Commit test and code changes together.

_Code Example:_
```python
# my_agents/tests/test_eval_benchmarks.py
def test_eval_edge_case():
    ...
```

---

### Documentation Update with Translation
**Trigger:** When documenting a new feature or improving existing documentation, including translations  
**Command:** `/docs`

1. Edit or create documentation files in `docs/en/`, `docs/ar/`, `docs/ko/`, `docs/pt-BR/`.
2. Update `docs/docs.json` for navigation.
3. Commit all documentation changes together.

---

## Testing Patterns

- **Test File Naming:**  
  Test files use the pattern `*_test.py` and are located in `tests/` directories.

- **Testing Framework:**  
  No specific framework detected, but structure is compatible with `pytest`.

- **Test Example:**  
  ```python
  # my_agents/tests/test_quick_mode.py
  def test_quick_mode_runs():
      result = quick_mode()
      assert result is not None
  ```

## Commands

| Command    | Purpose                                                    |
|------------|------------------------------------------------------------|
| /feature   | Start a new feature with tests and docs                    |
| /refactor  | Refactor code and update tests                             |
| /optimize  | Optimize code for performance                              |
| /test      | Add or update tests                                        |
| /docs      | Update documentation, including translations               |
```