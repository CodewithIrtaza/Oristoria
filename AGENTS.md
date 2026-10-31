# AGENTS.md

Context: [PRD](Docs/PRD.md) · [Tech design](Docs/TECH_DESIGN.md) · [Tasks](Docs/TASKS.md) · [Run instructions](README.md)

## Before and after every task

- **Before:** read [Docs/STATUS.md](Docs/STATUS.md) and the current task in [Docs/TASKS.md](Docs/TASKS.md).
- **After:** run the full test suites and lint, update `Docs/STATUS.md`, tick the task in `Docs/TASKS.md`, commit.

## Commands

| Action | Command |
|---|---|
| Install backend | `cd backend && uv sync --extra dev` |
| Install frontend | `cd frontend && npm install` |
| Dev backend | `cd backend && uv run uvicorn app.main:app --reload --port 8000` |
| Dev frontend | `cd frontend && npm run dev` |
| Test backend | `cd backend && uv run pytest -v` (integration needs Postgres + pgvector) |
| Test frontend | `cd frontend && npm test` |
| Lint frontend | `cd frontend && npm run lint` |
| Build / full stack | `docker compose up` (builds all three services) |

Backend lint/format is not configured. Do not add a linter or formatter without asking.

## Non-obvious decisions (differs from defaults)

- Stream with `astream(..., version="v2")`; `stream_events(version="v3")` is experimental — see [TECH_DESIGN §1](Docs/TECH_DESIGN.md).
- Message history lives ONLY in the LangGraph checkpointer. Never copy messages into app tables; `conversations`/`documents` hold metadata only.
- Stop = client abort via `AbortController`. There is no stop endpoint. Partial text is saved as an `AIMessage` with `additional_kwargs["stopped"]=True`; dangling tool calls are removed.
- Manually opened Postgres connections must use `autocommit=True` and `dict_row` (`AsyncPostgresSaver` requirement).
- LangGraph creates its own checkpoint/store tables via `setup()`. Never hand-edit them; migrations in `backend/migrations/` cover app tables only.
- Every `/api` route requires `X-Anon-Id` except `/health` and `/ready`. Return 404 (never 403) for foreign or missing conversations.
- Tests and CI use `LLM_PROVIDER=fake`. No real provider keys in tests, CI, or `VITE_*` vars; secrets live only in `.env` (git-ignored) and host dashboards.
- pytest runs with `asyncio_mode = "auto"` — async tests need no decorator.

## Git

- Small commits, one logical change each, conventional messages: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`.
- Never commit secrets, `.env`, or API keys. Inspect `git diff` for accidental values before every commit. Pushes to `main` auto-deploy Render + Vercel.

## Dependencies

- Never add a package without asking me first: tell me its name, why it is needed, and confirm it exists on the official registry (PyPI for backend, npm for frontend). Prefer existing deps — [TECH_DESIGN](Docs/TECH_DESIGN.md) already rejects sse-starlette, Alembic, react-markdown, and Redux.

## Testing rules

- Failing test first: each task in TASKS.md names the test — write it, watch it fail, then implement.
- Run the FULL suite (backend unit + integration + frontend) before saying a task is done.

## Never

- Never hardcode, print, or log API keys, `.env` values, or `DATABASE_URL`.
- Never ship an in-memory checkpointer or store in a production path.
- Never enable raw HTML in model-output markdown beyond Streamdown defaults.
- Never scope PDF chunks without the `thread_id` filter (cross-conversation leaks are an acceptance failure).
