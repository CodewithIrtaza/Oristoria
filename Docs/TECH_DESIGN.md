# Tech Design: LangGraph Chat (working title)

Companion to `docs/PRD.md`. Written 2026-10-30. Covers stack, architecture, data, API, repo layout, services, tests, deployment, and risks.

## 0. Assumptions and doc check

### Assumptions (decided without asking, change any of them)

1. **Hosting.** Backend on **Render free (Docker)**, frontend on **Vercel Hobby**, database on **Neon free Postgres**. Railway is dropped (see section 1). This resolves PRD open questions 3 and 10.
2. **One database for everything.** Neon Postgres holds app tables, LangGraph checkpoints, optional long-term memory, and pgvector chunks.
3. **Single backend instance.** In-process locks, semaphores, and rate limits are acceptable. Scaling out is a non-goal.
4. **Runtimes.** Python 3.12, Node 22 LTS. Vite 7 needs Node 20.19+ or 22.12+.
5. **PDF limits (PRD open question 5).** 5 MB, 40 pages, 3 PDFs per conversation, text PDFs only (no OCR).
6. **Per-visitor limits (PRD open question 7).** 20 messages/hour and 100/day per anonymous ID, plus a global cap of 3 concurrent generations.
7. **Stop semantics (PRD open question 8).** The partial assistant message is saved to thread state and marked `stopped`.
8. **Embeddings (PRD open question 4).** Mistral `mistral-embed` (1024 dims) stored in pgvector.
9. **Default chat model** is chosen by a 20-prompt tool-calling eval in the first tasks, not by guess (PRD open question 6).
10. **Anonymous identity.** The browser generates a random UUID `anon_id` and sends it as `X-Anon-Id`. It scopes data. It is not authentication.

### Documentation check log

Checked against current official docs or vendor pages on 2026-10-30. Pin exact versions in the lockfile at scaffold time.

| Item | What I confirmed | Source type |
| --- | --- | --- |
| LangGraph | 1.2.x line (1.2.13 on PyPI). Production memory uses a database-backed checkpointer. `stream_events(version="v3")` is **beta/experimental**; `astream(..., version="v2")` is the stable typed format | LangChain docs, changelog, reference |
| `langgraph-checkpoint-postgres` | `AsyncPostgresSaver`; call `setup()` once; manually created connections **must** use `autocommit=True` and `row_factory=dict_row` | LangChain reference |
| LangGraph Store | `AsyncPostgresStore`, namespace tuples, `Runtime[Context]` for user id, `store.setup()` | LangChain docs |
| Message trimming | `trim_messages` with `count_tokens_approximately` | LangChain docs |
| FastAPI SSE | Native `fastapi.sse.EventSourceResponse` / `ServerSentEvent`, added in **0.135.0**, works with POST, 15 s keep-alive ping, `X-Accel-Buffering: no` | FastAPI docs |
| `langchain-groq` | `ChatGroq`, `bind_tools`, token-level streaming, native async | LangChain docs |
| Groq limits | Limits are **per organization**, exact values only on the console limits page. Third-party sample for free text models: about 30 RPM, 1,000 RPD, **8,000 TPM**, 200,000 TPD | Groq docs, third-party sample |
| `langchain-postgres` | `PGVectorStore` + `PGEngine` (async, metadata filter). `PGVector` is deprecated | PyPI, LangChain docs |
| Mistral embeddings | `mistral-embed`, 1024 dims, free Experiment tier with low limits shown in console | Third-party summaries |
| `pypdf` | Pure Python, `PdfReader(...).pages[i].extract_text()`; 6.x on PyPI | PyPI |
| Streamdown | Streaming-safe markdown for React with built-in GFM, Shiki code highlighting, hardening; install `streamdown` + `@streamdown/code`; needs Tailwind `@source` line | streamdown.ai docs |
| Render free | Spins down after 15 min idle (about 1 min wake), 750 free hours/month, **ephemeral filesystem**, free Postgres **expires after 30 days** | Render docs |
| Railway | Free plan is $1/month credit, trial is a one-time $5. An always-on service is not $0 | Railway docs |
| Neon free | 0.5 GB per project, 100 CU-hours/month, scale to zero after 5 min, pgvector included, no expiry | Neon docs |
| Vercel Hobby | Personal, non-commercial use only | Vercel docs |

