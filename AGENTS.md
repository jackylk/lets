# Repository Guidelines

## Project Structure & Module Organization

`app/` contains the Python backend: FastAPI routes, database setup, gateway/CLI code, MCP server code, and artifact adapters. `frontend/src/` contains the React/Vite UI, grouped by feature areas such as `topic/`, `workspace/`, `messages/`, `settings/`, `api/`, and `fixtures/`. Backend tests live in `tests/` as `test_*.py`. Frontend unit tests sit next to source files as `*.test.tsx`. `docs/` holds planning and architecture notes, while `scripts/` and `bin/` contain local utilities.

## Build, Test, and Development Commands

Backend setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

Frontend setup and checks:

```bash
cd frontend
npm run dev          # start Vite locally
npm run build        # type-check and build
npm run test         # run Vitest
npm run lint         # ESLint for src/
```

Backend tests use Postgres, not SQLite. Ensure `lets_test` exists, then run:

```bash
pytest
pytest tests/test_topics_workspace_membership.py
```

## Coding Style & Naming Conventions

Python uses 4-space indentation, type hints where practical, and small helper functions for shared auth/database behavior. Keep route handlers direct and avoid broad refactors in feature patches. TypeScript uses React function components, `PascalCase` component names, `camelCase` values, and colocated feature modules. Use existing query hooks in `frontend/src/api/queries.ts` instead of duplicating request code. Run `npm run lint` for frontend style.

## Testing Guidelines

Add backend coverage for API permission, schema, and migration behavior in `tests/`. Add frontend behavior tests with Vitest and Testing Library beside the component under test. Prefer focused test commands during development, then run the relevant backend and frontend slices before committing.

## Commit & Pull Request Guidelines

Recent commits use short imperative subjects, for example `Add topic visibility and member controls` or `Remove duplicate agents sidebar entry`. Keep commits scoped to one logical change. PRs should include a concise summary, test evidence, screenshots for UI changes, and any migration/config notes. Do not mix unrelated worktree changes into a commit.

## Security & Configuration Tips

Do not commit real tokens or local secrets. Local agent tokens are issued with `.venv/bin/python -m app.tokens_cli issue ...` and should stay out of source control. Use environment variables such as `DATABASE_URL`, `LETS_TEST_DATABASE_URL`, and `LETS_GIT_REPO` for local configuration.
