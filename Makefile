# Linux/macOS convenience targets. Windows: use scripts/*.ps1 (same steps, same python -m entry points).
PY      ?= .venv/bin/python
DBT      = $(PY) -m orchestration.dbt_runner
OLIST_DIR ?=
UCI_DIR   ?=
FUNNEL_DIR ?=

.PHONY: setup db-up db-init ingest ingest-olist ingest-uci ingest-funnel ingest-fixtures dbt-deps dbt-build dbt-docs test test-unit lint typecheck flow clean

setup:            ## create venv + install project with dev extras
	python3.12 -m venv .venv
	$(PY) -m pip install -U pip
	$(PY) -m pip install -e ".[dev]"
	@test -f .env || cp .env.example .env

db-up:            ## OPTIONAL container DB (target runtime uses a native PG16 service instead)
	docker compose up -d --wait postgres

db-init:          ## schemas + raw tables + audit table (idempotent)
	$(PY) -m ingestion init-db

ingest: ingest-olist ingest-uci ingest-funnel   ## load Olist + UCI + Funnel CSVs (unchanged files are skipped)

ingest-olist: db-init
	$(PY) -m ingestion olist $(if $(OLIST_DIR),--source-dir $(OLIST_DIR),)

ingest-uci: db-init
	$(PY) -m ingestion uci $(if $(UCI_DIR),--source-dir $(UCI_DIR),)

ingest-funnel: db-init
	$(PY) -m ingestion funnel $(if $(FUNNEL_DIR),--source-dir $(FUNNEL_DIR),)

ingest-fixtures: db-init
	$(PY) -m ingestion olist --source-dir tests/fixtures/olist
	$(PY) -m ingestion uci --source-dir tests/fixtures/uci
	$(PY) -m ingestion funnel --source-dir tests/fixtures/funnel

dbt-deps:
	$(DBT) deps

dbt-build: dbt-deps   ## models + tests + seeds + snapshots in DAG order; logs DQ to core.dq_results
	$(DBT) source freshness
	$(DBT) build

dbt-docs:
	$(DBT) docs generate

test:             ## unit + integration (integration needs a *_test/_fixture/_ci database)
	$(PY) -m pytest

test-unit:
	$(PY) -m pytest -m "not integration"

lint:
	$(PY) -m ruff check ingestion orchestration tests
	$(PY) -m ruff format --check ingestion orchestration

typecheck:
	$(PY) -m mypy

flow:             ## Prefect flow: init-db -> ingest olist + uci + funnel (independent) -> dbt deps/freshness/build
	$(PY) -m orchestration.flow

clean:
	$(DBT) clean