**Not verified yet (check in Task 0 and pin):** `ToolNode`/`tools_condition` import paths, `AsyncPostgresSaver.adelete_thread`, `psycopg_pool` connection-health options, the fake chat model class name in `langchain-core`, Tailwind v4 and Vite exact versions, Playwright version.

## 1. Recommended stack

| Layer | Choice | Why (one line) | Rejected alternative |
| --- | --- | --- | --- |
| Language/tooling | Python 3.12 + `uv` lockfile | Fast reproducible installs for a Docker build | `pip` + `requirements.txt`: no lockfile discipline |
| API | FastAPI 0.135+ with native `fastapi.sse` | SSE over POST with keep-alive built in, no extra dependency | `sse-starlette`: now redundant; WebSockets: more moving parts for one-way streaming |
| Orchestration | LangGraph 1.2.x `StateGraph`, `astream(stream_mode=["messages","updates"], version="v2")` | Stable typed stream parts; explicit graph shows the skill | `stream_events(version="v3")`: marked experimental; prebuilt agent helpers: hide the graph |
| Chat models | `langchain-groq` `ChatGroq` default; Mistral and OpenRouter as fallback via `.with_fallbacks()` | Fast streaming, keys already available | LiteLLM proxy: an extra service to run |
| Persistence | Neon Postgres: `AsyncPostgresSaver` (+ `AsyncPostgresStore` for Should memory) via `psycopg` 3 pool | Survives restarts on a free tier with no expiry | SQLite file: Render free filesystem is ephemeral; Render free Postgres: expires after 30 days |
| Vector store | pgvector in the same Neon DB through `langchain-postgres` `PGVectorStore` | One database, metadata filter gives per-conversation isolation | Chroma/FAISS files: need a persistent disk; Qdrant Cloud: another account and service |
| Embeddings | Mistral `mistral-embed` through `langchain-mistralai` | Hosted, no local model memory cost | Local sentence-transformers: too heavy for 512 MB / 0.1 CPU |
| PDF | `pypdf` + a recursive text splitter | Pure Python, no system packages in Docker | PyMuPDF: AGPL licensing; OCR stacks: out of scope |
| Migrations | Plain numbered SQL files + a tiny runner; LangGraph `setup()` for its own tables | Three app tables do not justify a migration framework | Alembic: overkill here |
| Rate limiting | Small in-process sliding window keyed by `anon_id` + IP | Single instance, about 40 lines, easy to test | Postgres counters: extra DB round trip per request |
| Frontend | React 19 + TypeScript + Vite + Tailwind v4 | Standard, fast dev loop, Vercel auto-detects Vite | Next.js: SSR not needed, adds a server runtime |
| Markdown | Streamdown (`streamdown`, `@streamdown/code`) | Handles half-finished markdown while tokens stream | `react-markdown` + highlighter: breaks on unterminated blocks mid-stream |
| Client state | React state + a `useChatStream` hook, no state library | Small surface area for v1 | Redux Toolkit: boilerplate for little shared state |
| SSE client | `fetch` + `ReadableStream` with a small parser, `AbortController` for Stop | `EventSource` is GET-only; POST body needs fetch | Third-party SSE client: dependency for ~40 lines |
| Containers | Docker multi-stage, non-root; `docker compose` for local (Postgres with pgvector, backend, frontend) | One-command run is a success metric | Dev containers only: reviewers cannot run them |
| Hosting | Render free (backend), Vercel Hobby (frontend), Neon free (DB) | Only combination that stays at $0 without an expiring database | Railway: not $0 for an always-on service |

