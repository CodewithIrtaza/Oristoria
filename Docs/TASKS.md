# Implementation Tasks: LangGraph Chat

This document defines the roadmap as **vertical slices**. Each task delivers a runnable, testable slice of functionality from UI to backend/database, rather than an isolated technical layer.

> **Walking Skeleton Milestone:** Completed by **T03** (User can create conversations, stream responses token-by-token, switch chats, restart the backend, and see full conversation history restored from Postgres).

---

## Task Summary Table

| ID | Title | Vertical Deliverable | Depends On | Manual Check |
|---|---|---|---|---|
| **T01** | Connected Health & Liveness Baseline | Live status badge on frontend reading backend `/api/health` | None | No |
| **T02** | Single-Turn Streaming Chat | User sends a message and sees streamed tokens in real-time | T01 | Yes (visual streaming feel) |
| **T03** | Multi-Conversation & Restart Persistence | Sidebar with conversation list + state survives backend restart | T02 | Yes (container restart) |
| **T04** | Stop Streaming Mid-Response & State Recovery | "Stop" button immediately halts stream and preserves valid partial state | T03 | Yes (abort timing) |
| **T05** | Streaming Markdown & Syntax-Highlighted Code | Formatted text, headings, code blocks via Streamdown | T02 | Yes (visual rendering) |
| **T06** | PDF Upload, Validation & Vector Ingestion | User uploads PDF; status chip shows pages and chunking status | T03 | No |
| **T07** | RAG Tool Use & Per-Conversation Isolation | Agent calls `search_documents`; UI displays tool chip; scoped to conversation | T06 | Yes (RAG answer quality) |
| **T08** | Rate Limiting, Concurrency Semaphore & Provider Fallback | Rate limit notifications, max 3 concurrent runs, provider failover | T03 | No |
| **T09** | Conversation Management (Rename, Delete & Cascade Cleanup) | Rename titles inline, delete chat and cascade delete chunks/checkpoints | T03 | No |
| **T10** | Cross-Conversation Memory (LangGraph Store) | User preferences/facts persist across conversations under same anon ID | T03 | No |
| **T11** | Containerized Deployment & Production Smoke Verification | Live Render + Vercel deployment passing the 2-minute PRD demo checklist | T04, T07, T09 | Yes (live URL smoke test) |

---

## Detailed Vertical Slices

### T01: Connected Health & Liveness Baseline
- **Goal:** Establish and verify the frontend-to-backend communication link with CORS and liveness checks.
- **Files likely touched:**
  - `backend/app/main.py`
  - `backend/app/api/health.py`
  - `frontend/src/App.tsx`
  - `frontend/src/api/client.ts`
- **Acceptance Criteria:**
  - [ ] `GET /api/health` returns `200 {"status": "ok"}` without querying the database.
  - [ ] Frontend displays a green "● ok" indicator on load when connected to the backend.
  - [ ] Frontend gracefully shows "● offline" if the backend is stopped.
  - [ ] CORS is configured to allow `VITE_API_BASE_URL` and `ALLOWED_ORIGINS`.
- **Test to write first:**
  - Unit test in `backend/tests/unit/test_health.py::test_health_returns_ok`: `client.get("/api/health").status_code == 200`
- **Depends on:** None
- **Manual verification required:** No (fully automated via unit tests and curl).

---

### T02: Single-Turn Streaming Chat
- **Goal:** Enable a user to enter a message and watch the LLM reply stream in token-by-token over Server-Sent Events (SSE).
- **Files likely touched:**
  - `backend/app/api/messages.py`
  - `backend/app/graph/state.py`
  - `backend/app/graph/build.py`
  - `backend/app/graph/streaming.py`
  - `backend/app/llm/providers.py`
  - `frontend/src/App.tsx`
  - `frontend/src/api/sse.ts`
  - `frontend/src/hooks/useChatStream.ts`
  - `frontend/src/components/Composer.tsx`
  - `frontend/src/components/Message.tsx`
- **Acceptance Criteria:**
  - [ ] `POST /api/conversations/{id}/messages` accepts `{"content": "..."}` and returns a `text/event-stream`.
  - [ ] Emits typed SSE events: `message_start`, `token`, and `message_end` with JSON payloads.
  - [ ] Frontend `Composer` input submits user message and disables while streaming.
  - [ ] Tokens render incrementally in the chat view as they arrive.
  - [ ] Supports `LLM_PROVIDER=fake` for deterministic testing without external API keys.
