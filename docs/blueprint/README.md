# CHANGE OF PLAN (Jolly, 30 Oct 22:39 IST): SKIP THE BLUEPRINT. BUILD NOW.
Repo root = /workspace/enterprise360 (follows brief section 12 structure). Vertical slice first: Olist end-to-end, then UCI Online Retail II, then other domains.
Rules still apply: real public data only, no fabricated records, no false joins across datasets, production-quality code.
Ownership:
- Data Research: data/README.md (source, URL, license, checksum per dataset), download scripts' source configs, download Olist (+ marketing funnel) and UCI Online Retail II into data/raw (gitignored).
- Data Engineering: README, .gitignore, .env.example, docker-compose (Postgres), Makefile, pyproject, ingestion/, database/ddl, dbt_enterprise360/ (staging→intermediate→dims→marts), orchestration/ (Prefect), .github/workflows.
- KPI & Quality: governance/kpi_dictionary (YAML, Olist-supported KPIs), dbt tests/custom tests, tests/ (pytest unit/integration), docs/kpi-catalog.md, docs/assumptions-limitations.md.
- Power BI: powerbi/ PBIP (TMDL semantic model on the dbt marts, DAX measures matching KPI dictionary, PBIR Executive Command Center + Sales pages, dark navy theme JSON).
- Master (Grok Bot): coordination, integration review, copy to Jolly's laptop.

# TARGET RUNTIME = JOLLY'S LAPTOP (Windows 11, PowerShell 5.1)
- Project path: C:\Users\nishant\Projects\enterprise360 (master bot syncs repo there; all real runs happen there)
- Python 3.12.10 via `py -3.12` (also 3.14 default — use 3.12 for dbt compatibility). Create .venv with `py -3.12 -m venv .venv`.
- PostgreSQL 16 native Windows service (postgresql-x64-16), psql at C:\Program Files\PostgreSQL\16\bin. NO Docker installed → docker-compose stays optional; Makefile must have a PowerShell equivalent (scripts/*.ps1 or tasks via `python -m`).
- Git 2.52, VS Code installed. Power BI Desktop assumed.
- DB creds only via .env (user fills password locally). Never hardcode.
- Paths must be OS-agnostic (pathlib). Line endings: add .gitattributes.
