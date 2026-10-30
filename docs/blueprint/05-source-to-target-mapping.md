# 05 — Source-to-Target Mapping (STTM)
Owner: Data Engineering · Status: PROPOSED · Depends on: 03-dataset-catalogue.md, 04-dataset-feasibility-matrix.md (**not present at time of writing — reconciliation pending**, see §9)

Tags: **CONFIRMED FACT** = verifiable from publisher page / file headers; **PROPOSED** = design decision; **ASSUMPTION** = depends on a dataset/fact not yet verified by 03/04.

## 1. Conventions
- Layers: `raw` (Python-owned, all columns `text`, verbatim + load metadata) → `staging` (dbt views: rename, cast, trim, null-normalise, dedupe) → `intermediate` (dbt: joins/allocations/aggregations at explicit grains) → `core` (conformed dims/facts per domain) → `marts` (department-facing, Power BI). PROPOSED.
- Raw is typeless (`text`) so a malformed value never fails the load; typing happens once, in staging, via `try_cast`-style macros that route failures to a DQ quarantine count. Justification: lossless landing + single place for parse rules.
- Load metadata on every raw table: `_ingested_at timestamptz`, `_source_file text`, `_batch_id uuid`, `_row_hash char(64)` (SHA-256 of the normalised source row). `_row_hash` drives idempotent upsert and change detection.
- Null normalisation in staging: `''`, `'NA'`, `'nan'`, whitespace-only → `NULL`. Strings `trim()`; city names `lower(unaccent())` kept *in addition* to the original.
- Dedup rule (staging): exact duplicates on full business key + `_row_hash` collapsed with `row_number() over (partition by <bk> order by _ingested_at desc)`; non-identical duplicates on the business key are **flagged, not silently dropped** (test `warn`, counted in DQ mart).
- Currency: Olist monetary values are BRL (CONFIRMED FACT per Kaggle description). Stored as `numeric(12,2)`; no FX conversion (no real FX source in scope → would be fabrication).

## 2. Olist Brazilian E-Commerce (primary e-commerce core)
Source: Kaggle `olistbr/brazilian-ecommerce`, 9 CSVs, CC BY-NC-SA 4.0 (CONFIRMED FACT per Kaggle page; row counts to be confirmed by 03 — **ASSUMPTION** ~99.4k orders, 2016-09 → 2018-10).

### 2.1 olist_orders_dataset.csv → raw.olist_orders → staging.stg_olist__orders → core.fct_orders
| Source column | raw type | staging column | type | rule | target |
|---|---|---|---|---|---|
| order_id | text | order_id | varchar(32) | trim; NOT NULL; unique | fct_orders.order_id (degenerate), BK |
| customer_id | text | customer_id | varchar(32) | trim; NOT NULL | → dim_customer via customer_id→customer_unique_id (see 2.2) |
| order_status | text | order_status | varchar(20) | lower; accepted_values {delivered, shipped, canceled, unavailable, invoiced, processing, created, approved} | fct_orders.order_status; derived `is_canceled`, `is_delivered` |
| order_purchase_timestamp | text | purchased_at | timestamp | parse `YYYY-MM-DD HH24:MI:SS`; NOT NULL | purchase_date_key, purchased_at |
| order_approved_at | text | approved_at | timestamp | nullable | approved_at, hours_to_approve |
| order_delivered_carrier_date | text | delivered_carrier_at | timestamp | nullable | fct_deliveries |
| order_delivered_customer_date | text | delivered_customer_at | timestamp | nullable; flag if < purchased_at | fct_deliveries.delivery_days |
| order_estimated_delivery_date | text | estimated_delivery_at | timestamp | NOT NULL expected | fct_deliveries.is_on_time |
Timestamps are local Brazil time without zone (ASSUMPTION — publisher does not state TZ); stored as `timestamp` (no TZ), never shifted.
Business rules: `delivered` with null `delivered_customer_at` → kept, flagged `dq_missing_delivery_ts`. Delivery KPIs computed only for `order_status='delivered' and delivered_customer_at is not null`.

### 2.2 olist_customers_dataset.csv → raw.olist_customers → stg_olist__customers → core.dim_customer
| Source | staging | type | rule | target |
|---|---|---|---|---|
| customer_id | customer_id | varchar(32) | PK in staging; one per order (CONFIRMED FACT per Kaggle docs: a new customer_id per order) | bridge/lookup only |
| customer_unique_id | customer_unique_id | varchar(32) | NOT NULL | dim_customer BK (the real person) |
| customer_zip_code_prefix | customer_zip_prefix | char(5) | `lpad(...,5,'0')` (leading zeros lost in CSV readers) | dim_geography FK |
| customer_city | customer_city | text | trim, lower | attribute |
| customer_state | customer_state | char(2) | upper; accepted 27 UF codes | attribute |
Rule: dim_customer grain = `customer_unique_id`. Customer attributes per unique id taken from the **latest order** (by purchased_at). `int_olist__customer_order_map` keeps `customer_id → customer_unique_id` so facts resolve `customer_sk`. Without this, repeat-purchase and retention KPIs are wrong (every order looks like a new customer).