- **Test to write first:**
  - Unit test in `backend/tests/unit/test_streaming.py::test_stream_mapper_emits_expected_sse_sequence` asserting `message_start`, delta `token`s, and `message_end` are emitted in order.
- **Depends on:** T01
- **Manual verification required:** Yes — verify in browser that tokens appear incrementally (smooth typing effect) and not in a single buffered burst.

---

### T03: Multi-Conversation & Restart Persistence (Walking Skeleton Milestone)
- **Goal:** Enable creating and switching conversations in a sidebar, with all message history persisted to Neon Postgres so state survives backend restarts.
- **Files likely touched:**
  - `backend/app/db/pool.py`
  - `backend/app/db/migrate.py`
  - `backend/app/db/repositories.py`
  - `backend/app/api/conversations.py`
  - `backend/app/graph/build.py` (integrate `AsyncPostgresSaver`)
  - `frontend/src/components/Sidebar.tsx`
  - `frontend/src/hooks/useConversations.ts`
  - `frontend/src/hooks/useAnonId.ts`
- **Acceptance Criteria:**
  - [ ] Browser assigns a persistent anonymous UUID (`X-Anon-Id`) stored in `localStorage`.
  - [ ] "New chat" button creates a conversation row in Postgres and adds it to the sidebar.
  - [ ] Switching between conversations fetches thread state from `AsyncPostgresSaver` and displays previous messages.
  - [ ] Restarting the backend service does not wipe out conversations or message history.
  - [ ] Requests with a different `X-Anon-Id` cannot view or access another user's conversations (returns 404).
- **Test to write first:**
  - Integration test in `backend/tests/integration/test_persistence.py::test_conversation_survives_app_restart`: create conversation, send message, tear down app instance, recreate app instance, verify `GET /api/conversations/{id}` returns the complete message history.
- **Depends on:** T02
- **Manual verification required:** Yes — create 2 conversations in browser, send messages in each, restart the backend server (`docker compose restart backend` or kill/restart process), refresh page, and verify both histories remain intact.

---

### T04: Stop Streaming Mid-Response & State Recovery
- **Goal:** Allow the user to cancel generation mid-stream via a "Stop" button, preserving the partial message and leaving the LangGraph thread in a clean state for subsequent messages.
- **Files likely touched:**
  - `backend/app/api/messages.py`
  - `backend/app/graph/build.py`
  - `frontend/src/components/Composer.tsx`
  - `frontend/src/hooks/useChatStream.ts`
  - `frontend/src/api/sse.ts`
- **Acceptance Criteria:**
  - [ ] Clicking "Stop" triggers an `AbortController.abort()` on the frontend fetch request.
  - [ ] Backend detects client disconnect in the SSE generator `finally` block within 1 second.
  - [ ] Partial tokens streamed up to cancellation are saved to thread state as an `AIMessage` with `additional_kwargs={"stopped": true}`.
  - [ ] Any pending or unfulfilled tool calls are cleaned up so the thread state is not corrupted.
  - [ ] User can immediately send a follow-up message on the same thread without errors.
- **Test to write first:**
  - Integration test in `backend/tests/integration/test_stop_stream.py::test_client_abort_persists_partial_message_and_allows_next_turn`: initiate stream, close client connection after 2 tokens, assert checkpointer holds stopped message, send follow-up message and assert 200 response.
- **Depends on:** T03
- **Manual verification required:** Yes — click Stop while a long response is generating; confirm text generation ceases immediately and a new prompt can be answered right away.

---

### T05: Streaming Markdown & Syntax-Highlighted Code
- **Goal:** Render streaming assistant responses as formatted GitHub-Flavored Markdown with Shiki syntax-highlighted code blocks without breaking on incomplete tokens.
- **Files likely touched:**
  - `frontend/src/components/ChatView.tsx`
  - `frontend/src/components/Message.tsx`
  - `frontend/src/styles/tokens.css`
  - `frontend/src/styles/index.css`
  - `frontend/package.json`
