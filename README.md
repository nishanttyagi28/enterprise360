# Enterprise360

Enterprise retail / e-commerce analytics platform. **Power BI** is the consumption layer; this repo
holds the data platform underneath it: Python ingestion → PostgreSQL 16 → dbt (staging → intermediate
→ dimensional core → departmental marts) → Prefect orchestration, with data-quality results persisted
for BI. First vertical slice: **Olist Brazilian E-Commerce** (Kaggle `olistbr/brazilian-ecommerce`,
CC BY-NC-SA 4.0; see `data/README.md` for provenance/checksums, owned by Data Research).

## Architecture

```
data/raw/olist/*.csv ──► ingestion (python -m ingestion) ──► raw.*            (verbatim text + _ingested_at/_source_file/_batch_id/_row_hash)
                                                             raw._load_audit  (one row per file per run)
dbt (python -m orchestration.dbt_runner build):
  staging.stg_olist__*            views: rename (fix 'lenght' typos), cast, null-normalise, dedupe
  intermediate.int_olist__*       order-grain rollups, zip-prefix centroid, latest review, month coverage
  core.dim_* / core.fct_*         star schema (Power BI reads core directly)
  marts.mart_*                    pre-aggregated department marts (sales, product, operations, business)
  core.dq_results / dq_reconciliation   DQ history per run (on-run-end hook → dq.dq_results_log)
  snapshots.snap_olist__sellers   SCD2 on seller location
orchestration (python -m orchestration.flow): Prefect flow init-db → ingest → dbt deps → freshness → build
```

| Layer | Owner | Materialisation | Why |
|---|---|---|---|
| raw | Python | tables, all `text` | lossless landing; a malformed value never fails a load, typing happens once in dbt |
| staging | dbt | views | thin, always current |
| intermediate | dbt | views (centroid: table) | explicit grains; geolocation (1M rows) aggregated once |
| core | dbt | tables; `fct_order_items`, `fct_payments` incremental (delete+insert on natural key) | BI import performance; incrementals only where a single input drives the fact |
| marts | dbt | tables | small, BI-ready, ratios stored with numerator/denominator |

### Core model (grain → keys)
| Model | Grain | Keys |
|---|---|---|
| `fct_orders` | order | `order_sk`, `customer_sk`, `geography_sk`, `purchase_date_key` |
| `fct_order_items` | order line `(order_id, order_item_id)` (1 line = 1 unit) | `order_item_sk`, `product_sk`, `seller_sk`, `purchase_date_key`; `shipping_limit_at`, `is_handover_on_time` |
| `fct_payments` | `(order_id, payment_sequential)` | `payment_sk`, `order_sk` |
| `fct_reviews` | `(review_id, order_id)` (review_id alone is not unique) | `review_sk`, `is_latest_for_order` |
| `fct_deliveries` | order (delivery view) | `is_on_time`, `is_otd_eligible`, `delivery_days` |
| `dim_customer` | `customer_unique_id` (the person; Olist issues a new `customer_id` per order) | `customer_sk` |
| `dim_product` / `dim_seller` / `dim_geography` / `dim_date` | product / seller / zip prefix / day | `*_sk`, `date_key` (YYYYMMDD) |

Surrogate keys are `dbt_utils.generate_surrogate_key` hashes of business keys, so facts derive FKs
without lookup joins and keys are stable across rebuilds.

### Fan-out rules (enforced by tests)
- Payments are **never** joined to order lines; both are rolled up to order grain first
  (`int_olist__order_items_aggregated`, `int_olist__order_payments_aggregated`).
- Geolocation is collapsed to one row per zip prefix (`int_olist__zip_prefix_centroid`,
  **median** lat/lng of in-Brazil points, modal city/state) before any join.
- Order-level CSAT uses one review per order (`int_olist__order_review_latest`).
- Marts aggregate each fact to the mart grain separately and join the aggregates 1:1.
- Reconciliation tests: fact vs staging totals, order rollups vs lines/payments, marts vs facts,
  raw vs core orders (`tests/assert_recon_*`), plus `assert_payments_vs_items_freight` (**warn**:
  ~1.1k orders legitimately differ - vouchers, installment interest, payments without items).

