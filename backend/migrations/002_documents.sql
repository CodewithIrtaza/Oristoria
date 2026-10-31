-- Migration 002: documents table
-- Applied by app/db/migrate.py on first startup.

create table if not exists documents (
    id              uuid primary key,
    conversation_id uuid not null references conversations(id) on delete cascade,
    filename        text not null,
    size_bytes      integer not null,
    page_count      integer not null,
    chunk_count     integer not null,
    status          text not null check (status in ('ready', 'failed')),
    error           text,
    created_at      timestamptz not null default now()
);
