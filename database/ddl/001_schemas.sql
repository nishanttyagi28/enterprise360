-- Layered schemas (STTM §1). raw = Python-owned landing; the rest are owned/built by dbt.
create schema if not exists raw;
create schema if not exists staging;
create schema if not exists intermediate;
create schema if not exists core;
create schema if not exists marts;
create schema if not exists snapshots;
