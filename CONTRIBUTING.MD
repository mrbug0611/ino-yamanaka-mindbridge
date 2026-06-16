# Contributing to MindBridge

I appreciate your interest in contributing. This document covers everything you need to get started: repository conventions, branch workflow, testing requirements, and what to expect from code review.

---

## Table of Contents

- [Development Setup](#development-setup)
- [Branch & Commit Conventions](#branch--commit-conventions)
- [Backend Guidelines](#backend-guidelines)
- [Frontend Guidelines](#frontend-guidelines)
- [Testing](#testing)
- [Opening a Pull Request](#opening-a-pull-request)
- [Code Review](#code-review)
- [Reporting Issues](#reporting-issues)

---

## Development Setup

Follow the **Local Development** section in the [README](./README.md) to get a backend and frontend running without Docker.

Minimum requirements:

- Python 3.10+
- Node.js 20+
- PostgreSQL 16 (or run `docker compose up db` to start only the database)

Install pre-commit tooling (optional but recommended):

```bash
pip install ruff pytest pytest-asyncio
cd frontend && npm install
```

---

## Branch & Commit Conventions

| Branch prefix | Purpose |
|---|---|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `chore/` | Tooling, dependencies, docs |
| `refactor/` | Code restructuring without behaviour change |

Keep commits small and focused. Write commit messages in the imperative mood:

```
feat: add typing indicator timeout on the frontend
fix: prevent duplicate signals on WebSocket reconnect
chore: upgrade sentence-transformers to 3.1
```

---

## Backend Guidelines

### Code style

- Use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting (`ruff check .` / `ruff format .`)
- All public functions and classes should have docstrings
- Use type annotations throughout (FastAPI depends on them)

### Adding a new router

1. Create `routers/MyFeature.py` with `router = APIRouter()`
2. Register it in `main.py`: `app.include_router(MyFeature.router, prefix="/api/myfeature", tags=["myfeature"])`
3. Add Pydantic request/response models to `models.py`
4. Write at least a basic happy-path integration test in `tests/`

### Database

- Schema changes must be applied to `database.py` (`init_db`) so that `docker compose up --build` always produces a working database
- Prefer parameterised `asyncpg` queries (`$1`, `$2`, …) over string formatting
- Always release connections in `finally` blocks:

```python
conn = await get_db()
try:
    # ...
finally:
    await release_db(conn)
```

### NLP service

The NLP service (`services/Nlp.py`) has two backends — semantic (sentence-transformers) and keyword fallback. If you change the classification logic:

- Update the topic exemplars and/or keyword lists consistently in both backends
- Run `pytest tests/test_nlp.py -v` and make sure all existing tests still pass
- Add a test for the new behaviour

---

## Frontend Guidelines

### Code style

- ESLint is configured in `frontend/eslint.config.js`. Run `npm run lint` before committing.
- Components live in `src/components/` (reusable) or `src/views/` (page-level)
- All backend calls must go through `src/api.js` — never `fetch` directly from a component
- WebSocket logic lives exclusively in `src/hooks/Usewebsocket.js`

### Styling

All styling is inline CSS-in-JS (no CSS framework, no external stylesheet). Follow the colour tokens already in use:

| Token | Hex | Use |
|---|---|---|
| Primary | `#7C3AED` | Buttons, accents |
| Slate 900 | `#1E293B` | Body text |
| Slate 400 | `#94A3B8` | Muted / secondary text |
| Border | `#E2E8F0` | Dividers, card borders |
| Background | `#F8FAFC` | Page / card backgrounds |

Topic colours are defined in `src/constants.js` and must be extended there when adding new topics.

### Adding a new view

1. Create `src/views/MyView.jsx`
2. Add state management in `App.jsx` following the existing pattern (`view`, `setView`)
3. Pass only the minimum required props; avoid prop-drilling more than two levels

---

## Testing

### Backend

```bash
# All tests
pytest tests/ -v --asyncio-mode=auto

# Individual suites
pytest tests/test_nlp.py -v
pytest tests/Test_Background.py -v --asyncio-mode=auto
pytest tests/Test_Api.py -v
```

Every PR that touches backend logic must include or update tests. Aim for:

- At least one happy-path test per new endpoint
- At least one error/edge-case test per non-trivial function
- Existing test coverage must not decrease

### Frontend

```bash
cd frontend
npm run lint
```

A test suite for React components is planned. Until it exists, manual smoke-testing in the browser is required before opening a PR that modifies views or hooks.

---

## Opening a Pull Request

1. Push your branch and open a PR against `main`
2. Fill in the PR description template:
   - **What changed** — a plain-English summary
   - **Why** — motivation or issue reference
   - **How to test** — steps to verify the change manually or via automated tests
3. Link any related issues with `Closes #123` or `Refs #123`
4. Ensure CI is green before requesting review

---

## Code Review

Pull requests are reviewed automatically by [CodeRabbit](https://coderabbit.ai) (configured in `.coderabbit.yaml`) and manually by a maintainer.

CodeRabbit will post a summary and inline suggestions. You do not need to resolve every automated comment, but you should address or explicitly dismiss each one.

Maintainer review focuses on:

- Correctness and test coverage
- Consistency with existing patterns
- Performance implications (especially WebSocket broadcast and NLP calls)
- Security (no credentials in code, no unvalidated user input reaching the database)

---

## Reporting Issues

Open a GitHub issue with:

- A clear title describing the problem
- Steps to reproduce
- Expected vs. actual behaviour
- Relevant logs or screenshots
- Your environment (OS, browser, Docker version, or Python version)

For security vulnerabilities, please do not open a public issue. Email the maintainers directly.