Frontend theming uses CSS variables as design tokens, so a distinctive theme and dark mode (PRD Could) is a token swap.

## 2. Architecture

### Components

```
 Browser (Vercel static SPA)
 +--------------------------------------------------------------+
 | React UI: Sidebar | ChatView (Streamdown) | Upload | Stop     |
 | localStorage: anon_id        fetch + AbortController          |
 +-------------------------------+------------------------------+
                                 | HTTPS, CORS (exact origin)
                                 | X-Anon-Id header
                                 v
 Render free web service (Docker, single instance)
 +--------------------------------------------------------------+
 | FastAPI                                                       |
 |  routers: conversations | messages (SSE) | documents | health  |
 |  middleware: request id, CORS, rate limit, anon_id check      |
 |  services: ConversationService, IngestService, RunRegistry    |
 |             (one active run per thread, global semaphore)     |
 |                      |                                        |
 |  LangGraph compiled graph  <--- AsyncPostgresSaver            |
 |   nodes: agent <-> tools(search_documents)  [+ Store, Should] |
 |        |                         |                            |
 +--------|-------------------------|----------------------------+
          | HTTPS                   | psycopg pool / SQLAlchemy engine
          v                         v
 Groq (default)            Neon Postgres (+ pgvector)
 Mistral (fallback, embed)  conversations, documents,
 OpenRouter (fallback)      LangGraph checkpoint tables,
                            doc_chunks (vectors), store (Should)
```

### Data flow: send a message

```
1  UI  POST /api/conversations/{id}/messages {content}   (fetch, AbortController)
2  API validate X-Anon-Id owns {id}; rate limit; acquire per-thread run lock + semaphore
3  API graph.astream({"messages":[user msg]}, config{thread_id}, stream_mode=[messages,updates], version=v2)
4  Graph agent node: trim history -> model.ainvoke with tools bound
5    if tool call -> tools node: search_documents(query) -> pgvector top-k filtered by thread_id -> back to agent
6  API map stream parts to SSE: message_start, token*, tool_start, tool_end, message_end
7  Graph writes checkpoint to Postgres after each step
8  API release lock; update conversations.updated_at
```

### Data flow: Stop

```
1  UI  AbortController.abort()  -> HTTP connection closes
2  API detects disconnect / task cancellation in the stream generator
3  API (in finally) reads the partial text it already streamed, then
      graph.aupdate_state(config, {"messages":[AIMessage(partial, additional_kwargs={"stopped": True})]})
   and drops any unanswered tool-call message so history stays valid
4  API release lock
```

### Data flow: upload a PDF

```
1  UI  POST /api/conversations/{id}/documents (multipart)
2  API check size, %PDF magic bytes, page count, per-conversation count
3  API pypdf extract text -> split -> embed in batches (Mistral) -> insert rows with thread_id, document_id, page
4  API insert documents row (status ready) -> 201 {id, filename, pages, chunks}
```

### Data flow: restart

```
Backend container restarts -> lifespan startup opens pool, runs SQL migrations, checkpointer.setup()
-> GET /api/conversations lists from the conversations table
-> GET /api/conversations/{id} rebuilds messages from graph.aget_state(thread_id)
```

### Graph shape

- State: `MessagesState` (add-messages reducer). Tools receive `thread_id` from the run config.
- `agent` node: trims history with `trim_messages` to a token budget, adds a system prompt that lists attached document names, calls the model with `search_documents` bound.
- Conditional edge: tool calls go to `tools`, otherwise end. `recursion_limit` is capped to bound tool loops.
- Should: compile with `store=AsyncPostgresStore` and `context_schema` carrying `anon_id` for namespace `("memories", anon_id)`.

## 3. Data model and state

### Ownership rule

- **Message history lives only in the LangGraph checkpointer.** The app never copies messages into its own table.
- **Conversation metadata lives in the app table** `conversations`, because the checkpointer has no clean "list my threads" feature.

