# AI Architect: Guidelines

This checklist outlines key software development lifecycle best practices tailored for transitioning from a Data Science background to building complex AI systems. It uses the current `app-personal-finance` project (Python backend/Streamlit frontend) and the planned "DataWizard" project (Python backend/React frontend) as examples.

---

## 1. Modular Design & Separation of Concerns

**Goal:** Break down the system into logical, independent components with clear responsibilities for better maintainability, testability, and reusability.

**Key Practices:**

*   **Backend (LangGraph/FastAPI):**
    *   **Agent Logic vs. Infrastructure:** Separate graph definitions (e.g., `graph.py`) from server setup (e.g., `server.py`).
        *   _Status (Current): Done_
    *   **Nodes:** Isolate each agent step into its own function/module.
        *   _Example (Refactor Plan):_ Move `classify_query_node` to `src/agent/nodes/classify_query_node.py`.
        *   _Status: Next Step_
    *   **Prompts:** Separate LLM prompts (e.g., in `.yaml` files) from Python code.
        *   _Example (Refactor Plan):_ Store `classify_query` prompt in `src/agent/prompts/classify_query_prompts.yaml`.
        *   _Status: Next Step_
    *   **Agent State:** Define state clearly (e.g., `state.py`) focusing on data transfer.
        *   _Status (Current): Done, needs multi-agent refinement_
    *   **Utilities:** Create shared utility modules (DB connection, config, prompt loading).
        *   _Example:_ `src/agent/utils/prompt_loader.py`.
    *   **Multi-Agent Structure (DA):** Use separate directories per agent.
        *   _Example (DA):_ `src/agents/super_agent/`, `src/agents/data_analyst/`.

*   **Frontend (Streamlit - Current Project):**
    *   **Tabs/Pages:** Separate UI sections into modules.
        *   _Example:_ `streamlit/tabs/assistant.py`.
        *   _Status (Current): Done_
    *   **UI Logic vs. API Calls:** Keep UI rendering code separate from backend communication code.
        *   _Example:_ `render()` vs. `call_assistant_api()` in `assistant.py`.
        *   _Status (Current): Done_
    *   **Utilities:** Separate reusable UI logic (styling, etc.).
        *   _Example:_ `streamlit/style_utils.py`.
        *   _Status (Current): Done_

*   **Frontend (React - DataWizard):**
    *   **Components:** Build small, reusable UI pieces.
        *   _Example (DA):_ `src/components/Chat/ChatInput.jsx`.
    *   **Containers/Pages:** Assemble components into views.
        *   _Example (DA):_ `src/pages/AssistantPage.jsx`.
    *   **API Service Layer:** Centralize backend communication logic.
        *   _Example (DA):_ `src/services/assistantAPI.js`.
    *   **State Management:** Separate UI state logic (Context, Zustand, etc.).
    *   **Hooks:** Create custom hooks for reusable logic.
        *   _Example (DA):_ `src/hooks/useAssistantChat.js`.

---

## 2. Testing Strategy & Automation

**Goal:** Ensure code correctness, prevent regressions, enable safe refactoring, and automate checks.

**Key Practices:**

*   **Testing Levels:**
    *   **Unit Tests:** Test smallest units in isolation. **Focus here first.** Mock external dependencies (LLMs, DBs, APIs). Use `pytest` and `pytest-mock` or `unittest.mock`.
        *   _Example (Current):_ `tests/unit_tests/test_nodes.py` mocking `LLM.invoke`.
        *   _Status: Next Step_
    *   **Integration Tests:** Test interactions between components or API endpoints. Mock external systems selectively.
        *   _Example (Backend):_ Test `graph.invoke` flow with mocked LLM/DB.
        *   _Example (API):_ Test `/assistant/invoke` endpoint using `httpx`, mocking `graph.invoke`.
        *   _Example (DA Frontend):_ Use React Testing Library with mock API services.
        *   _Status: Next Step (Backend/API), Future (DA Frontend)_
    *   **End-to-End (E2E) Tests:** Test full user flows. Tools: Cypress, Playwright.
        *   _Status: Lower priority initially_
*   **Test Automation:**
    *   **Test Runner:** Use `pytest`.
    *   **CI/CD:** Use GitHub Actions (or similar) to run tests automatically on push/PR.
        *   _Status (Current): Basic workflows exist, need review/update._
    *   **Test Coverage:** Measure using `pytest-cov` (optional but good).
*   **Testing Agentic/LLM Systems:**
    *   **Mocking:** Mock LLM calls for deterministic unit/integration tests.
    *   **Focus on Logic:** Test the code *around* LLM calls (state updates, error handling).
    *   **Validate Interfaces/Types:** Check if nodes produce the expected *type* of output.
    *   **LLM Evals (Advanced):** LangSmith Evals, Ragas, etc., for testing LLM quality.
        *   _Status: Future (DA)_

