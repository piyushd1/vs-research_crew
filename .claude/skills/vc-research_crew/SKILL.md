```markdown
# vc-research_crew Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill provides a comprehensive guide to the development patterns, coding conventions, and workflows used in the `vc-research_crew` Python codebase. The repository is organized for modular agent and skill development, with a focus on clarity, maintainability, and extensibility. It employs conventional commit messages, structured workflows for feature and documentation updates, and a consistent approach to testing and code organization.

## Coding Conventions

**File Naming:**
- Use `snake_case` for all Python files.
  - Example: `controller.py`, `llm_policy.py`, `test_controller_flow.py`

**Import Style:**
- Prefer **relative imports** within modules.
  - Example:
    ```python
    from .tools import ToolManager
    from ..renderers.markdown_renderer import MarkdownRenderer
    ```

**Export Style:**
- Use **named exports** (explicitly define what is exported from a module).
  - Example:
    ```python
    __all__ = ["AgentController", "ToolManager"]
    ```

**Commit Messages:**
- Follow the **Conventional Commits** specification.
  - Prefixes: `feat`, `fix`, `docs`, `refactor`, `chore`
  - Example: `feat: add evidence aggregation to controller`

**Directory Structure:**
- Implementation: `src/my_agents/`, `lib/crewai/src/crewai/`
- Tests: `tests/` adjacent to source directories
- Configuration: `pyproject.toml`, `.yaml`, `.json` files as needed

## Workflows

### add-ecc-bundle
**Trigger:** When introducing a new agent or skill ECC bundle to the project  
**Command:** `/add-ecc-bundle`

1. Create or update command documentation in `.claude/commands/*.md` (e.g., `add-ecc-bundle-or-skill.md`).
2. Create or update skill documentation in `.claude/skills/vc-research_crew/SKILL.md` and `.agents/skills/vc-research_crew/SKILL.md`.
3. Configure agent identity in `.agents/skills/vc-research_crew/agents/openai.yaml`.
4. Update identity and ECC tool configuration in `.claude/identity.json` and `.claude/ecc-tools.json`.
5. Update agent definitions in `.codex/agents/*.toml`, `.codex/AGENTS.md`, and `.codex/config.toml`.
6. Update instincts in `.claude/homunculus/instincts/inherited/vc-research_crew-instincts.yaml`.

**Example:**
```bash
# Add a new ECC bundle for a skill
/add-ecc-bundle
```

---

### feature-development-with-tests-and-docs
**Trigger:** When adding or refactoring features in the agent system, including tests and docs  
**Command:** `/feature-dev`

1. Modify implementation files in `my_agents/src/my_agents/` (e.g., `controller.py`, `llm_policy.py`).
2. Update or add corresponding test files in `my_agents/tests/` (e.g., `test_controller_flow.py`).
3. Update `my_agents/pyproject.toml` if dependencies or configuration change.
4. Update or add documentation in `my_agents/README.md` or `docs/*`.

**Example:**
```python
# src/my_agents/controller.py
def aggregate_evidence(evidence_list):
    return [e for e in evidence_list if e.is_valid()]

# tests/test_controller_flow.py
def test_aggregate_evidence():
    assert aggregate_evidence([MockEvidence(valid=True)]) == [MockEvidence(valid=True)]
```

---

### core-library-feature-or-refactor-with-tests
**Trigger:** When adding, refactoring, or fixing features in the core CrewAI library  
**Command:** `/core-feature`

1. Modify implementation files in `lib/crewai/src/crewai/` (e.g., `llm.py`, `agent/core.py`).
2. Update or add tests in `lib/crewai/tests/` and cassettes in `lib/crewai/tests/cassettes/` if needed.
3. Update configuration or dependency files (`lib/crewai/pyproject.toml`, `uv.lock`) as necessary.

**Example:**
```python
# src/crewai/llm.py
class LLM:
    def generate(self, prompt):
        # Implementation here

# tests/test_llm.py
def test_generate():
    llm = LLM()
    assert llm.generate("Hello") is not None
```

---

### documentation-update-with-translations
**Trigger:** When improving or adding documentation, including translations  
**Command:** `/update-docs`

1. Modify or add documentation in `docs/en/concepts/*.mdx`, `docs/ar/concepts/*.mdx`, `docs/ko/concepts/*.mdx`, or `docs/pt-BR/concepts/*.mdx`.
2. Update `docs/docs.json` to reflect new or updated docs.

**Example:**
```mdx
<!-- docs/en/concepts/agent-skills.mdx -->
# Agent Skills
Agents can be extended with custom skills for new capabilities.
```

---

## Testing Patterns

- Test files are named with the pattern `*_test.py` or `test_*.py`.
- Tests are placed in `tests/` directories adjacent to source code.
- The testing framework is not explicitly specified, but tests follow standard Python conventions (likely `pytest` or `unittest`).
- Example test:
    ```python
    def test_controller_initialization():
        controller = AgentController()
        assert controller is not None
    ```

## Commands

| Command           | Purpose                                                        |
|-------------------|----------------------------------------------------------------|
| /add-ecc-bundle   | Add a new agent or skill ECC bundle to the project             |
| /feature-dev      | Develop or refactor a feature with tests and documentation     |
| /core-feature     | Implement or refactor a core library feature with tests        |
| /update-docs      | Update or add documentation, including translations           |
```