### Business rules worth knowing
- **GMV is not revenue** (KPI_GMV = Σ item_price; freight excluded). Net GMV excludes `canceled`/`unavailable`.
- **Complete months** (`int_olist__month_coverage` → `dim_date.is_complete_month`,
  `mart_business_overview_monthly.is_partial_month = NOT is_complete_month`, tested):
  a month is complete when the whole calendar month lies within [min, max] order purchase date
  (2016-09 and 2018-10 are false). `is_low_volume_month` = orders < 10% (`var olist_low_volume_ratio`)
  of the median complete month (flags 2016-10..12 ramp-up and the 16-order 2018-09 tail).
  `is_reporting_month` = complete AND not low volume → use for trends and MoM growth.
- **OTD** (`fct_deliveries.is_on_time`): delivered date ≤ estimated date, over `is_otd_eligible`
  orders (status delivered, delivery timestamp present and not before purchase).
- **Seller handover SLA** (`fct_order_items.is_handover_on_time`): `delivered_carrier_at <= shipping_limit_at`
  per line (carrier date is order-level, deadline is per line); NULL if either is missing.

### Data quality results (`core.dq_results`)
One row per `run_id` (dbt invocation_id) × `check_id` (test unique_id), appended every dbt run by the
`on-run-end` hook (`macros/dq_results_log.sql`) into `dq.dq_results_log` (created by `on-run-start`,
so a fresh DB works). Columns: run_id, run_at, check_id, check_name, layer, model_name, kpi_id,
severity (`block` = dbt error / `warn`), weight, status (`pass`/`warn`/`fail`), failing_rows,
source_value, mart_value, variance (+ test_type, dbt_status, execution_seconds, is_latest_run).
- dbt `error` → `fail`; **`skipped` → `fail`** (a check that did not run proved nothing).
- `kpi_id` / `weight` / `layer` come from seed `dq_check_config` (LIKE pattern on check name, longest
  match wins; owned by KPI & Quality). Default weight: **block = 3, warn = 1**; kpi_id NULL.
- source/mart/variance are captured at log time from `core.dq_reconciliation` (variance = mart − source).

**DQ score (KPI_DQ_SCORE)**, strict: only `pass` earns weight (`warn` and `fail` earn 0):
`dq_score = Σ weight[status='pass'] / Σ weight` over all checks of the latest `run_id`.
`core.dq_run_summary` (one row per run_id) exposes total/passed/warned/failed checks, failed block
checks, total/passed/warned weight and `dq_score`, so warns are visible as their own measure:
```sql
select dq_score, warned_checks, failed_checks from core.dq_run_summary where is_latest_run;
```

## UCI Online Retail II (independent domain)
UK online retailer, GBP, 2009-12 → 2011-12. **Never joined to Olist**: own raw table, own schemas
(`uci_staging`, `uci_intermediate`, `uci_core`, `uci_marts`), own dims (product, customer, country) and
its own `uci_dim_date` built from the same calendar macros as `dim_date`. Plan, decisions, profiling
and checksums: `docs/blueprint/uci-online-retail-plan.md`.
- Load: `python -m ingestion uci` (or `.\scripts\run.ps1 -Domain uci`; default `-Domain all` loads both, independently) (both yearly CSVs → `raw.uci_online_retail_ii_lines`; each file
  replaced independently; `_source_line_no` = row position, the only line key).
- Dedup (staging): exact duplicates within a file dropped (DQ warn); where a later file restates a
  window (2010-12-01..09), only the later file's lines are kept. Both logged with before/after counts in
  `core.dq_results`.
- Facts: `uci_fct_invoice_lines` (line grain, signed; cancellations are negative lines) and
  `uci_fct_invoices` (invoice grain). `line_type` from seed `uci_stockcode_class` + rules (postage,
  fee, discount, manual, voucher, stock_writeoff, zero_price, bad_debt, …).