- **Acceptance Criteria:**
  - [ ] Render bold, italics, links, blockquotes, ordered/unordered lists, and headings properly.
  - [ ] Fenced code blocks (` ```python `) render with proper syntax highlighting, language label, and copy-to-clipboard button.
  - [ ] Mid-stream unterminated code blocks or asterisks do not throw React errors or glitch.
  - [ ] CSS token variables in `tokens.css` control theme colors, borders, and dark backgrounds.
- **Test to write first:**
  - Frontend test in `frontend/src/__tests__/MarkdownRender.test.tsx::renders_code_block_with_highlighting`: render message containing ` ```python\nprint("hello")\n``` ` and assert code block elements and language tags are present.
- **Depends on:** T02
- **Manual verification required:** Yes — prompt the model to output a Python snippet and verify code formatting, dark theme contrast, and copy button functionality.

---

### T06: PDF Upload, Validation & Vector Ingestion
- **Goal:** Provide a file picker in the chat view to upload PDFs, validate limits (5 MB, 40 pages, 3 per thread), chunk text, generate Mistral embeddings, and store them in pgvector.
- **Files likely touched:**
  - `backend/app/api/documents.py`
  - `backend/app/rag/ingest.py`
  - `backend/app/db/repositories.py`
  - `frontend/src/components/UploadButton.tsx`
  - `frontend/src/components/Sidebar.tsx`
  - `frontend/src/api/client.ts`
- **Acceptance Criteria:**
  - [ ] Upload button permits selecting `.pdf` files and sends `multipart/form-data` to `POST /api/conversations/{id}/documents`.
  - [ ] Rejects files > 5 MB (`413`), non-PDF magic bytes (`415`), > 40 pages (`422`), or scanned PDFs with 0 extractable text (`422`).
  - [ ] Enforces maximum 3 PDFs per conversation.
  - [ ] Chunks text using recursive splitter, generates embeddings, and inserts into `doc_chunks` with `thread_id`, `document_id`, and `page`.
  - [ ] Frontend displays attached document pill with filename, page count, and status.
- **Test to write first:**
  - Unit test in `backend/tests/unit/test_ingest.py::test_pdf_validation_rejects_non_pdf_and_oversize`: assert `validate_pdf_bytes` throws `ValueError` on bad header or oversized byte array.
- **Depends on:** T03
- **Manual verification required:** No (covered by automated upload tests using fixture PDFs).

---

### T07: RAG Tool Use & Per-Conversation Isolation
- **Goal:** Connect the LangGraph agent to the `search_documents` retrieval tool so questions about uploaded PDFs are answered accurately, while guaranteeing strict data isolation between conversations.
- **Files likely touched:**
  - `backend/app/graph/tools.py`
  - `backend/app/graph/nodes.py`
  - `backend/app/rag/retriever.py`
  - `frontend/src/components/ToolChip.tsx`
  - `frontend/src/components/Message.tsx`
- **Acceptance Criteria:**
  - [ ] Graph includes `search_documents(query)` tool bound to the model.
  - [ ] System prompt dynamically lists names of documents attached to the thread.
  - [ ] When tool is called, backend streams `tool_start` and `tool_end` SSE events.
  - [ ] Frontend renders a subtle "searched your PDF" chip when retrieval executes.
  - [ ] **Strict Isolation:** A document uploaded in Conversation A is never retrieved or cited when asking questions in Conversation B.
- **Test to write first:**
  - Integration test in `backend/tests/integration/test_rag_isolation.py::test_rag_never_leaks_chunks_across_conversations`: upload doc with secret key to Conv A, query Conv B for the secret key, assert retrieval returns empty and agent does not know the secret.
- **Depends on:** T06
- **Manual verification required:** Yes — upload a custom PDF (e.g. resume or notes) and ask a specific factual question; confirm the answer directly quotes the document and displays the search chip.

---

### T08: Rate Limiting, Concurrency Semaphore & Provider Fallback
- **Goal:** Protect shared provider rate limits and free tier resources using in-memory sliding window rate limits, concurrency semaphore, and multi-model fallback.
- **Files likely touched:**
  - `backend/app/core/rate_limit.py`
  - `backend/app/core/run_registry.py`
  - `backend/app/llm/providers.py`
  - `frontend/src/components/Composer.tsx`
- **Acceptance Criteria:**
  - [ ] Limits requests to 20/hour and 100/day per anonymous ID; returns `429` with `Retry-After` header when exceeded.
  - [ ] Maximum 3 concurrent generation runs globally across all users via `asyncio.Semaphore(3)`; subsequent requests return `503 Busy`.
  - [ ] Second concurrent request on the exact same conversation thread returns `409 Conflict`.
  - [ ] Model fallback: if Groq returns 429 or 5xx, fails over to Mistral/OpenRouter before streaming first token.
  - [ ] Frontend displays human-readable alert banner when rate-limited or busy.
- **Test to write first:**
  - Unit test in `backend/tests/unit/test_rate_limit.py::test_rate_limiter_blocks_and_calculates_retry_after`: simulate 20 rapid requests, verify 21st returns `(False, retry_after > 0)`.
- **Depends on:** T03
- **Manual verification required:** No (automated via rapid-fire test script).

---

### T09: Conversation Management (Rename, Delete & Cascade Cleanup)
- **Goal:** Enable users to rename conversation titles inline and delete conversations, ensuring all associated database records, LangGraph checkpoints, and vector chunks are deleted in Neon.
- **Files likely touched:**
  - `backend/app/api/conversations.py`
  - `backend/app/db/repositories.py`
  - `frontend/src/components/Sidebar.tsx`
  - `frontend/src/api/client.ts`
- **Acceptance Criteria:**
  - [ ] `PATCH /api/conversations/{id}` accepts `{"title": "..."}` (1-80 chars) and updates the sidebar title.
  - [ ] `DELETE /api/conversations/{id}` returns `204` and deletes the conversation row.
  - [ ] Deletion cascades: removes document metadata, vector chunks (`doc_chunks`), and LangGraph checkpoint records for that `thread_id`.
  - [ ] Neon storage remains bounded (no orphaned checkpoints or vector embeddings).
  - [ ] Frontend sidebar removes the deleted item and redirects user to a new or next chat.
- **Test to write first:**
  - Integration test in `backend/tests/integration/test_cascade_delete.py::test_delete_conversation_purges_chunks_and_checkpoints`: verify zero rows remain in `conversations`, `documents`, `doc_chunks`, and checkpoints table after deletion.
- **Depends on:** T03
- **Manual verification required:** No (verified via integration assertions).

---

### T10: Cross-Conversation Memory (LangGraph Store)
- **Goal:** Implement long-term user memory across threads using LangGraph `AsyncPostgresStore`, allowing the assistant to remember facts about the user under their anonymous ID.
- **Files likely touched:**
  - `backend/app/api/memory.py`
  - `backend/app/graph/build.py`
  - `backend/app/graph/nodes.py`
  - `frontend/src/components/Sidebar.tsx`
- **Acceptance Criteria:**
  - [ ] StateGraph compiles with `store=AsyncPostgresStore` and namespaces keyed by `("memories", anon_id)`.
  - [ ] When user states stable profile information (e.g. "I am a frontend engineer using Vue"), memory is saved to store.
  - [ ] In a completely new conversation under the same browser, the assistant recalls this context.
  - [ ] `GET /api/memory` lists memories stored for the anonymous ID.
  - [ ] `DELETE /api/memory` allows the user to wipe all stored profile memories.
- **Test to write first:**
  - Integration test in `backend/tests/integration/test_memory_store.py::test_fact_saved_in_thread_1_recalled_in_thread_2`: prompt thread 1 with personal fact, start new thread 2, assert response acknowledges the fact.
- **Depends on:** T03
- **Manual verification required:** No (automated via multi-thread test).

---

### T11: Containerized Deployment & Production Smoke Verification
- **Goal:** Package frontend and backend with production Dockerfiles, configure Render and Vercel hosting, and execute a live smoke test verifying the 2-minute portfolio demo checklist.
- **Files likely touched:**
  - `docker-compose.yml`
  - `backend/Dockerfile`
  - `frontend/Dockerfile`
  - `README.md`
  - `scripts/smoke_test.py`
- **Acceptance Criteria:**
  - [ ] `docker compose up` brings up Postgres (pgvector), backend, and frontend locally with single command.
  - [ ] Render web service deploys backend container; `/api/health` returns 200 without waking Neon Postgres.
  - [ ] Vercel hosts frontend static build with `VITE_API_BASE_URL` pointing to Render.
  - [ ] Cold start loading state informs visitor ("Waking the server...") on initial request.
  - [ ] Passes all 6 checks in the PRD Demo Checklist on the public URL.
- **Test to write first:**
  - Automated smoke script `backend/tests/smoke_test.py::test_live_endpoint_pipeline` running basic ping and chat against target URL.
- **Depends on:** T04, T07, T09
- **Manual verification required:** Yes — perform the complete 2-minute walkthrough on the live Vercel/Render URL (chat, stream, stop, upload PDF, query PDF, restart backend, confirm persistence).