### Tables

```sql
-- app tables (SQL migrations)
conversations (
  id          uuid primary key,          -- also the LangGraph thread_id
  anon_id     uuid not null,
  title       text not null default 'New chat',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index on conversations (anon_id, updated_at desc);

documents (
  id              uuid primary key,
  conversation_id uuid not null references conversations(id) on delete cascade,
  filename        text not null,
  size_bytes      integer not null,
  page_count      integer not null,
  chunk_count     integer not null,
  status          text not null check (status in ('ready','failed')),
  error           text,
  created_at      timestamptz not null default now()
);

-- vector table, created through langchain-postgres PGEngine/PGVectorStore
doc_chunks (
  id uuid, content text, embedding vector(1024),
  thread_id uuid,  document_id uuid,  page integer   -- real columns for filtering
);
```

LangGraph creates its own checkpoint tables via `setup()`. Do not edit them by hand. The Should-level long-term memory store also creates its own tables via `store.setup()`.

### Runtime state (in memory, single instance)

| State | Purpose |
| --- | --- |
| `RunRegistry` | Thread ids with an active run. A second send returns 409 |
| `Semaphore(3)` | Caps concurrent LLM generations to protect shared provider limits |
| Rate-limit windows | Per `anon_id` and per IP counters |

### Conventions

- Assistant messages interrupted by Stop carry `additional_kwargs["stopped"] = true`.
- Message ids are LangChain message ids, used as stable React keys.
- Tool messages are not returned to the UI as chat bubbles; tool activity is shown as a small "searched your PDF" chip.

### Retention and storage guard (Neon free is 0.5 GB)

Checkpoints store state snapshots per step, so storage grows faster than raw text size. This is measured in Task 0, not guessed.

- Assumed caps: 20 conversations per `anon_id`, 100 messages per conversation.
- A janitor task at startup and once a day deletes conversations idle over 30 days, with their checkpoints and chunks.
- Delete a conversation in one transaction: `doc_chunks` rows, then the `conversations` row (cascades `documents`), then the checkpoints for that thread.

## 4. API surface

Base path `/api`. All JSON. Every route except `/health` requires `X-Anon-Id: <uuid>`. Errors use `{"error": {"code": "...", "message": "...", "retry_after": null}}`.

| Method + path | Request | Response |
| --- | --- | --- |
| `GET /health` | none | `200 {"status":"ok"}` (liveness, does not touch the DB) |
| `GET /ready` | none | `200 {"status":"ready"}` after a DB ping, else `503` |
| `POST /conversations` | `{}` | `201 {"id","title","created_at","updated_at"}` |
| `GET /conversations` | none | `200 {"items":[{"id","title","updated_at"}]}` newest first |
| `GET /conversations/{id}` | none | `200 {"conversation":{...},"messages":[{"id","role":"user|assistant","content","stopped":false,"tools":[{"name","chunks"}]}],"documents":[{"id","filename","page_count"}]}` |
| `PATCH /conversations/{id}` (Should) | `{"title":"..."}` (1 to 80 chars) | `200 {conversation}` |
| `DELETE /conversations/{id}` (Should) | none | `204` |
| `POST /conversations/{id}/messages` | `{"content":"...","model":null}` (1 to 4000 chars; `model` only if the Could selector ships) | `200 text/event-stream` (below) |
| `POST /conversations/{id}/documents` | `multipart/form-data`, field `file` (PDF) | `201 {"id","filename","page_count","chunk_count","status":"ready"}` |
| `GET /conversations/{id}/documents` | none | `200 {"items":[...]}` |
| `DELETE /conversations/{id}/documents/{doc_id}` | none | `204` |
| `GET /memory` (Should) | none | `200 {"items":[{"id","text"}]}` |
| `DELETE /memory` (Should) | none | `204` clears all memories for this `anon_id` |

