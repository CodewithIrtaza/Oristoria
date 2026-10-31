-- Migration 001: conversations table
-- Applied by app/db/migrate.py on first startup.

create table if not exists conversations (
    id          uuid primary key,
    anon_id     uuid not null,
    title       text not null default 'New chat',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create index if not exists conversations_anon_id_updated_at
    on conversations (anon_id, updated_at desc);
