# Oristoria — LangGraph Chat

A streaming AI chat app with PDF context, built with FastAPI, LangGraph, React + Vite, and Neon Postgres.

## Architecture

```
Browser (Vercel SPA) → FastAPI + LangGraph (Render) → Groq / Mistral / OpenRouter
                                ↕
                       Neon Postgres + pgvector
```

See [`docs/TECH_DESIGN.md`](docs/TECH_DESIGN.md) for the full architecture.

## Quick start — one command (Docker)

```bash
# 1. Copy and fill in secrets
cp .env.example .env
#    Edit .env:  set DATABASE_URL, GROQ_API_KEY, etc.
#    For local demo without API keys, leave LLM_PROVIDER=fake

# 2. Start everything
docker compose up
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API docs (Swagger): http://localhost:8000/docs

## Quick start — without Docker

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: http://localhost:8000/api/health

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

## Run tests

```bash
# Backend unit tests (no DB, no network required)
cd backend
uv run pytest tests/unit -v

# Backend integration tests (requires Postgres with pgvector)
uv run pytest tests/integration -v

# Frontend (coming in later tasks)
cd frontend
npm test
```

## Environment variables

See [`.env.example`](.env.example) for all variable names.  
Real values go in `.env` (git-ignored) or in your hosting dashboard (Render / Vercel).

## Demo checklist (manual smoke test before each release)

- [ ] New chat created, streamed reply appears token by token
- [ ] Stop button aborts mid-stream; partial message is saved
- [ ] Markdown and code blocks render correctly
- [ ] Upload a PDF, ask a question about it → answer cites the document
- [ ] Restart the backend container → history is still present
- [ ] Second conversation does not see the first conversation's PDF

## Deployment

| Service | Purpose | Branch trigger |
|---------|---------|---------------|
| Render (Docker) | Backend | push to `main` |
| Vercel (Vite) | Frontend | push to `main` |
| Neon | Postgres + pgvector | — |

Health check endpoint: `GET /api/health`  
Frontend reads backend URL from `VITE_API_BASE_URL` (set in Vercel env).

## Tech stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.12, FastAPI 0.115+, LangGraph 1.2.x |
| Orchestration | LangGraph `StateGraph`, `astream` v2 |
| Chat LLM | Groq (default), Mistral / OpenRouter (fallback) |
| Embeddings | Mistral `mistral-embed` (1024 dims) |
| Database | Neon Postgres + pgvector |
| Frontend | React 19, TypeScript, Vite 7, Tailwind v4 |
| Markdown | Streamdown |
| Containers | Docker multi-stage, docker compose |
