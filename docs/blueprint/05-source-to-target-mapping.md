# 05 — Source-to-Target Mapping (STTM)
Owner: Data Engineering · Status: **Olist IMPLEMENTED** (§1–2 match the code in `ingestion/`, `database/ddl/`, `dbt_enterprise360/`); §3–6 PROPOSED.
Column-level detail: `docs/source-to-target-mapping.md`. Lineage diagram: `docs/data-lineage.md`.

## 1. Conventions (implemented)
- Layers: `raw` (Python: `python -m ingestion`) → `staging` (dbt views) → `intermediate` (dbt views; geolocation centroid = table) → `core` (dims/facts, tables; `fct_order_items`, `fct_payments` incremental delete+insert) → `marts` (tables). DQ: `dq.dq_results_log` (hook) → `core.dq_results`, `core.dq_run_summary`, `core.dq_reconciliation`.
- Raw = all `text`, exact source headers (typos kept), plus `_ingested_at timestamptz`, `_source_file`, `_batch_id uuid`, `_row_hash char(64)` = sha256 of U+001F-joined values. NOT NULL only on natural-key columns. Loads: COPY → temp table → one-transaction replace, skipped when the file sha256 equals the last successful load (`raw._load_audit`).
- Staging (`macros/clean_text.sql`): `''`, whitespace, `NA`, `nan`, `null`, `none` → NULL; trim; cities lower-case, states upper-case; zip prefixes `lpad(…,5,'0')`; timestamps `::timestamp` (Brazil local time, no zone, never shifted); money `numeric(12,2)` BRL. Dedupe per business key keeping latest `_ingested_at` (`macros/dedupe.sql`).
- Surrogate keys: `dbt_utils.generate_surrogate_key(<business key>)` → facts derive FKs without lookups. Date FK: `date_key = YYYYMMDD` integer.
- Not done (vs earlier draft): `unaccent()` on city names, DQ quarantine counts for failed casts (casts fail the build instead).

## 2. Olist Brazilian E-Commerce
Kaggle `olistbr/brazilian-ecommerce`, 9 CSVs, CC BY-NC-SA 4.0. Loaded row counts (2026-10-30): orders 99,441 · customers 99,441 · order_items 112,650 · payments 103,886 · reviews 99,224 · products 32,951 · sellers 3,095 · geolocation 1,000,163 · translation 71. Purchases 2016-09-04 → 2018-10-17.

| Source file | raw | staging | intermediate | core |
|---|---|---|---|---|
| olist_orders_dataset | raw.olist_orders | stg_olist__orders | int_olist__order_items_enriched, int_olist__month_coverage | fct_orders, fct_deliveries, dim_date flags |
| olist_customers_dataset | raw.olist_customers | stg_olist__customers | int_olist__customer_order_map | dim_customer (BK customer_unique_id) |
| olist_order_items_dataset | raw.olist_order_items | stg_olist__order_items | int_olist__order_items_aggregated / _enriched | fct_order_items; fct_orders rollups |
| olist_order_payments_dataset | raw.olist_order_payments | stg_olist__order_payments | int_olist__order_payments_aggregated | fct_payments; fct_orders rollups |
| olist_order_reviews_dataset | raw.olist_order_reviews | stg_olist__order_reviews | int_olist__order_review_latest | fct_reviews; fct_orders.latest_review_score |
| olist_products_dataset | raw.olist_products | stg_olist__products | — | dim_product |
| product_category_name_translation | raw.olist_product_category_name_translation | stg_olist__category_translation | — | dim_product.category_name_en |
| olist_sellers_dataset | raw.olist_sellers | stg_olist__sellers | — | dim_seller; snapshots.snap_olist__sellers (SCD2) |
| olist_geolocation_dataset | raw.olist_geolocation | stg_olist__geolocation | int_olist__zip_prefix_centroid | dim_geography |