Status codes: `400` validation, `404` unknown or foreign conversation (never reveal which), `409` a run is already active on this thread, `413` file too large, `415` not a PDF, `422` unreadable or no extractable text, `429` rate limited (with `Retry-After`), `503` provider unavailable or server busy.

### SSE stream for `POST /conversations/{id}/messages`

Implemented with FastAPI's native `ServerSentEvent`. Each `data` is JSON.

| Event | Data |
| --- | --- |
| `message_start` | `{"message_id":"...","conversation_id":"..."}` |
| `token` | `{"delta":"..."}` |
| `tool_start` | `{"id":"...","name":"search_documents","args":{"query":"..."}}` |
| `tool_end` | `{"id":"...","name":"search_documents","chunks":4}` |
| `message_end` | `{"message_id":"...","finish_reason":"stop|length|stopped|error","usage":{"input_tokens":0,"output_tokens":0}}` |
| `error` | `{"code":"rate_limited|provider_unavailable|busy|internal","message":"...","retry_after":null}` |

The stream ends after `message_end` or `error`. FastAPI sends a keep-alive comment every 15 seconds when idle. **Stop** is the client aborting the request; there is no separate stop endpoint (see risk R1 for why this is verified early).

## 5. Folder structure

```
.
├── docker-compose.yml          # db (pgvector), backend, frontend
├── README.md                   # one-command run, architecture diagram, demo checklist
├── docs/
│   ├── PRD.md
│   ├── TECH_DESIGN.md
│   └── architecture.md         # diagram source for README
├── .github/workflows/ci.yml    # lint, unit, integration (Postgres service), frontend tests
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml          # + uv.lock
│   ├── migrations/             # 001_conversations.sql, 002_documents.sql, ...
│   ├── app/
│   │   ├── main.py             # app factory, lifespan (pool, migrations, checkpointer)
│   │   ├── config.py           # typed settings from env
│   │   ├── api/                # routers: conversations.py, messages.py, documents.py, memory.py, health.py
│   │   ├── core/               # anon_id dependency, rate_limit.py, run_registry.py, errors.py
│   │   ├── graph/              # state.py, nodes.py, tools.py, build.py, streaming.py (parts -> SSE events)
│   │   ├── llm/                # providers.py (Groq/Mistral/OpenRouter + fallbacks), prompts.py
│   │   ├── rag/                # ingest.py (pypdf, split, embed), retriever.py
│   │   └── db/                 # pool.py, migrate.py, repositories.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── fixtures/           # sample PDFs (text, 40-page, scanned)
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts
    ├── e2e/                    # Playwright specs
    └── src/
        ├── main.tsx, App.tsx
        ├── api/                # client.ts, sse.ts (fetch stream parser)
        ├── hooks/              # useChatStream.ts, useConversations.ts, useAnonId.ts
        ├── components/         # Sidebar, ChatView, Message, Composer, UploadButton, ToolChip
        └── styles/             # tokens.css (theme variables), index.css (Tailwind + Streamdown @source)
```

## 6. External services and secrets

Names only. Values live in Render and Vercel dashboards and a local `.env` that is git-ignored.

| Service | Used for | Secret name |
| --- | --- | --- |
| Groq | Default chat model | `GROQ_API_KEY` |
| Mistral | Embeddings and fallback chat model | `MISTRAL_API_KEY` |
| OpenRouter | Fallback chat model | `OPENROUTER_API_KEY` |
| Neon | Postgres + pgvector | `DATABASE_URL` |
| Render | Backend hosting (Git auto-deploy) | account only |
| Vercel | Frontend hosting (Git auto-deploy) | account only |
| GitHub | Repo + Actions CI | none needed; CI uses a fake chat model, so **no provider keys in CI** |

No secret is ever placed in a `VITE_` variable, since those ship to the browser.

## 7. Testing strategy

### Unit (fast, no network, no DB)

