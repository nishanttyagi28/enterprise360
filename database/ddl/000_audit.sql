create schema if not exists raw;
-- One row per (source file, run). Drives incremental skip (sha256) and pipeline monitoring.
create table if not exists raw._load_audit (
    batch_id       uuid primary key,
    source_name    text        not null,
    source_file    text        not null,
    file_sha256    char(64)    not null,
    file_bytes     bigint      not null,
    target_table   text        not null,
    status         text        not null check (status in ('running', 'success', 'skipped', 'failed')),
    rows_loaded    bigint      not null default 0,
    started_at     timestamptz not null default now(),
    finished_at    timestamptz,
    error_message  text
);
create index if not exists ix_load_audit__source_status
    on raw._load_audit (source_name, status, finished_at desc);