Rules (CONFIRMED on loaded data unless marked):
- **Grains**: fct_orders/fct_deliveries = order; fct_order_items = (order_id, order_item_id), 1 line = 1 unit; fct_payments = (order_id, payment_sequential); fct_reviews = (review_id, order_id) — 789 review_ids span several orders, 547 orders have >1 review; order CSAT uses the latest review per order.
- **Customer**: dim_customer grain = customer_unique_id (96,096 people; 2,997 with ≥2 orders); location from the latest order. Facts resolve `customer_sk` via `int_olist__customer_order_map` (1:1 on customer_id).
- **Status**: `is_canceled` = status in (canceled, unavailable) → KPI_NET_GMV / KPI_CANCEL_RATE.
- **Delivery**: `is_otd_eligible` = delivered AND delivered_customer_at present AND ≥ purchased_at; `is_on_time` = delivered date ≤ estimated date. Seller handover `fct_order_items.is_handover_on_time` = delivered_carrier_at ≤ shipping_limit_at (NULL if either missing).
- **Products**: 610 without category → `'unknown'`; 2 categories without translation (pc_gamer, portateis_cozinha_e_preparadores_de_alimentos) → pt name, `is_category_translated=false`. Typos `…_lenght` renamed `…_length`.
- **Geography**: one row per zip prefix (19,173): union of geolocation, customer and seller prefixes; points outside the Brazil bbox (lat −34..6, lng −74..−34) dropped; centroid = **median** lat/lng, modal city/state; 163 prefixes (157 customer, 7 seller, overlapping) have no points → NULL coordinates, `has_coordinates=false`. Raw geolocation is never joined directly.
- **Fan-out**: payments never joined to items; both rolled up to order grain first. Payments vs items+freight differ for 1,076 orders (vouchers, interest, payments without items) → warn test, quantified in dq_reconciliation.
- **Month coverage** (`int_olist__month_coverage`): complete = whole month inside [min, max] purchase date; low volume = < 10% of median complete-month orders; reporting = complete AND not low volume (excludes 2016-09..12, 2018-09, 2018-10).

## 3. IBM HR Analytics Employee Attrition (People domain) — ASSUMPTION pending 03
Single CSV (~1,470 rows, 35 cols; IBM-created **fictional** data — 03 must classify REAL vs SIMULATED; if SIMULATED the brief's "avoid simulated" rule may exclude it). Mapping: `EmployeeNumber` → BK; `Age, Department, JobRole, JobLevel, MonthlyIncome, YearsAtCompany, Attrition(Yes/No→bool), OverTime, ...` → `hr.stg_ibm_hr__employees` → `core_hr.dim_employee_snapshot` + `core_hr.fct_workforce_snapshot` (grain: employee at single undated snapshot). Drop constant columns `EmployeeCount, StandardHours, Over18` (zero variance). No dates → no time-series headcount, no attendance, no payroll facts.

## 4. CFPB Consumer Complaint Database (Customer Service / Risk) — ASSUMPTION pending 03
CSV/API from consumerfinance.gov. Key columns (verify): `Complaint ID` (BK), `Date received`, `Date sent to company`, `Product, Sub-product, Issue, Sub-issue, Company, State, ZIP code, Submitted via, Company response to consumer, Timely response?, Consumer disputed?`. → `raw.cfpb_complaints` → `stg_cfpb__complaints` → `core_cfpb.fct_complaints` (grain: one complaint). Joins only to `dim_date` (date received). Companies are US financial firms — **not** Olist or any retailer; no customer join.

## 5. SEC EDGAR Financial Statement Data Sets (Finance benchmark) — ASSUMPTION pending 03
Quarterly zips `sub.txt, num.txt, tag.txt, pre.txt` (tab-delimited). `sub.adsh` (BK filing), `num(adsh, tag, version, ddate, qtrs, uom, coreg, value)`. → `raw.sec_sub/num/tag/pre` → `stg_sec__*` → `core_sec.fct_financial_fact` (grain: adsh × tag × ddate × qtrs × uom × coreg), `dim_sec_company` (cik), `dim_sec_tag`. Filter to retail SICs (e.g. 5311, 5331, 5961 — ASSUMPTION) for public-retailer P&L benchmarking. Not the company's own P&L.

## 6. M5 Forecasting (Walmart) — ASSUMPTION pending 03
`calendar.csv, sales_train_evaluation.csv (wide d_1..d_1941), sell_prices.csv`. Wide → long unpivot in Python **before** load? No: PROPOSED unpivot in dbt staging is ~59M rows — performed in Python (pandas `melt` per chunk) into `raw.m5_sales_long` to keep Postgres scans sane. Grain: item_id × store_id × d. `sell_prices(store_id,item_id,wm_yr_wk,sell_price)` joins via calendar `wm_yr_wk`. → `core_m5.fct_daily_unit_sales`, `dim_m5_item`, `dim_m5_store`. Revenue = units × sell_price is **DERIVED** and only where price exists. Joins `dim_date` via calendar.date.

## 7. Cross-source rule
No key in sections 3–6 maps to any Olist dimension. Only `core.dim_date` is shared (calendar semantics are genuinely identical). Each domain lives in its own schema (`core_hr`, `core_cfpb`, `core_sec`, `core_m5`) and mart folder.

## 8. Out of mapping
UCI Online Retail II: planned as a separate source-specific domain (no conformed joins with Olist) — see `uci-online-retail-plan.md`.

## 9. Reconciliation status with 03/04
03 and 04 did not exist at write time. Every non-Olist mapping and every Olist row-count/uniqueness claim above must be re-checked against them.
