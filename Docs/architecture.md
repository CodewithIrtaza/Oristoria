# Architecture

```
 Browser (Vercel static SPA)
 +--------------------------------------------------------------+
 | React UI: Sidebar | ChatView (Streamdown) | Upload | Stop    |
 | localStorage: anon_id        fetch + AbortController         |
 +-------------------------------+------------------------------+
                                 | HTTPS, CORS (exact origin)
                                 | X-Anon-Id header
                                 v
 Render free web service (Docker, single instance)
 +--------------------------------------------------------------+
 | FastAPI                                                      |
 |  routers: conversations | messages (SSE) | documents | health|
 |  middleware: request id, CORS, rate limit, anon_id check     |
 |  services: ConversationService, IngestService, RunRegistry   |
 |             (one active run per thread, global semaphore)    |
 |                      |                                       |
 |  LangGraph compiled graph  <--- AsyncPostgresSaver           |
 |   nodes: agent <-> tools(search_documents)  [+ Store]       |
 |        |                         |                           |
 +--------|-------------------------|---------------------------+
          | HTTPS                   | psycopg pool
          v                         v
 Groq (default)            Neon Postgres (+ pgvector)
 Mistral (fallback, embed)  conversations, documents,
 OpenRouter (fallback)      LangGraph checkpoint tables,
                            doc_chunks (vectors), store
```

See [TECH_DESIGN.md](TECH_DESIGN.md) for the full spec.
