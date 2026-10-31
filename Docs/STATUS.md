# Status

## Done

- **T01 — Connected Health & Liveness Baseline** (2026-10-31). Verified live: `GET /api/health` → `200 {"status":"ok"}` (DB-free, guarded by test), `GET /api/ready` → 200 stub, CORS allows `http://localhost:5173` and rejects foreign origins, frontend badge `● ok` / `● offline` covered by `App.test.tsx`. Also fixed two pre-existing test-infra bugs: vitest setup imported uninstalled `@testing-library/jest-dom` (removed import; suite was 100% red before), and vitest had no `include` so it collected Playwright `e2e/` specs.

## In progress

- (none)

## Decisions

- `/ready` stays a stub until the psycopg pool lands (T03); T01 acceptance only covers `/api/health`.
- Did NOT install `@testing-library/jest-dom` or `eslint` — dependency rule requires asking first. Tests use plain vitest matchers; both flagged to Irtaza.
- Vitest `include` scoped to `src/**` so Playwright specs are never executed by vitest.
- First two commits split as `docs:` (AGENTS.md + Docs) then `feat:` (scaffold) because the repo had zero commits before T01.

## Known bugs

- `npm run lint` fails: the script exists but `eslint` is not in devDependencies (blocked on approval to add eslint + config).
- `backend/pyproject.toml` pytest warns `asyncio_default_fixture_loop_scope` unset (cosmetic).
- `.gitignore` excludes `uv.lock`, which contradicts TECH_DESIGN's lockfile-discipline rationale — flagged, not changed.

## Next step

- **T02 — Single-Turn Streaming Chat** (`Docs/TASKS.md`). Test-first: `backend/tests/unit/test_streaming.py::test_stream_mapper_emits_expected_sse_sequence`.

## How to resume

- Read `Docs/TASKS.md` T02. Backend: `cd backend && uv sync --extra dev && uv run uvicorn app.main:app --reload --port 8000`. Frontend: `cd frontend && npm install && npm run dev`. Tests: `uv run pytest -v` (backend), `npm test` (frontend). No `.env` needed — `LLM_PROVIDER=fake` is the default.