- Measures: `gross_product_sales` (product lines, non-C), `product_cancellations`, `discounts`,
  **`net_sales_proxy_gbp` = Net Sales (proxy)** = product + cancellations + discounts; postage and fees
  reported separately; `invoiced_value_gbp` = all lines.
- AOV (`uci_mart_sales_daily.aov_gbp`) = Net Sales (proxy) / sales (non-C) invoices. It is a daily ratio
  (non-additive): in BI compute monthly AOV as `sum(net_sales_proxy_gbp) / sum(sales_invoice_count)`.

## Ingestion design
- Contracts (`ingestion/sources/olist.py`): exact headers in order (typos preserved), natural keys.
- Header validation (BOM-safe, explicit UTF-8) → **COPY** streamed in binary chunks (no newline/codepage
  translation on Windows) into a temp table → single-transaction replace of the raw table → ANALYZE.
- **Idempotent + incremental**: file sha256 compared with the last successful load in `raw._load_audit`;
  unchanged files are skipped, `--force` reloads. Re-runs never duplicate rows.
- `_row_hash` = sha256 of U+001F-joined values, computed in SQL; `ingestion.loaders.row_hash` is the
  tested Python reference. Connection retries with exponential back-off (tenacity). JSON logs (structlog).

## Setup & run — Windows laptop (target runtime; PowerShell 5.1, Python 3.12, PostgreSQL 16 service)
```powershell
cd C:\Users\nishant\Projects\enterprise360
Copy-Item .env.example .env        # then edit .env: POSTGRES_PASSWORD=<e360_app password>
.\scripts\setup.ps1 -CreateTestDatabase   # venv (py -3.12), pip install, DDL, dbt deps, dbt debug
.\scripts\run.ps1 -Test                   # ingest data\raw\olist -> dbt freshness + build -> pytest/ruff/mypy
.\scripts\run.ps1 -Prefect                # same pipeline as a Prefect flow
```
- DB `enterprise360` owned by `e360_app` is assumed to exist; `-CreateDatabase` creates role+DB as
  `POSTGRES_ADMIN_USER` if needed.
- `-CreateTestDatabase` needs CREATEDB on `e360_app`. If missing, a superuser runs once:
  `& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -U postgres -c "CREATE DATABASE enterprise360_test OWNER e360_app;"`
- If scripts are blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- Equivalent `python -m` entry points (any OS): `python -m ingestion init-db`, `python -m ingestion olist
  [--source-dir DIR] [--force]`, `python -m ingestion uci [--source-dir DIR] [--force]`, `python -m orchestration.dbt_runner <dbt args>` (loads `.env`, uses the
  in-repo `dbt_enterprise360/profiles.yml`), `python -m orchestration.flow`.

## Setup & run — Linux/macOS
`make setup && make ingest && make dbt-build && make test && make lint typecheck` (or `make flow`).
`docker-compose.yml` is **optional** (`make db-up`); the reference runtime is a native PostgreSQL 16.

## Tests
- `pytest`: unit (contracts, BOM, hashing, null normalisation, DDL↔contract sync, KPI dictionary) and
  integration (live DB: COPY load, idempotent re-run, forced reload replaces, changed-file reload,
  SQL/Python row-hash parity, audit). Integration tests load fixtures into `E360_TEST_DB`
  (default `enterprise360_test`) and refuse the main DB.
- `dbt build`: ~230 tests (Olist + UCI, incl. KPI & Quality's `tests/uci`, enabled by var `uci_models_built: true`) (unique/not_null/relationships/accepted_values, dbt_utils, grain, fan-out,
  reconciliation, coverage consistency) interleaved with models.
- Fixtures: `tests/fixtures/olist` (synthetic, FK-consistent, covers the known quirks; CI runs on these).

## Configuration
All credentials come from `.env` (gitignored): `POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER,
POSTGRES_PASSWORD`, plus `E360_TEST_DB`, `E360_OLIST_DIR`, `E360_UCI_DIR`, `E360_LOG_LEVEL`, `E360_DBT_THREADS`.
