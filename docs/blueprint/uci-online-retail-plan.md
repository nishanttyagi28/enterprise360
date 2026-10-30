# UCI Online Retail II — implementation plan
Owner: Data Engineering · Status: **BUILT 2026-10-30** (decisions D1–D6 approved; see §0) · Source: UCI ML Repository "Online Retail II" (id 502, CC BY 4.0 per UCI page — Data Research to confirm in data/README.md).
Domain rule: **independent source**. No conformed joins with Olist (different company, country, currency GBP vs BRL, period). Nothing in `uci` ever joins a `core.*` Olist table.

## 0. As built (2026-10-30, real files)
- Files and checksums (pass to Data Research for data/README.md):
  | File | Bytes | SHA-256 |
  |---|---|---|
  | online_retail_II_Year_2009-2010.csv | 46,810,498 | `17181af53059386e360acb2714218558ef526f84acacc768ebbdd3a35623d941` |
  | online_retail_II_Year_2010-2011.csv | 48,039,783 | `9f3414a3d06748ef953051fa6e2e183b1591047bdfda95e99afd5888de28eb16` |
  UTF-8, no BOM, LF line endings.
- Dedup: raw 1,067,371 → within-file exact duplicates dropped 12,133 (DQ warn `assert_uci_exact_duplicates_dropped`) → overlap window 2010-12-01 08:26..2010-12-09 20:01: 44,404 lines → 22,202 kept (later file's copy; 22,202 dropped; `assert_uci_overlap_deduped`, every dropped line has an identical line in the later file) → **1,033,036 lines**. (22,523 raw overlap rows − 321 that were also within-file duplicates = 22,202.)
- Totals (GBP): gross product sales 19,643,861.64 · product cancellations −716,462.57 · discounts −12,879.63 · **Net Sales (proxy) 18,914,519.44** · postage 433,410.51 · fees −264,936.18 · other non-product −227,460.07 · invoiced value (all lines) 18,855,533.70.
- Objects: schemas `uci_staging` (stg_uci__invoice_lines_all, stg_uci__invoice_lines), `uci_intermediate` (int_uci__invoice_lines_classified, int_uci__product_descriptions, int_uci__month_coverage, int_uci__dedup_stats), `uci_core` (uci_fct_invoice_lines, uci_fct_invoices, uci_dim_product, uci_dim_customer, uci_dim_country, uci_dim_date, seed uci_stockcode_class), `uci_marts` (uci_mart_sales_daily, uci_mart_product_monthly, uci_mart_country_monthly, uci_mart_customer_cohorts, uci_mart_customer_rfm).
- Changes vs plan below: separate `uci_dim_date` (shared macros `calendar_spine`/`calendar_columns`, not a shared table); line types renamed to match KPI & Quality tests (`stock_writeoff` = non-C, qty<0, price 0; other price-0 lines = `zero_price`); overlap rule = rows of an earlier file at/after the first timestamp of a later file (not a hard-coded date); line timestamps column `invoice_ts`.
- Single AOV definition (KPI_UCI_AOV): net_sales_proxy_gbp / sales invoices (45,336 total) = £417.21 overall; recompute from summed components, never average daily aov_gbp.
- Net Sales (proxy) = product lines (sales + cancellations, signed) + discount lines. Gross product sales = product lines on non-C invoices (all have qty>0, price>0).

## 1. Profiling (real files, 2026-10-30, duckdb over the CSVs)
| Check | Result |
|---|---|
| Rows | 2009-2010: 525,461 (2009-12-01 07:45 → 2010-12-09 20:01); 2010-2011: 541,910 (2010-12-01 08:26 → 2011-12-09 12:50) |
| **File overlap** | 2010-12-01..2010-12-09: **22,523 rows identical in both files** (1,088 invoices) — the second file restates that window |
| Exact duplicate rows | 6,865 within file 1, 5,268 within file 2; **34,335 removed overall** → 1,033,036 distinct rows |
| (Invoice, StockCode) not unique after exact dedupe | 11,162 pairs (same item on several lines of one invoice) → no natural line key |
| Invoices | 53,628 distinct; 8,292 cancellation invoices (`C…`, 19,494 rows); 6 `A…` rows = "Adjust bad debt" (StockCode B, 5 negative prices) |
| Negative quantity | 22,950 rows: 19,493 are `C` invoices; **3,457 non-C rows, all price 0 and no customer** (stock write-offs: damaged/lost/etc.). 1 `C` row has qty ≥ 0 |
| Price | 6,202 rows price 0 (6,131 without customer); 5 negative (all bad-debt adjustments) |
| Customer ID blank | **243,007 rows (22.8%)**, of which 750 are cancellations; values formatted as float (`13085.0`) — cast to integer |
| Customers / products / countries | 5,942 customers · 5,305 StockCodes · 43 countries (UK 981,330 rows; "Unspecified" 756) |
| Customer in >1 country | 13 customers |
| Non-product StockCodes | ~5,927 rows: POST 2,122, DOT 1,446, M/m 1,426 (Manual), C2 282 (carriage), D 177 (Discount), S 104 (samples), BANK CHARGES 102, ADJUST 67, AMAZONFEE 43, CRUK 16, TEST001 15, PADS 19, B 6, gift_0001_* vouchers 89 |
| StockCode case | 3,471 rows contain lower-case (e.g. `gift_0001_20`, `m`); normalise with upper() only for matching rules, keep original |
| Description | 4,382 NULL (all price 0); per StockCode up to 9 distinct descriptions; 1,232 codes have >1 description; 4,370 codes have >1 positive price |
| Invoice with >1 timestamp | 83 invoices (minute rollover while keying) |
| Parse errors | 0 (Quantity int, Price numeric, InvoiceDate `YYYY-MM-DD HH:MM:SS`) |
| Timezone | Not stated; hours 06:10–21:52 consistent with UK local time. Store `timestamp` without zone, document as UK local (GMT/BST), never shift |
| Value check | Σ qty×price (distinct rows): sales invoices £20.47M, cancellations −£1.46M |

## 2. Ingestion contract
- Contract `uci_online_retail_ii` in `ingestion/sources/uci.py`: columns `Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country` (exact, incl. the space). One contract, **two files** → one raw table `raw.uci_online_retail_ii_lines` (text columns quoted as source, e.g. `"Customer ID"`) + `_source_file`, `_ingested_at`, `_batch_id`, `_row_hash`, and **`_source_line_no`** (file row number, needed because there is no natural line key).
- Batch replace keyed by file hash **per file** (delete where `_source_file = <file>` then insert) — extends the current loader with a file-scoped replace mode. Encoding: UTF-8 (check £ in descriptions) — the xlsx is not loaded.

## 3. Dedup & overlap rules (staging `stg_uci__invoice_lines`)
1. **Overlap**: rows dated 2010-12-01..09 exist in both files; keep the later file (2010-2011) for dates ≥ 2010-12-01, the earlier file for dates < 2010-12-01 (rule by date window + source file, not by row match, so it stays correct if a future restatement differs).
2. **Exact duplicates within a file**: DEFAULT drop (keep lowest `_source_line_no`), count them in DQ (warn). Open decision D1 — they may be genuine repeated scans.
3. Line key: `invoice_line_sk = hash(_source_file, _source_line_no)` after the rules above; grain test = one row per (source file, line no).

## 4. Model (schema `uci_*` objects in separate schemas: `uci_staging`, `uci_intermediate`, `uci_core`, `uci_marts`)
Separate schemas keep Power BI navigation clean and make "no cross-source join" structural; model prefix `uci_` avoids name clashes.
- **uci_fct_invoice_lines** — grain: invoice line (deduped). Signed measures: `quantity`, `unit_price`, `line_value = quantity × unit_price` (GBP). Flags: `is_cancellation` (Invoice starts with C), `line_type` ∈ {product, postage, manual, discount, fee, bank_charge, sample, voucher, adjustment, bad_debt, test, stock_writeoff} from a **seed `uci_stockcode_class`** (pattern → type; stock_writeoff = non-C, qty<0, price 0), `has_customer`. FKs: `uci_product_sk`, `uci_customer_sk` (NULL-customer → `-1` unknown member), `uci_country_sk`, `invoice_date_key`.
  Cancellations as **signed lines in the same fact** (not a separate fact): there is no reliable link from a C invoice to its original invoice, so a separate "returns" fact could not carry more information; signed lines make Net = Gross + cancellations additive in DAX.
- **uci_fct_invoices** — grain: invoice (from aggregated lines): line count, units, gross product value, invoice timestamp = min(InvoiceDate) (83 multi-timestamp invoices), customer, country, is_cancellation.
- **uci_dim_product** — BK StockCode (original case). Description varies (≤9 per code): SCD1 attribute = most frequent non-null description (ties → latest); history via `uci_int_product_descriptions` (code × description × first/last seen). Full SCD2 not justified: descriptions change as typo fixes/relabels, not as business events, and there is no effective-date source. Price is a fact attribute, not a dim attribute.
- **uci_dim_customer** — BK Customer ID (int); unknown member for blanks; attributes: first/last invoice date, primary country (most invoices; 13 multi-country customers flagged).
- **uci_dim_country** — distinct Country (43) + ISO code via small seed; "Unspecified" kept as its own member.
- **Date**: reuse `core.dim_date` (generic Gregorian calendar, no Olist attributes in its key/columns except the Olist coverage flags) — justification: calendar semantics are identical (STTM §7). The Olist `is_complete_month` flags do **not** apply to UCI; UCI gets its own `uci_int_month_coverage` (2009-12 → 2011-12; 2011-12 partial). Open decision D2: if Power BI wants no Olist columns visible from the UCI model, create `uci_dim_date` as a thin view over the spine instead.

## 5. Marts (`models/marts/uci/`)
- `uci_mart_sales_daily` (date): invoices, cancellation invoices, gross product sales, cancellations value, net sales proxy, units, active customers (identified only), `sales_invoice_count`, `aov_gbp` = KPI_UCI_AOV = Net Sales (proxy) / sales (non-C) invoices (daily ratio, non-additive: monthly AOV = sum(net_sales_proxy_gbp) / sum(sales_invoice_count)); `gross_product_value_per_product_invoice_gbp` keeps the old gross-per-product-invoice ratio.
- `uci_mart_product_monthly` (month × StockCode): units, gross, cancelled, net, cancellation rate.
- `uci_mart_country_monthly` (month × country).
- `uci_mart_customer_cohorts` (first-purchase month × months since; identified customers only).
- `uci_mart_customer_rfm` (customer snapshot at max date; input for segmentation — P6).

## 6. KPIs (GBP, never summed with Olist BRL)
Supported: GMV/gross sales (product lines, non-C), cancellations value & rate (C lines — "cancellation", NOT confirmed returns), net sales proxy, orders (invoices), AOV, units per invoice, active/new/repeat customers & retention (identified customers only: 77.2% of rows), product/country mix, price variance per product.
Not supported: revenue/profit/margin (no cost, tax, discounts ledger), true return rate (no link C→original), CAC/marketing, inventory/stock levels (write-off lines are not a stock ledger), delivery/fulfilment, customer demographics.

## 7. Tests
Source: header contract; not_null Invoice/StockCode/InvoiceDate. Staging: overlap rule leaves 0 rows of file 1 dated ≥ 2010-12-01; grain unique (source file, line no); accepted_values line_type; `C` ⇒ quantity ≤ 0 (warn, 1 known exception); price ≥ 0 except bad_debt (warn). Core: relationships to all uci dims; unknown customer member present; reconciliation raw (after dedup rules) vs fact counts and Σ line_value; invoices rollup = lines; mart totals = fact totals; currency column constant 'GBP'. DQ: same dq_results hook (layer from `uci_` prefix → extend `_dq_layer`), kpi_ids for UCI KPIs to be added by KPI & Quality.

## 8. Open decisions
- D1 Exact duplicate rows within a file: drop (default, common practice) vs keep as genuine repeated scans.
- D2 Shared `core.dim_date` (justified above) vs separate `uci_dim_date`.
- D3 Net sales proxy: include non-product lines (postage, manual, fees, discounts)? Proposed: GMV = product lines only; postage/fees reported separately; discounts (D) shown as their own line in net.
- D4 Stock write-off rows (3,457, no customer, price 0): keep in fact with line_type=stock_writeoff (value 0) vs exclude.
- D5 Customer country: per invoice (as source) in facts; dim carries primary country only.
- D6 Load the xlsx instead of CSVs? Proposed: CSVs (already exported by Data Research; checksum them in data/README.md).