---

## 3. Git Workflow Best Practices

**Goal:** Maintain clean history, facilitate collaboration, prevent data loss.

**Key Practices:**

*   **Branching Strategy:**
    *   `main`: Stable, deployable code. Protect it.
    *   `feature/<name>`: For new features/refactoring. Branch off `main`.
    *   `fix/<name>`: For bug fixes. Branch off `main`.
    *   *Status (Current): Using `main` and `feature/agentic-ai` correctly._
*   **Commits:**
    *   **Atomic:** Single logical change per commit.
    *   **Descriptive Messages:** Use Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`). Explain the 'why'.
        *   _Status: Practice Continuously_
*   **Merging:**
    *   Merge features/fixes back to `main` via Pull Requests.
    *   Keep branches updated with `main` (`git pull origin main`) to minimize conflicts.
*   **Pull Requests (PRs):**
    *   Use even solo for self-review and history. Clear descriptions.
*   **.gitignore:**
    *   Ignore virtual envs (`.venv/`), caches (`__pycache__/`), secrets (`.env`), logs (`*.log`), OS files (`.DS_Store`), etc.
        *   _Status: Review/Update Needed_

---

## 4. Coding Best Practices (Quality & Automation)

**Goal:** Write clean, readable, maintainable, less error-prone code; automate checks.

**Key Practices:**

*   **Code Quality Tools (Setup in `pyproject.toml`):**
    *   **Linter (`Ruff`):** Style errors, potential bugs.
    *   **Formatter (`Black` or `Ruff format`):** Consistent code style.
    *   **Type Checker (`mypy`):** Verify type hints.
        *   _Status: Next Step (Setup & Configure)_
*   **Automation (`pre-commit` framework):**
    *   Run linters/formatters/type checkers automatically before commit.
    *   Setup: `pip install pre-commit`, create `.pre-commit-config.yaml`, run `pre-commit install`.
        *   _Status: Next Step (Setup & Configure)_
*   **Logging (`logging` module):**
    *   Use instead of `print()` for backend/library code.
    *   Use appropriate levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
    *   Include context in messages. Configure centrally.
        *   _Status (Current): Basic usage exists, needs refinement._
*   **Docstrings:**
    *   Use a standard format (Google Style recommended).
    *   Document public modules, classes, functions (purpose, Args, Returns, Raises).
        *   _Status: Next Step (Add/Improve)_
*   **Configuration Management:**
    *   Avoid hardcoding values (keys, paths, model names).
    *   Use `.env` + `python-dotenv` for secrets/environment settings.
    *   Load config centrally at startup (e.g., in `config.py` or app entry point). Pydantic `BaseSettings` is an option for structure.
        *   _Status (Current): Partially done, needs consolidation._

---

## 5. UI/UX Best Practices (Streamlit & React)

**Goal:** Create an intuitive, responsive, informative, and pleasant user interface.

**Key Practices:**

*   **Responsiveness:** UI adapts to different screen sizes.
    *   *Streamlit:* Use `st.columns`, containers. Test different widths.
    *   *React (DA):* Use CSS frameworks (MUI Grid), Flexbox/Grid, media queries. Test in dev tools.
*   **Clarity & Feedback:**
    *   Indicate application state (loading, thinking). Use `st.spinner`, toasts, loading indicators.
    *   Provide immediate feedback on user actions.
    *   Handle errors gracefully in the UI. Explain the issue and next steps if possible.
        *   _Status (Current): Basic feedback/error handling exists._
*   **Consistency:** Uniform styling, terminology, layout patterns. (Component libraries help).
*   **Accessibility (a11y):** Design for users with disabilities (color contrast, keyboard nav). *(Advanced)*
*   **Performance:** Optimize load times. Minimize backend delays. (Code splitting, memoization in React).
*   **"Wow" Factor (DA - React):**
    *   **Visualize Agent State/Steps:** Show which agent/node is active.
    *   **Streaming Responses:** Display LLM outputs (text, code) in real-time.
    *   **Interactive Charts:** Leverage Plotly.js interactivity.
    *   **Clear Process Output:** Show intermediate DSA results (feature lists, model params, metrics).

---

**Summary of Immediate Next Steps (on `feature/agentic-ai` branch):**

1.  **Refactoring:** Implement the `nodes/` and `prompts/` modularization.
2.  **Testing Setup:** Set up `pytest`, create initial unit tests (mocking IO) for existing nodes, and basic API integration tests.
3.  **Code Quality Setup:** Configure `Ruff`, `Black`/`Ruff format`, `mypy` in `pyproject.toml` and set up `pre-commit` hooks.
4.  **Docs & Logging:** Improve docstrings and add more contextual logging.
5.  **Git:** Ensure `.gitignore` is comprehensive. Continue using feature branches and descriptive commits. Start using PRs (optional).