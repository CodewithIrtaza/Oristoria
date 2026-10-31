# PRD: LangGraph Chat (working title)

A Claude-style chat web app with streaming responses, persistent multi-conversation history, and a RAG tool over user-uploaded PDFs. Built as a portfolio piece.

## Problem

Recruiters and clients reviewing a junior AI engineer's portfolio mostly see notebooks, screenshots, and repos they cannot quickly verify. They have no fast way to confirm the engineer can ship a production-grade GenAI app: streaming, persistent state, tool use, and a real deployment.

This project is a live, deployed chat app that proves those skills in about two minutes of use.

## Users

- **Primary: recruiters, hiring managers, and prospective clients.** They open a public link, spend a few minutes, and judge the work. Technical and semi-technical. No account, no setup.
- **Secondary: the builder.** Uses the app and repo as a walkthrough in interviews and client calls.
- **Secondary: developers reading the repo.** Want to run it locally with one Docker command and understand the architecture.

Visitors are anonymous. There is no login in v1.

## Goals

1. Demonstrate an end-to-end GenAI app: streaming, persistent state (LangGraph checkpointer), tool use (RAG), and containerized deployment.
2. Let a reviewer pass a 2-minute demo checklist on the live URL.
3. Feel fast: first token visible in about 2 seconds.
4. Ship a deployed v1 within 6 weeks at $0 infrastructure cost.
5. Leave a clean repo that is easy to read and run.

## Non-goals

Explicitly out of scope for v1:

- Login, accounts, and sharing conversations
- Message edit, regenerate, and branching
- Voice, image input, and non-PDF uploads
- Billing, usage tiers, and an admin dashboard

## Features

### Must

1. **Streaming chat with Stop.** Token-by-token streaming over SSE from a FastAPI endpoint, with a Stop button that cancels generation mid-response.
2. **Multiple conversations with persistent history.** A sidebar lists conversations. State lives in a LangGraph StateGraph with a persistent checkpointer keyed by `thread_id`, so history survives a backend restart (short-term, thread-level memory).
3. **Markdown and code rendering.** Assistant messages render markdown, with formatted code blocks.
4. **RAG as a tool.** The user uploads a PDF to a conversation. The agent calls a retrieval tool to answer from it. Documents are scoped to their conversation.
5. **Public deployment.** Dockerized. Backend on Railway or Render, frontend on Vercel, reachable by a public URL with no login.

### Should

- Rename and delete conversations.
- Long-term memory using the LangGraph Store, keyed by an anonymous browser ID, with a way to clear it.
- Basic rate limiting per browser/IP to protect free API keys.
- Provider fallback: Groq as default, OpenRouter or Mistral if Groq is rate limited or down.
- Short-term memory management for long chats (trim or summarize so the context window is not exceeded).

### Could

- Web search tool.
- Model/provider selector.
- Auto-generated conversation titles.
- Distinctive visual theme and dark mode.

## User stories

- As a reviewer, I can open the live URL and start chatting without signing in so that I can evaluate the app immediately.
  - Acceptance: no login screen; a new conversation is ready on first load.

- As a user, I can send a message and watch the reply stream in so that the app feels responsive.
  - Acceptance: tokens appear incrementally, not as one block.
  - Acceptance: first token appears in about 2 seconds when the backend is warm.

- As a user, I can stop a response mid-generation so that I do not wait for an answer I no longer want.
  - Acceptance: clicking Stop halts streaming within about 1 second.
  - Acceptance: the partial reply stays visible and the app accepts a new message.

- As a user, I see markdown and code rendered properly so that answers are readable.
  - Acceptance: headings, lists, bold, and links render.
  - Acceptance: fenced code blocks render in a distinct, formatted block.

- As a user, I can create multiple conversations and switch between them so that I can keep topics separate.
  - Acceptance: "New chat" creates a conversation that appears in the sidebar.
  - Acceptance: selecting a conversation loads its full message history.

- As a user, I find my history intact after the backend restarts so that I can trust the app with ongoing work.
  - Acceptance: after restarting the backend container, all conversations and messages are still present.

- As a user, I can upload a PDF to a conversation and ask questions about it so that answers come from my document.
  - Acceptance: a PDF upload succeeds and shows as attached to that conversation.
  - Acceptance: asking about its content triggers the retrieval tool and returns an answer grounded in the PDF.
  - Acceptance: a PDF uploaded in one conversation is not used in another.

- As a developer, I can run the whole app with one Docker command so that I can try the repo locally.
  - Acceptance: documented in the README; the app runs with only environment variables added.

- (Should) As a user, I can rename and delete conversations so that my sidebar stays organized.
  - Acceptance: rename updates the sidebar and persists across restart.
  - Acceptance: delete removes the conversation and its stored state after confirmation.

- (Should) As a returning user, the assistant remembers stable facts across my conversations so that I do not repeat myself.
  - Acceptance: a fact saved in one conversation is available in a new one from the same browser.
  - Acceptance: I can clear stored memory.

## Success metrics

- **Demo checklist passes on the live URL:** create a chat, stream a reply, stop one mid-way, upload a PDF and query it, restart the backend, and confirm history is intact.
- **Latency:** first token visible in about 2 seconds on a warm backend. Cold-start delay is documented, not counted.
- **Clean repo:** README, architecture diagram, one-command Docker run, and basic tests.
- **Schedule:** deployed v1 within 6 weeks.

Usage numbers (visits, chats) are not tracked in v1.

## Constraints

- **Deadline:** 6 weeks to a deployed, working v1.
- **Budget:** $0. Free tiers only; cold starts are accepted.
- **Hosting:** Docker. Backend on Railway or Render, frontend on Vercel.
- **Stack:** Python FastAPI with SSE; LangGraph StateGraph with a checkpointer keyed by `thread_id`; React chat UI with a conversation sidebar.
- **LLM:** Groq as default. API keys available for Groq, OpenRouter, and Mistral. The chosen model must support tool calling.
- **Identity:** no login; anonymous browser ID where an identifier is needed.
- **Persistence:** must survive restarts, so no in-memory-only checkpointer in production.

### Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Strangers burn the free API keys on a public demo | Per-browser/IP rate limits, message and upload size caps, spend alerts on provider dashboards |
| Free-tier cold starts or database expiry lose history or make the demo feel broken | Loading state in the UI, README note about cold starts, durable database choice verified against current free-tier terms, periodic export or backup |
| Scope creep: RAG, memory, and deploy in 6 weeks | Fixed Must list; build in order streaming, then persistence, then RAG, then deploy; Should and Could items only after Musts are deployed |
| Groq free-tier limits or outages | Provider abstraction with fallback to OpenRouter or Mistral; friendly error message on failure |

## Open questions

1. What is the product name?
2. Rename/delete is currently Should, not Must. Confirm.
3. Which persistent checkpointer backend: SQLite file or hosted Postgres? Verify free-tier storage and expiry terms on Railway, Render, and any database provider before choosing.
4. Which embedding model and vector store for RAG, and where do vectors persist on a free tier?
5. PDF limits: maximum file size, page count, and number of files per conversation.
6. Which Groq model supports tool calling reliably, and what are its current free-tier rate limits?
7. Rate limit thresholds (messages per minute, per day) per browser/IP.
8. Stop semantics: is the partial assistant message saved to thread state when generation is cancelled?
9. Long-term memory: what exactly is stored (facts, preferences), and how is it extracted?
10. Railway or Render for the backend: decide after checking current free-tier terms.