- Rate limiter: window rollover, per-`anon_id` vs per-IP.
- Run registry: second run on the same thread is rejected, lock released on error and on cancel.
- Stream mapper: LangGraph v2 stream parts to SSE events (tokens, tool start/end, end reasons), using recorded fixtures.
- Stop handler: partial text becomes a `stopped` assistant message; a dangling tool-call message is removed.
- PDF ingest helpers: size and page limits, magic-byte check, no-text PDF rejected, chunk metadata.
- Settings validation and error-to-HTTP mapping.
- Frontend: SSE parser (split chunks, multi-line data, keep-alive comments), `useChatStream` state machine, anon id creation.

### Integration (real Postgres with pgvector, fake LLM and fake embeddings)

- Full message flow through `httpx` against the FastAPI app: events arrive in order, history appears in `GET /conversations/{id}`.
- **Restart persistence:** build the app, send messages, tear it down, build it again on the same database, assert history is intact.
- Stop: abort mid-stream, assert partial message is stored and the next turn succeeds.
- Retrieval isolation: PDF uploaded in conversation A is never returned for conversation B.
- Ownership: wrong `X-Anon-Id` gets `404`; deleting a conversation removes checkpoints, chunks, and documents.
- Concurrency: two simultaneous sends on one thread give `409`.
- Provider fallback: primary fake model raises a rate-limit error, fallback answers.

### End to end (Playwright against `docker compose`, fake LLM)

Automates the PRD demo checklist: new chat, streamed reply, Stop mid-way, markdown and code block render, upload PDF and ask about it, restart the backend container, history still present, second conversation does not see the first PDF.

### Not automated

- Real Groq and Mistral calls: a manual **live smoke script** run before each release against the deployed URLs, plus the tool-calling eval from Task 1 (section 9).
- Visual polish and the first-token latency target: measured by hand on the deployed app and logged.

## 8. Deployment and environment variables

### Targets

- **Backend:** Render free web service built from `backend/Dockerfile`. Bind `0.0.0.0` on the port Render provides. Health check path `/api/health`.
- **Frontend:** Vercel project rooted at `frontend/`, Vite preset, static build. The browser calls the Render URL directly (CORS), not through a Vercel proxy.
- **Database:** Neon free project with the `vector` extension enabled.
- **Local:** `docker compose up` brings up Postgres (pgvector image), backend, and frontend; a `fake` provider mode lets reviewers run it without keys.
- **Cold starts:** Render sleeps after 15 minutes idle and takes about a minute to wake; the UI shows a "waking the server" state when the first request is slow. Optionally ping `/api/health` on a schedule: Render gives 750 free hours per month, enough for one always-on service. Verify Render's current terms first. The ping must not touch the DB, so Neon can still scale to zero.
- **Vercel Hobby is non-commercial.** A personal portfolio fits. Do not use this deployment for client work or paid use.

### Backend environment variables

| Variable | Purpose | Example/default |
| --- | --- | --- |
| `APP_ENV` | `development` or `production` | `production` |
| `DATABASE_URL` | Neon connection string (direct, or pooled with prepared statements off) | secret |
| `GROQ_API_KEY`, `MISTRAL_API_KEY`, `OPENROUTER_API_KEY` | Provider keys | secret |
| `LLM_PROVIDER` | `groq`, `mistral`, `openrouter`, or `fake` | `groq` |
| `LLM_PRIMARY_MODEL`, `LLM_FALLBACK_MODEL` | Model ids chosen by the Task 1 eval | set after eval |
| `EMBEDDING_MODEL` | Embedding model | `mistral-embed` |
| `ALLOWED_ORIGINS` | Comma-separated exact frontend origins | Vercel URL |
| `MAX_PDF_MB`, `MAX_PDF_PAGES`, `MAX_DOCS_PER_CONVERSATION` | Upload limits | `5`, `40`, `3` |
| `RATE_LIMIT_PER_HOUR`, `RATE_LIMIT_PER_DAY` | Per `anon_id` | `20`, `100` |
| `MAX_CONCURRENT_GENERATIONS` | Global semaphore | `3` |
| `MAX_OUTPUT_TOKENS`, `HISTORY_TOKEN_BUDGET`, `RETRIEVAL_TOP_K` | Keep requests under provider token limits | tuned in Task 1 |
| `MAX_CONVERSATIONS_PER_ANON`, `MAX_MESSAGES_PER_CONVERSATION`, `RETENTION_DAYS` | Storage guard | `20`, `100`, `30` |
| `LOG_LEVEL` | Logging | `INFO` |

