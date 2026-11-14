-- Migration 003: doc_chunks table for vector embeddings
-- Applied by app/db/migrate.py on first startup.

create extension if not exists vector;

create table if not exists doc_chunks (
    id              uuid primary key,
    thread_id       uuid not null references conversations(id) on delete cascade,
    document_id     uuid not null references documents(id) on delete cascade,
    page            integer not null,
    content         text not null,
    embedding       vector(384) not null,  -- all-MiniLM-L6-v2 produces 384-dim embeddings
    created_at      timestamptz not null default now()
);

create index if not exists doc_chunks_thread_id
    on doc_chunks (thread_id);

create index if not exists doc_chunks_document_id
    on doc_chunks (document_id);

-- HNSW index for vector similarity search (requires pgvector >= 0.5.0)
create index if not exists doc_chunks_embedding_hnsw
    on doc_chunks using hnsw (embedding vector_cosine_ops)
    with (m = 16, ef_construction = 64);