### 2.3 olist_order_items_dataset.csv → raw.olist_order_items → stg_olist__order_items → core.fct_order_items
| Source | staging | type | rule | target |
|---|---|---|---|---|
| order_id | order_id | varchar(32) | FK orders | degenerate |
| order_item_id | order_item_id | smallint | 1..n sequence within order | PK part |
| product_id | product_id | varchar(32) | FK products | product_sk |
| seller_id | seller_id | varchar(32) | FK sellers | seller_sk |
| shipping_limit_date | shipping_limit_at | timestamp | | seller SLA |
| price | item_price | numeric(12,2) | ≥0 | measure |
| freight_value | freight_value | numeric(12,2) | ≥0 | measure |
PK `(order_id, order_item_id)`. One row = one unit (quantity is expressed by repeated rows; CONFIRMED FACT per dataset docs — verify in 03). `item_quantity = 1` constant.

### 2.4 olist_order_payments_dataset.csv → raw.olist_order_payments → stg_olist__order_payments → core.fct_payments
| Source | staging | type | rule |
|---|---|---|---|
| order_id | order_id | varchar(32) | FK |
| payment_sequential | payment_sequential | smallint | PK part |
| payment_type | payment_type | varchar(20) | accepted {credit_card, boleto, voucher, debit_card, not_defined} |
| payment_installments | payment_installments | smallint | ≥0 (0 observed → flag) |
| payment_value | payment_value | numeric(12,2) | ≥0 |
PK `(order_id, payment_sequential)`. **Never joined to order_items** (many×many fan-out). Reconciliation: `sum(payment_value)` per order vs `sum(price+freight)` per order — difference tracked (vouchers/installment interest), tolerance 0.01 BRL flagged not failed.

### 2.5 olist_order_reviews_dataset.csv → raw.olist_order_reviews → stg_olist__order_reviews → core.fct_reviews
| Source | staging | type | rule |
|---|---|---|---|
| review_id | review_id | varchar(32) | NOT unique alone (ASSUMPTION — known community finding; confirm in 03) |
| order_id | order_id | varchar(32) | FK |
| review_score | review_score | smallint | CHECK 1..5 |
| review_comment_title | review_title | text | nullable, Portuguese |
| review_comment_message | review_message | text | nullable; embedded newlines → CSV parser must be quote-aware |
| review_creation_date | review_created_at | timestamp | |
| review_answer_timestamp | review_answered_at | timestamp | |
PK `(review_id, order_id)`; exact dup rows removed. Order-level CSAT uses `int_olist__order_review_latest` (latest review per order) to avoid double counting multiple reviews per order.

### 2.6 olist_products_dataset.csv → stg_olist__products → core.dim_product
| Source | staging | type | rule |
|---|---|---|---|
| product_id | product_id | varchar(32) | BK |
| product_category_name | category_name_pt | text | null → `'unknown'` member |
| product_name_lenght (sic) | product_name_length | int | rename typo |
| product_description_lenght (sic) | product_description_length | int | rename typo |
| product_photos_qty | product_photos_qty | int | |
| product_weight_g | product_weight_g | int | ≥0 |
| product_length_cm / height_cm / width_cm | same | int | derived `product_volume_cm3` |

### 2.7 product_category_name_translation.csv → stg_olist__category_translation → dim_product.category_name_en
`product_category_name` → `category_name_pt`, `product_category_name_english` → `category_name_en`. Left join from products; categories missing a translation (ASSUMPTION: a small number exist) → fall back to pt name, flagged.

### 2.8 olist_sellers_dataset.csv → stg_olist__sellers → core.dim_seller
`seller_id` (BK), `seller_zip_code_prefix` → `seller_zip_prefix` char(5) lpad, `seller_city`, `seller_state`.

### 2.9 olist_geolocation_dataset.csv → stg_olist__geolocation → int_olist__zip_prefix_centroid → core.dim_geography
| Source | staging | rule |
|---|---|---|
| geolocation_zip_code_prefix | zip_prefix char(5) | lpad |
| geolocation_lat / lng | lat/lng numeric(9,6) | drop points outside Brazil bbox (lat −34..6, lng −74..−34) |
| geolocation_city / state | city/state | lower/unaccent; upper |
Many rows per zip prefix (CONFIRMED FACT per dataset docs). Intermediate aggregates to **one row per zip_prefix**: median lat/lng, modal city/state. Joining raw geolocation to customers/sellers would multiply rows — prohibited.

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
UCI Online Retail zip is present in `/datasets` but not in this brief's source list → not mapped; decision for master/Data Research.

## 9. Reconciliation status with 03/04
03 and 04 did not exist at write time. Every non-Olist mapping and every Olist row-count/uniqueness claim above must be re-checked against them.