### Frontend environment variables

| Variable | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | Backend base URL, public by design, set at build time in Vercel |

## 9. Top 5 technical risks and first-task de-risking

Suggested order: Task 0 (walking skeleton, deployed) then Task 1 (graph + stop + model eval) before any UI polish.

| # | Risk | Why it matters | De-risk in the first tasks |
| --- | --- | --- | --- |
| R1 | **Stop leaves broken thread state.** A cancelled node may write nothing, or leave a tool call without its result, which providers reject on the next turn | Stop is a Must and the next message after Stop must work | Task 1 spike: stream, abort at three points (before first token, mid-text, during a tool call), then send a follow-up. Implement the `aupdate_state` partial-save and dangling-tool-call cleanup, and keep these as permanent integration tests. Also confirm disconnect is detected through Render's proxy; if not, add an explicit `POST .../stop` |
| R2 | **The streaming path breaks in production.** CORS, proxy buffering, abort propagation, and a sleeping backend can all look like "no streaming" | The whole demo depends on streaming | Task 0: deploy a "hello stream" endpoint to Render and a bare Vite page to Vercel on day 1 or 2. Check incremental tokens, abort, keep-alive, and first request after sleep. Fix CORS and headers before building features |
| R3 | **Free-tier persistence is flaky.** Neon scales to zero after 5 minutes (stale pooled connections), pooled endpoints and prepared statements can clash, and checkpoint storage may outgrow 0.5 GB | History surviving restart is a Must | Task 0: run `AsyncPostgresSaver` from Render against Neon with `autocommit=True` and `dict_row`, prepared statements off if pooled, and pool health checks. Test: idle over 5 minutes then send, redeploy then reload history. Measure bytes per turn and set the storage-guard caps from real numbers |
| R4 | **Groq free limits and tool-calling quality.** Limits are per organization, so all visitors share about 8k tokens per minute (sample figure; check the console). A RAG turn can use several thousand tokens, and some models call tools unreliably | One reviewer can starve another; a flaky tool call breaks the RAG demo | Task 1: build a 20-prompt eval (tool needed, tool not needed, no documents) across 2 or 3 candidate models; record tool-call accuracy and tokens per turn. Pick the default from it. Enforce history trim, `RETRIEVAL_TOP_K`, output cap, the concurrency semaphore, and fallback on 429. Fallback only helps before the first token, so show a friendly error if a stream fails midway |
| R5 | **RAG ingestion and isolation.** Parsing and embedding on 0.1 CPU can time out, embedding limits can throttle uploads, scanned PDFs have no text, and a filter bug would leak one conversation's PDF into another | Per-conversation scoping is an acceptance criterion | Task 3 spike with three fixtures (small text PDF, 40-page PDF, scanned PDF): measure ingest time and embedding calls, tune the limits, return `422` for no-text PDFs. Write the isolation test (conversation A vs B) before the retriever. Batch embeddings with retry and backoff |

### Cross-cutting notes

- **Prompt injection through PDFs.** The only tool is read-only retrieval, so the worst case is a misleading answer. Wrap retrieved text in clear delimiters and tell the model to treat it as data.
- **Markdown safety.** Rely on Streamdown's built-in hardening; do not enable raw HTML from model output beyond its defaults.
- **Observability.** Structured logs with a request id, time to first token, token counts, provider used, and fallback events. These numbers feed the success metrics.
