# Enterprise360 — Power BI (PBIP: TMDL semantic model + PBIR report)

Olist vertical slice. Real public data only (Olist Brazilian E-Commerce, BRL, 2016-09 to 2018-10). Nothing in this model invents targets, costs or records.
**GMV is not recognized revenue.** No measure, title or visual here is labelled as revenue.

```
powerbi/
├── Enterprise360.pbip                      # open this in Power BI Desktop
├── .gitignore                              # .pbi/localSettings.json, .pbi/cache.abf, …
├── Enterprise360.SemanticModel/
│   ├── definition.pbism                    # version 4.2 (TMDL)
│   └── definition/  database.tmdl · model.tmdl · expressions.tmdl · relationships.tmdl
│                    cultures/en-US.tmdl · roles/State Manager (demo).tmdl · tables/*.tmdl (13 tables)
├── Enterprise360.Report/
│   ├── definition.pbir                     # byPath ../Enterprise360.SemanticModel
│   ├── definition/  version.json · report.json · pages/pages.json · pages/<id>/page.json · pages/<id>/visuals/<id>/visual.json
│   │                bookmarks/bookmarks.json · bookmarks/<id>.bookmark.json
│   └── StaticResources/RegisteredResources/Enterprise360Light.json  # theme (light)
└── tools/
    ├── build_pbip.py                       # deterministic generator (source of truth for this first cut)
    └── validate_pbip.py                    # JSON-schema + cross-reference validator
```

## Opening it in Power BI Desktop
1. Use a Power BI Desktop build from **January 2026 or later**. The files target report 3.1.0, page 2.0.0, visualContainer 2.5.0, bookmark 2.0.0 and definitionProperties 2.0.0. Older builds reject newer schema versions. Newer builds upgrade the files when you save.
2. If your build still marks these as preview, enable **File → Options → Preview features → "Power BI Project (.pbip) save option"**, **"Store semantic model using TMDL format"** and **"Store reports using enhanced metadata format (PBIR)"**, then restart Desktop.
3. Open `Enterprise360.pbip`. It opens with no data (no cache.abf is committed). That is expected.
4. **Transform data → Edit parameters**: `PgServer` = `localhost:5432` (host:port; the PostgreSQL connector accepts `server:port`), `PgDatabase` = `enterprise360`, `PgSchema` = `core`.
5. **Refresh**. When prompted, choose **Database** credentials, user **`e360_app`**, and type the password into the dialog. Desktop stores it in your Windows profile. No password is, or may ever be, written into any project file. Set encryption to match the local Postgres (choose "no encryption" only if your local server has no SSL).
6. Prerequisite: `dbt build` has created the `core` facts and dimensions.
7. Save, then commit the diffs Desktop makes (`.pbi/` is gitignored).

### `DQ Results` before Data Engineering builds `core.dq_results`
The `DQ Results` query wraps the table lookup in `try … otherwise` with an empty table that has the same columns. If `core.dq_results` is missing (for example, dbt has not run on this database yet), refresh therefore **does not fail**. The table loads 0 rows, and the DQ Score, check cards and checks table show blank. Data Engineering's dbt project now defines it (`models/dq/dq_results.sql`), so after `dbt build` the next refresh loads it with no change needed.
If you would rather skip the table entirely, go to **Transform data → right-click `DQ Results` → untick "Include in report refresh"**. Do **not** untick "Enable load", because that deletes the table and breaks the DQ measures.
Note: a Desktop permission or privacy prompt for the database still applies to this table as it does to the others.

## Semantic model
Import mode with a star/constellation schema. Every relationship is many-to-one with single-direction filtering. There are no many-to-many or bidirectional model relationships.

| Table | Source (`PgSchema`, default `core`) | Grain | Notes |
|---|---|---|---|
| Order Item | `fct_order_items` | order line | GMV, freight. Filtered by Product and Seller, and by Order (and through it Customer, Geography, Date, Status) |
| Order | `fct_orders` | order | Order ID (drill field), customer, status, purchase date, approval hours, `latest_review_score`, `payment_vs_items_diff` |
| Payment | `fct_payments` | payment | → Order only. **Never** related to Order Item (fan-out) |
| Delivery | `fct_deliveries` | order | `is_otd_eligible`, `is_on_time` (date comparison, done in dbt), `delivery_days`, DQ flags, `Carrier Handover At` (delivered_carrier_at), `delivered_date_key` (used by TREATAS; no relationship) |
| Customer | `dim_customer` | customer_unique_id | repeat, new and retention logic use the person (customer_sk), not the per-order customer_id |
| Geography | distinct `dim_customer.state` + IBGE UF name/region | state | state level on purpose (zip-prefix geolocation duplicates) |
| Seller / Product | `dim_seller` / `dim_product` | seller_id / product_id | English category with PT fallback (dbt) |
| Order Status | distinct `fct_orders.order_status` | status | adds a display group |
| Date | `dim_date` | day | **marked as date table**. Month sorts by Month No, Year Month sorts by Month Start |
| DQ Run Summary | `dq_run_summary` (dbt view in core; empty fallback if absent) | dbt run | strict `dq_score` (warn earns 0), counts, `is_latest_run`. Filters DQ Results by Run ID. Standalone from the Olist star. Generator switch `USE_DQ_RUN_SUMMARY` |
| DQ Results | `dq_results` (dbt `models/dq`, schema core; empty fallback if absent) | run_id × check_id | **standalone**: no relationships, so Date, Geography and other slicers do not affect it |
| _Measures | — | — | all explicit measures, in display folders |
| Time Intelligence | calculation group | — | Current, MTD, QTD, YTD, PY, YoY, YoY %, Rolling 12M. YoY % has its own format string. Any visual that uses YoY on GMV must carry the partial caveat |

`discourageImplicitMeasures` is on. Keys are hidden with summarizeBy none.

**Product and Seller filters (approved design choice, KPI & Quality).** Product and Seller filter only Order Item. Order-grain measures (`[Orders]`, `[Active Customers]`, `[Avg Approval Hours]`, `[On-Time Delivery %]`, `[Late Orders]`, `[Avg Delivery Days]`, `[Avg Review Score]`, `[Low Review %]`, and `[Cancellation Rate %]` through `[Orders]`) follow those filters **only when Product or Seller is actually filtered**. They test `ISCROSSFILTERED('Product') || ISCROSSFILTERED('Seller')`. When that is true, the measure runs with `CROSSFILTER('Order Item'[order_id], 'Order'[Order ID], BOTH)` and counts the *orders containing* the filtered lines. Otherwise it runs unchanged, so orders without items (some canceled or unavailable) stay in the company figure. The model's relationships remain single-direction. Visuals showing these breakdowns carry an "orders containing …" subtitle and have totals off.

**Role-playing date (delivery date), RLS-safe.** `[On-Time Delivery % (by Delivery Date)]` = `CALCULATE([On-Time Delivery %], REMOVEFILTERS('Date'), TREATAS(VALUES('Date'[date_key]), 'Delivery'[delivered_date_key]))`. Here is how it propagates:
- CALCULATE evaluates `VALUES('Date'[date_key])` in the outer context, so it holds the selected dates, after any Time Intelligence item.
- `REMOVEFILTERS('Date')` then drops the purchase-date path (Date → Order → Delivery).
- TREATAS applies the same keys directly to `Delivery[delivered_date_key]`.
- Customer, Geography, Order Status and the RLS role still filter Order, and Order → Delivery is an active one-way relationship, so all of them still reach Delivery.
- `[On-Time Delivery %]` refers only to Delivery columns (`is_otd_eligible`, `is_on_time`) and has no Date reference, so the purchase date is not reintroduced. Its Product/Seller branch turns on Order Item ↔ Order BOTH, which only widens filtering from the item side and doesn't touch Date.
- The earlier inactive Date → Delivery relationship was **removed**, because nothing used it any more. The model has no ambiguous paths: 9 active one-way relationships form a tree. `tools/validate_pbip.py` now fails on any measure, calc item or calculated column that uses `CROSSFILTER(..., NONE)` or `ALL`/`ALLEXCEPT`/`ALLSELECTED`/`REMOVEFILTERS` on Geography, Customer or Order. I confirmed with a test model that the check catches both patterns.

**DQ Score %** comes from `core.dq_run_summary.dq_score`. It uses the run flagged `is_latest_run = TRUE`, unless a run is selected (run slicer or the Run At axis on `DQ Run Summary`); if several runs are selected, it uses the latest of them. Checked on 2026-10-30 against the local warehouse: the latest run (23:08 IST) gives a view `dq_score` of 0.9980, and the old weighted calculation over `dq_results` gives 0.99802. Both show 99.8%. The view rounds to 4 decimal places. The run slicer and score trend use `DQ Run Summary`, and its Run ID filters the check-level `DQ Results` table.
**Check-level DQ "latest run" logic.** Every DQ measure filters to the latest `run_at`, unless `Run ID` or `Run At` is already in the filter context (slicer, axis, or table row). In that case it uses the run in context. This means the DQ Score trend by Run At shows one score per run.

**GMV Growth % and complete months.** The Date table loads `dim_date.is_complete_month` as a hidden column (TRUE = the whole calendar month lies inside Olist coverage; complete means not partial). `[GMV Growth %]` returns BLANK when prior-month GMV is blank or 0, **or** when the current or prior month has any day with `is_complete_month = FALSE`. It is meant to be read at Year Month level. To drop the check, set `DATE_COMPLETE_FLAG_COLUMN = None` in the generator.

## Measures (names from docs/kpi-catalog.md; each TMDL description and `KPI_Id` annotation carry the id)
| KPI id | Measure | Folder | Status | Catalog |
|---|---|---|---|---|
| `KPI_GMV` | `[GMV]` | Sales | SUPPORTED | catalog |
| `KPI_GMV_INCL_FREIGHT` | `[GMV incl Freight]` | Sales | SUPPORTED | catalog |
| `KPI_NET_GMV` | `[Net GMV]` | Sales | SUPPORTED | catalog |
| `KPI_FREIGHT` | `[Freight Value]` | Sales | SUPPORTED | catalog |
| `KPI_FREIGHT_SHARE` | `[Freight Share %]` | Sales | SUPPORTED | catalog |
| `KPI_GMV_GROWTH` | `[GMV Growth %]` | Sales | PARTIAL | catalog |
| `KPI_PAYMENT_VALUE` | `[Payment Value]` | Payments | SUPPORTED | catalog |
| `KPI_PAYMENT_VALUE` | `[Payment Mix %]` | Payments | SUPPORTED | supporting (approved) |
| `KPI_ORDERS` | `[Orders]` | Orders | SUPPORTED | catalog |
| `KPI_ITEMS_PER_ORDER` | `[Items Sold]` | Orders | SUPPORTED | supporting (approved) |
| `KPI_AOV` | `[AOV]` | Orders | SUPPORTED | catalog |
| `KPI_ITEMS_PER_ORDER` | `[Items per Order]` | Orders | SUPPORTED | catalog |
| `KPI_CANCEL_RATE` | `[Cancellation Rate %]` | Orders | SUPPORTED | catalog |
| `KPI_APPROVAL_HOURS` | `[Avg Approval Hours]` | Orders | SUPPORTED | catalog |
| `KPI_ACTIVE_CUSTOMERS` | `[Active Customers]` | Customers | SUPPORTED | catalog |
| `KPI_NEW_CUSTOMERS` | `[New Customers]` | Customers | SUPPORTED | catalog |
| `KPI_REPEAT_RATE` | `[Repeat Purchase Rate %]` | Customers | SUPPORTED | catalog |
| `KPI_CUSTOMER_RETENTION` | `[Customer Retention %]` | Customers | PARTIAL | catalog |
| `KPI_CUSTOMER_RETENTION` | `[Retention Cohort Size]` | Customers | PARTIAL | supporting (approved) |
| `KPI_OTD_RATE` | `[On-Time Delivery %]` | Delivery | SUPPORTED | catalog |
| `KPI_OTD_RATE` | `[On-Time Delivery % (by Delivery Date)]` | Delivery | SUPPORTED | supporting (approved) |
| `KPI_OTD_RATE` | `[Late Orders]` | Delivery | SUPPORTED | supporting (approved) |
| `KPI_SELLER_HANDOVER_OTD` | `[Seller Handover On-Time %]` | Delivery | PARTIAL | catalog (approved) |
| `KPI_SELLER_HANDOVER_OTD` | `[Handover Missing Timestamp]` | Data Quality | PARTIAL | supporting — DQ exclusion count, not an operational KPI |
| `KPI_DELIVERY_DAYS` | `[Avg Delivery Days]` | Delivery | SUPPORTED | catalog |
| `KPI_REVIEW_SCORE` | `[Avg Review Score]` | Reviews | SUPPORTED | catalog |
| `KPI_LOW_REVIEW_RATE` | `[Low Review %]` | Reviews | SUPPORTED | catalog |
| `KPI_DQ_SCORE` | `[DQ Score %]` | Data Quality | SUPPORTED | catalog |
| `KPI_RECON_VARIANCE` | `[Reconciliation Variance]` | Data Quality | SUPPORTED | catalog |
| `KPI_DQ_SCORE` | `[Checks Failed]` | Data Quality | SUPPORTED | supporting (approved) |
| `KPI_DQ_SCORE` | `[Checks Warned]` | Data Quality | SUPPORTED | supporting (approved) |
| `KPI_DQ_SCORE` | `[Blocking Failures]` | Data Quality | SUPPORTED | supporting (approved) |
| `KPI_DQ_SCORE` | `[Failing Rows]` | Data Quality | SUPPORTED | supporting (approved) |
| `KPI_PAYMENT_VALUE` | `[Payment Mismatch Orders]` | Data Quality | SUPPORTED | supporting (approved) | Baseline 1,076 orders (verified against core).
| `KPI_PAYMENT_VALUE` | `[Payment Without Items Orders]` | Data Quality | SUPPORTED | supporting — data-quality exclusion count (approved) |
| `KPI_PAYMENT_VALUE` | `[Overpaid Orders]` | Data Quality | SUPPORTED | supporting — data-quality exclusion count (approved) |
| `KPI_PAYMENT_VALUE` | `[Underpaid Orders]` | Data Quality | SUPPORTED | supporting — data-quality exclusion count (approved) |
| `KPI_PAYMENT_VALUE` | `[Items Without Payment Orders]` | Data Quality | SUPPORTED | supporting — data-quality exclusion count (approved) |
| `KPI_OTD_RATE` | `[Delivered Missing Timestamp]` | Data Quality | SUPPORTED | supporting (approved) — DQ exclusion count, not an operational KPI |
| `KPI_DELIVERY_DAYS` | `[Delivered Before Purchase]` | Data Quality | SUPPORTED | supporting (approved) — DQ exclusion count, not an operational KPI |
| `KPI_OTD_RATE` | `[OTD Eligible Orders]` | Data Quality | SUPPORTED | supporting (approved) |
| `KPI_PAYMENT_VALUE` | `[Payment Records]` | Data Quality | SUPPORTED | supporting (approved) |

**Formatting helper (not a KPI, hidden):** `[DQ Status Colour]` returns a hex colour per check status, used only for conditional formatting of the Data Quality checks table.

Locked KPI & Quality definitions, as implemented:
- **GMV Growth %**: month over month on calendar months by purchase date.
- **Customer Retention %**: customers active in the previous calendar month who order again in the current month. It is always shown next to `[Retention Cohort Size]`, on the same card row and in the same table.
- **Repeat Purchase Rate %**: 2+ distinct orders within the selected period. Visual titles say "within selected period".
- **Delivery KPIs, including Avg Delivery Days**: only `is_otd_eligible = true`.

## Report pages (1280×720, light theme; page navigator on every page lists all visible pages)
| Page | Content |
|---|---|
| Executive Command Center | purchase-date slicer; 5 cards (GMV, Orders, AOV, Avg Review Score, OTD %); **bookmark buttons "Executive view" / "Detail view"**. Executive view shows the GMV vs Net GMV trend, GMV by state, top categories, and GMV Growth % (partial caveat). Detail view shows a monthly scorecard table |
| Sales Performance | cards (including Repeat Purchase Rate % "within selected period", with caveat); GMV trend; by category; by state; payment mix donut ("payment value, not sales"); top sellers table (drill source to Seller Detail) |
| Customer Intelligence | Active, New, Repeat % and Retention % cards, with Retention Cohort Size next to Retention % (both partial); active vs new by month (new = first-order cohort size); by region; by state; monthly retention table with cohort size |
| Product Performance | GMV by category; category scorecard (GMV, Items Sold, AOV, Items per Order, Avg Review Score, Freight Share %); top products |
| Operations & Delivery | OTD %, Avg Delivery Days, Late Orders, Cancellation Rate %, Avg Approval Hours; Seller Handover On-Time % card (partial caveat); OTD by **delivery** month; OTD by customer state; OTD and seller handover on-time % by seller state (partial caveat); orders-by-status funnel; late orders table (drill source to Order Detail) |
| Data Quality | run slicer (default latest); DQ Score %, Blocking Failures, Checks Failed, Checks Warned, Failing Rows; checks table (check, layer, model, KPI id, severity, status coloured pass/warn/fail through `[DQ Status Colour]`, failing rows, variance); reconciliation variance by KPI id; DQ Score % by run; warehouse checks from the fct tables (payment-vs-items mismatches, delivered without timestamp, delivered before purchase, OTD-eligible orders, row counts) |
| Order Detail *(drill-through on Order[Order ID], hidden)* | back button; order header (status, purchase, approval, estimated/actual delivery, latest review); order lines; payments |
| Seller Detail *(drill-through on Seller[Seller ID], hidden)* | back button; GMV, Orders, AOV, OTD % and review cards; GMV trend; top categories; seller's orders (drill on to Order Detail) |
| Tooltip - Category / Tooltip - State *(tooltip pages, 320×240, hidden)* | GMV, AOV, Avg review, On-time %. Assigned to every category and state visual |

**Order-level KPIs broken down by product, category or seller** (Orders, AOV, OTD %, Avg Delivery Days, Avg Review Score, Avg Approval Hours) count *orders containing* the selected product, category or seller. An order with items from two categories counts in both. Every such visual carries a subtitle or title saying so: the category scorecard, top products, top sellers, OTD by seller state, the Seller Detail cards and the category tooltip. Review score columns are titled exactly "Avg Review Score of orders containing category", "… product" or "… seller", because Olist reviews rate an order, not a product. Totals are **off** on the category, product and seller tables (and the Seller Detail orders table), so no row of categories appears to add up to the company figure.

**Drill-through** sources: Sales Performance top sellers and the Seller Detail orders table, plus the Operations late-orders table and the Seller Detail orders table. To use it, right-click a row and choose Drill through.

**Bookmarks** (`definition/bookmarks/`) target only the 5 swappable visuals (`applyOnlyToTargetVisuals`). They use `suppressData` so slicer selections survive. The Detail-view table starts hidden. I kept these simple: the only change they make is visibility of individual visuals (no visual groups, no captured filter state). If Desktop rewrites them on save, commit the result.

## RLS — "State Manager (demo)" — DEMO ONLY
`roles/State Manager (demo).tmdl` applies the static filter `Geography[State] = "SP"` and `DQ Results = FALSE()` and `DQ Run Summary = FALSE()`, which hide DQ from this role.
- **What the filter reaches:** Geography → Customer → Order → Order Item, Payment and Delivery. That covers every Olist fact. All relationships run 1→many in the filtering direction, so no bidirectional filtering is needed.
- **What it does not reach:** Product, Seller, Date and Order Status dimension rows still list every member, though measures are filtered. `DQ Results` is blocked for this role. Every Olist fact is filtered, including `[On-Time Delivery % (by Delivery Date)]` (now TREATAS-based, see the semantic model notes). The validator guards against measures that would cut the path.
- **Testing:** RLS is enforced only in the Power BI Service, for users with the Viewer role on the workspace (Admin, Member and Contributor bypass it). In Desktop, test it with **Modeling → View as → State Manager (demo)**.
- **Production design:** a user-to-state mapping table plus `USERPRINCIPALNAME()`, and role membership set in the Service. This demo role is not a security control.

## NOT SUPPORTED (no measures or visuals built; Olist lacks the data)
Net/recognized revenue, Gross Profit / Gross Margin, Operating Profit / Margin, P&L, Cost per Order (no COGS, opex or GL) · Target Achievement, Budget vs Actual (no real targets; none fabricated) · CAC, ROAS, CTR, Marketing ROI (no spend) · Return Rate / Refunds (no returns table) · Inventory Turnover, Stockout, Fill Rate (no inventory) · Supplier/procurement KPIs (sellers are merchants, not suppliers) · HR KPIs · Cash flow / AR / AP (payments are transaction values) · Complaint resolution time · margin-based CLV · (contractual seller SLAs: Olist has only its own shipping deadline, covered by `[Seller Handover On-Time %]`).
Lead conversion (Olist Marketing Funnel) is a separate dataset and is not joined to orders.

## Payment vs items+freight exceptions (verified)
`[Payment Mismatch Orders]` = `CALCULATE(COUNTROWS('Order'), KEEPFILTERS(ABS('Order'[payment_vs_items_diff]) > 0.01))`.
- **How the column is built:** dbt computes `fct_orders.payment_vs_items_diff` as `(coalesce(p.payment_value_total, 0) - coalesce(i.items_gross_total, 0))::numeric(14,2)`. A missing side counts as 0, so the result is never NULL.
- **Grain:** `fct_orders` is built from `stg_olist__orders` (all 99,441 orders) with items and payments left-joined. Orders with payments but no items are therefore rows in the Order table.
- **Verified 2026-10-30** on the local warehouse (core) and on the raw CSVs, using exact decimals: **1,076** orders, made up of 772 payments-without-items, 264 overpaid, 39 underpaid and 1 items-without-payment.
- **Breakdown measures:** they use the hidden `has_items` and `has_payment` columns and the sign of the diff. All four are shown on the Data Quality page.
- **Breakdown subtitle:** the exceptions card notes that payment-without-items orders do not appear under product or seller filters, so the four breakdowns will not sum to the mismatch total when filtered.
- **Note:** these measures follow the Date slicer by purchase date. Orders with no items do not appear under Product or Seller filters.

## Data Engineering status
- **`core.dq_results`** now exists in dbt (`models/dq/dq_results.sql`, a view in `core` over `dq.dq_results_log`). Its 14 spec columns match what the model selects, and the extra columns (`test_type`, `dbt_status`, `execution_seconds`, `is_latest_run`) are not loaded. The `try … otherwise` fallback is kept, so a refresh still succeeds on a database where dbt has not run yet. The model has not yet been refreshed against real rows.
- **`dim_date.is_complete_month`**: now in dbt and wired in (see GMV Growth %).
- **Seller handover (KPI_SELLER_HANDOVER_OTD, PARTIAL).** `[Seller Handover On-Time %]` = items handed to the carrier (`fct_deliveries.delivered_carrier_at`) at or before the item's `shipping_limit_at` / items with both timestamps. It is a **full timestamp** comparison, now computed in dbt as `core.fct_order_items.is_handover_on_time`. The model loads that source column, and the earlier calculated column was dropped. `shipping_limit_at` is **Olist's seller shipping deadline, not a contractual SLA**. Partial: carrier handover is recorded per order, so sellers in multi-seller orders share one handover time. This caveat appears on every visual that shows the measure: the Operations & Delivery card and the seller-state chart. `[Handover Missing Timestamp]` (DQ exclusion count) is shown on the Data Quality page. Target and benchmark: to be set by owner.
- dbt surrogate keys are md5 text; `date_key` is an integer yyyymmdd.

## Forecast & Anomalies (exploratory; kpis.yaml @ ef85a62 KPI_GMV_FORECAST, KPI_GMV_ANOMALY_FLAG, both PARTIAL)

**Sources** (via `PgSchemaMarts`; DE has not committed the SQL yet, so the column names are **provisional**). All three tables are standalone: they have their own month axis and no Date relationship.

| Table | Mart | Notes |
|---|---|---|
| GMV Forecast | marts.mart_gmv_forecast | |
| GMV Forecast Backtest | marts.mart_gmv_forecast_backtest | GMV series only |
| GMV Anomalies | marts.mart_gmv_anomalies | |

The column-to-source mapping lives in one place, `FC_SRC` in `tools/build_pbip.py`, so a rename is a one-line change. All money columns are decimal with Currency.Type.

**Why standalone:** the marts do carry `month_date_key`, and `dim_date` runs to 2019-12-31, but relating them to Date would put them under the Olist reporting-month trend filter and the purchase-date slicer. Kept standalone, 2018-09..2019-02 is never hidden.

**RLS:** the "State Manager (demo)" role hides all three tables (`FALSE()`), because these are company-wide figures with no state grain.

**Validator:** a new `forecast-rules` check fails if:
- any measure uses `forecast_gmv` without an `is_forecast` or validation+test filter (train rows are the in-sample fit);
- anything references or loads `is_anomaly`.

**Measures** (folder `Forecast & Anomalies`):
- **KPI_GMV_FORECAST**, parent annotation on all:
  - `[GMV Forecast]` (is_forecast rows)
  - `[GMV Forecast Lower]`, `[GMV Forecast Upper]` (formatting; kpis.yaml names a single `[GMV Forecast Lower/Upper]`, split into two because DAX needs one value each)
  - `[GMV Baseline (Naive)]`
  - `[GMV Forecast Actual]`
  - `[GMV Backtest Forecast]` (validation and test rows only)
  - `[Backtest MAE]`, `[Backtest sMAPE %]`, `[Backtest Months]`
- **KPI_GMV_ANOMALY_FLAG**:
  - `[GMV Anomaly Months]` (is_gmv_anomaly only)
  - `[GMV Robust Z]`
  - `[GMV Anomaly Z Threshold]`
  - `[Orders Robust Z]` (a separate, labelled orders series)

Only `[GMV Forecast]`, `[GMV Forecast Lower/Upper]`, `[GMV Baseline (Naive)]`, `[GMV Anomaly Months]` and `[GMV Robust Z]` are named in kpis.yaml. **The others need a KPI & Quality listing.**

**Verified by SQL (run 7476f047):**
- **Backtest, GMV, 3 months per split:**

| Split | holt_damped (model) | naive_last_value (baseline) |
|---|---|---|
| Validation | MAE 60,295 / sMAPE 5.80% | MAE 147,948 / sMAPE 16.11% |
| Test | MAE 287,398 / sMAPE 28.25% | MAE 124,745 / sMAPE 13.37% |

  The model does not beat the baseline on test.
- **Test actuals below the interval:** all three Jun–Aug 2018 actuals are below the 95% lower bounds — 865,124 < 932,111; 895,507 < 977,905; 854,686 < 1,021,685.
- **Anomalies:** GMV anomaly months = 0. Nov 2017 GMV z = 2.84 (not flagged); its orders z is 5.60 (orders flag only).
- **Forecast:** 2018-09..2019-02 = 939,062 … 1,033,841.

**Page:**
- Label strip: Exploratory | GMV = item price, not revenue | Statistical flags, not confirmed incidents | Monthly grain; day-level events like Black Friday are not detectable.
- Forecast line chart:
  - actuals;
  - backtest forecast (validation and test only; never train);
  - forward forecast;
  - lower and upper bounds labelled "95% model-based interval, not a guarantee";
  - "Naive baseline (last value)".
- "Backtest, 3 months per split" matrix (model vs baseline: MAE, sMAPE, n months, totals off), with the notes "Model does not beat the naive baseline on the test period" and "test actuals fell below the interval".
- Robust-z chart against the 3.5 threshold, with the orders series labelled separately.
- `[GMV Anomaly Months]` card. There is no accuracy headline card and no targets.

**Rulings applied (KPI & Quality on f8d4f4c):**
- **Approved:** the split `[GMV Forecast Lower]` / `[GMV Forecast Upper]` drawn as separate lines; the marts staying unlinked from Date; the three column differences; and the seven extra measures.
- **Supporting kinds:**
  - **formatting:** Lower/Upper, Backtest sMAPE %, Z Threshold, Robust Z, plus the dynamic texts
  - **breakdown:** Baseline, Forecast Actual, Backtest Forecast, Backtest MAE, Backtest Months, Anomaly Months, and `[Orders Robust Z]` (labelled "orders flag, not GMV")
- **Parent annotation:** every forecast measure is annotated `KPI_ParentKpi = KPI_GMV_FORECAST`, and every anomaly measure `KPI_GMV_ANOMALY_FLAG`.

**Page behaviour:**
- **Legend:** "95% interval (lower)" / "95% interval (upper)", and the subtitle says "95% interval (lower/upper): model-based, not a guarantee".
- **Slicers:** every forecast, backtest and anomaly visual says "All dates: date slicers don't apply (standalone monthly mart)". The page has no date slicer today. Any slicer added later is set to NoFilter on every visual on the page by the generator.
- **Dynamic notes:** `[Backtest Test Verdict]` compares the selected model's test sMAPE with the baseline's. `[Test Interval Note]` counts the test months outside lower_gmv/upper_gmv and is BLANK when that count is 0. Both are shown as cards. Current text:
  - "Model does not beat the naive baseline on the test period (test sMAPE 28.25% vs 13.37%)"
  - "3 of 3 test actuals fell outside the 95% interval (3 below lower, 0 above upper): intervals are not calibrated"

**Coming DE changes:**
- **New columns:** `interval_method` and `selected_model` do **not** exist yet (checked 2026-10-31). They are mapped in `FC_OPTIONAL_SRC`. Set `FC_SHOW_METHOD = True` in `tools/build_pbip.py` to load them and show the "Interval method / selected model" caption. Both modes were generated and validated.
- **Never loaded:** `fitted_gmv` and the combined flag under either name, `is_anomaly` or `is_any_anomaly`. The generator asserts this, and the validator `forecast-rules` check fails on either flag name or on `fitted_gmv`.

**DE rebuild (marts in db 2026-10-31; dbt models committed in 9972c3e):**
- **Backtest load:** the mart now has a `cv` split (39 points) and an `ses` model row. The backtest query keeps only `series = 'gmv'`, `split IN (validation, test)`, and `model IN (selected_model, baseline_model)`. The two model names are read from `mart_gmv_forecast` in M, not hardcoded; today they are holt_damped and naive_last_value.
- **Backtest measures:** `[Backtest MAE]`, `[Backtest sMAPE %]` and `[Backtest Months]` are BLANK unless exactly one split and one model are in context. Matrix subtotals are off.
- **Caption:** `selected_model`, `selection_reason` and `interval_method` exist, so `FC_SHOW_METHOD = True`. A caption shows Selected model / Selection reason / Interval method, read from forward-forecast rows: holt_damped / "holt_damped CV sMAPE 16.80% < baseline 21.21%" / conformal_abs_cv.
- **Slicer subtitle:** the forecast, backtest, anomaly-z and anomaly-months visuals say "Date and reporting-month slicers do not apply (forecast months extend past the reporting window)", and any slicer on the page is set to NoFilter on them.
- **Not loaded:** train rows now carry `fitted_gmv` (with `forecast_gmv` NULL), and `is_anomaly` was renamed `is_any_anomaly`. Neither is loaded, and the validator and generator ban `fitted_gmv`, `is_anomaly` and `is_any_anomaly`.
- **Current page values:**
  - Test sMAPE: model 28.25% vs baseline 13.37%. The verdict note reads "Model does not beat the naive baseline on the test period (test sMAPE 28.25% vs 13.37%)".
  - The conformal intervals now contain all three test actuals (Jun–Aug 2018 lower bounds 792,667 / 755,410 / 770,407), so `[Test Months Outside Interval]` = 0 and the interval note is **blank**. The earlier "fell below the interval" statement applied to the old ETS intervals only.
  - Anomalies: 0 GMV anomaly months. Nov 2017 GMV z is 2.84; its orders z is now 4.76.
  - Forecast 2018-09..2019-02: 939,062 … 1,033,841.

**Deal window (f1a3af8):** `[Deal Window Complete]` (formatting, parent KPI_FUNNEL_CONVERSION_RATE) is 1/0 per cohort month and BLANK unless exactly one Date[Year Month] is in context.
- **Rule:** it uses the same rule as `mart_funnel_monthly.is_deal_window_complete` (first-contact month >= first won month, 2017-12), derived from lead and deal rows. A SQL check against the mart matched for all 12 cohorts: 2017-06..2017-11 = incomplete, 2017-12..2018-05 = complete.
- **Cohort chart colours:**

| Colour | Meaning |
|---|---|
| Grey #6B7280 | incomplete deal window |
| Amber #B45309 | immature |
| Teal #0E7490 | complete and mature |

- **Tooltip and subtitle:** the tooltip shows both flags, and the subtitle explains all three colours.

**Backtest baseline:** the M load reads `selected_model` and `baseline_model` from `mart_gmv_forecast`. It keeps the baseline rows plus the selected model's rows, and adds `Model Role` (selected / baseline / selected baseline).
- `[Backtest Test sMAPE (Baseline)]` is keyed on the baseline's name (naive_last_value) through Model Role, not on "not selected".
- If the baseline itself is selected, the verdict reads "Baseline (naive_last_value) was selected; no separate model to compare on the test period (test sMAPE x%)".

**Column notes vs the spec:**
- `mart_gmv_forecast_backtest` has an extra `series` column (gmv/orders); it is filtered to gmv in M.
- `smape_pct` is stored in percent units (28.2545), so it is divided by 100.
- `mart_gmv_forecast` also has `is_anomaly`, `is_orders_anomaly`, orders columns, `interval_level` (0.95), `training_cutoff`, `horizon` and `run_id`. These are not loaded.
- The anomalies month column is `anomaly_date` (month start).

## Marketing Funnel (Olist funnel dataset; kpis.yaml v2.1.0 KPI_FUNNEL_*)

**Sources:**
- `core.fct_leads` → table **Lead**
- `core.fct_closed_deals` → table **Closed Deal**. `declared_monthly_revenue_brl` is deliberately *not* loaded: it is self-reported and is not revenue.
- `core.dim_lead_origin` → table **Lead Origin**
- `marts.mart_funnel_time_to_close` → table **Funnel Time to Close**, read through the new parameter **`PgSchemaMarts`** (default `marts`)

`marts.mart_funnel_monthly` now exposes `mqls`, `converted_leads_in_cohort` and `is_cohort_mature`, but it is deliberately **not** loaded. Cohort figures are computed from the lead rows (`core.fct_leads`) by choice, so that they recalculate correctly under any origin or date filter and stay ratio-of-sums at every grain. The mart is pre-aggregated by month × origin.

**Relationships.** Five were added, all one-way many-to-one and all active, with no ambiguous paths because the two facts are not related to each other:
- Lead[first_contact_date_key] → Date
- Closed Deal[won_date_key] → Date
- Lead[origin_sk] → Lead Origin
- Closed Deal[origin_sk] → Lead Origin
- Funnel Time to Close[origin_sk] → Lead Origin

There is no Seller link, so funnel figures are never blended with order KPIs. The "State Manager (demo)" role does not filter funnel tables, because they have no state.

**Measures** (display folder `Marketing Funnel`) and values verified in the warehouse on 2026-10-31:

| Measure | KPI id | Status | Verified |
|---|---|---|---|
| MQLs | KPI_FUNNEL_MQLS | SUPPORTED | 8,000 |
| MQLs by Origin (breakdown) | KPI_FUNNEL_MQLS | SUPPORTED | not_recorded (null origin) 60, unknown 1,099, kept separate |
| Closed Deals | KPI_FUNNEL_CLOSED_DEALS | SUPPORTED | 842 |
| Closed Deals by Business Segment, Closed Deals by Lead Type (breakdowns) | KPI_FUNNEL_CLOSED_DEALS | SUPPORTED | 33 segments, 1 null segment, 6 null lead type |
| Unmatched Closed Deals (dq_exclusion) | KPI_FUNNEL_CLOSED_DEALS | SUPPORTED | 0 |
| Converted Leads in Cohort (breakdown) | KPI_FUNNEL_CONVERSION_RATE | PARTIAL | 842 |
| Lead-to-Deal Conversion % | KPI_FUNNEL_CONVERSION_RATE | PARTIAL | 10.53% (842 / 8,000) |
| Cohort Is Mature (formatting; 1/0, per cohort month only; BLANK at total) | KPI_FUNNEL_CONVERSION_RATE | PARTIAL | Apr and May 2018 immature (cohort month end + 210 days > 2018-11-14) |
| Cohort Maturity Colour (hidden formatting helper) | KPI_FUNNEL_CONVERSION_RATE | PARTIAL | #B45309 immature, #0E7490 mature |
| Median Days to Close | KPI_FUNNEL_MEDIAN_DAYS_TO_CLOSE | SUPPORTED | 14 (841 valid deals) |
| Negative Duration Deals (dq_exclusion) | KPI_FUNNEL_MEDIAN_DAYS_TO_CLOSE | SUPPORTED | 1 |
| Closed Deals by Days-to-Close Bucket (breakdown; approved by KPI & Quality) | KPI_FUNNEL_MEDIAN_DAYS_TO_CLOSE | SUPPORTED | 841 (mart total 842 minus the 1 negative-duration deal, excluded in M with bucket_min_days >= 0). All dates: the mart has no date grain; the Date slicer interaction is set to NoFilter |

**How the measures work:**
- **Conversion** is cohorted by first-contact month: `DIVIDE([Converted Leads in Cohort], [MQLs])`. It is never deals-in-month divided by MQLs-in-month, and never an average of monthly rates.
- **Median** is `MEDIANX` over deal rows with a non-negative duration. It never averages the mart's `median_days_to_close`.
- **Naming:** kpis.yaml `power_bi_dax` proposes `[Lead Conversion %]`. The measure uses the KPI & Quality name `[Lead-to-Deal Conversion %]`.

**Monthly cohort values** (first-contact month):

| Cohort | Conversion |
|---|---|
| 2017-06 | 0% |
| 2017-07 | 0.84% |
| 2017-08 | 2.33% |
| 2017-09 | 2.24% |
| 2017-10 | 3.37% |
| 2017-11 | 4.04% |
| 2017-12 | 5.50% |
| 2018-01 | 13.32% |
| 2018-02 | 14.49% |
| 2018-03 | 14.22% |
| 2018-04 | 13.54% (immature) |
| 2018-05 | 9.98% (immature) |

**Page "Marketing Funnel"** (after Data Quality in the navigator):
- Date and origin slicers, and a scope note.
- KPI cards.
- MQLs and closed deals trend. Its subtitle explains the two time axes and the partial June 2017.
- Cohort conversion column chart. Bars are coloured by maturity (amber #B45309 = immature), with the caveat that wins only start in Dec 2017, so 2017 cohorts look low.
- Origin table, plus closed deals by business segment and by lead type.
- Time-to-close distribution, from the mart (All dates; date slicers do not apply; buckets total 841).

No targets are shown (they are to be set by the owner). The Olist reporting-month trend filter is **not** applied here: the funnel spans 2017-06 to 2018-11, and deals in Sep–Nov 2018 would be dropped.

**NOT SUPPORTED (funnel):**
- CAC, ROAS and cost per lead: there is no marketing spend data.
- Revenue from deals: `declared_monthly_revenue_brl` is self-reported and is not revenue.
- Seller-level funnel-to-GMV attribution: only 380 of 842 deal sellers appear in orders, and the data is not blended.

**Adding a page.** Build a `Page`, call `header()`/`cards()`, then `PAGES.append(...)`. The page navigator on every page lists all non-hidden pages in `PAGES` order. The Forecast & Anomalies page follows Marketing Funnel.

## Design system (light theme, `Enterprise360Light.json`)

Every page, including the drill-through and tooltip pages, has a white page and wallpaper (#FFFFFF, transparency 0). Visuals are white cards with a 1px #E5E7EB border, radius 4, and no shadow. Gridlines are #E5E7EB, and table and matrix headers are #F3F4F6.

Contrast ratios on white (WCAG AA body text needs 4.5:1 or more):

| Use | Colour | Ratio |
|---|---|---|
| Primary text (titles, values, table text, slicer items) | #1F2937 | 14.68:1 |
| Secondary text (axes, legends, category labels) | #4B5563 | 7.56:1 |
| Muted text | #6B7280 | 4.83:1 |
| Card callouts, accent text (cyan-700) | #0E7490 | 5.36:1 |
| Accent lines and links (blue-600) | #2563EB | 5.17:1 |
| PARTIAL caveat subtitles (amber-700) | #B45309 | 5.02:1 |
| Good | #047857 | 5.48:1 |
| Bad | #B91C1C | 6.47:1 |
| Selected navigator/button state (white on #0E7490) | #FFFFFF | 5.36:1 |
| Dark text on DQ status tints (pass #D1FAE5 / warn #FEF3C7 / fail #FEE2E2) | #1F2937 | 12.9 / 13.2 / 12.0:1 |

Button and navigator states: default is light grey #F3F4F6 or white with dark text; hover is #E5E7EB; selected is #0E7490 with white text.

The old cyan #22D3EE (1.81:1 on white) is no longer used. The data palette keeps the same hues, made darker: #0891B2, #2563EB, #6366F1, #0D9488, #3B82F6, #8B5CF6, #64748B, #D97706.

## "Pending changes in your queries" banner (fixed in the generator)

Desktop rebuilds its Power Query document from the TMDL and compares it with the model. Three differences found in the generated model could trigger the banner:

1. `PBI_QueryOrder` listed only the 5 parameters, not the 22 table queries. Desktop always lists every query (parameters, then every table with an M partition).
2. Six PostgreSQL `numeric` money columns were declared `dataType: decimal` (Fixed Decimal) while their M returned untyped `type number`, so the M output schema differed from the model columns. They stay **decimal (Fixed Decimal, 4 dp)**, and each table's M now has an explicit `Money = Table.TransformColumnTypes(..., {{col, Currency.Type}})` step, the pattern Desktop writes. Decimal is kept, not double, so exact comparisons such as `ABS(payment_vs_items_diff) > 0.01` are free of float error. The warehouse maximum scale fits within 4 dp: 2 dp for item_price, freight_value, payment_value and payment_vs_items_diff, and 3 dp for line_value and monetary_net_sales_proxy_gbp. Values at 4 dp reproduce the verified results exactly: 1,076 mismatch orders, GMV R$13,591,643.70 and UCI Net Sales (proxy) £18,914,519.437. The six columns are:
   - Order Item: item_price, freight_value
   - Order: payment_vs_items_diff
   - Payment: payment_value
   - UCI Invoice Line: line_value
   - UCI RFM: monetary_net_sales_proxy_gbp
3. Navigation tables were missing `annotation PBI_NavigationStepName = Navigation`.

These now carry the Currency.Type step, the full query order and the annotations are written, and `validate_pbip.py` runs a `query-consistency` check. The check fails on:
- a missing or unknown query in PBI_QueryOrder;
- a `decimal` column whose M does not type it `Currency.Type`, or a `Currency.Type` column not declared `decimal`;
- a missing PBI_ResultType or PBI_NavigationStepName annotation;
- any `.pbi/unappliedChanges.json` or `cache.abf` in the project.

All other columns were compared with `information_schema` types and match.

**If the banner persists on a laptop**, a stale `Enterprise360.SemanticModel/.pbi/unappliedChanges.json` from an earlier "Apply later" may be left behind. It is git-ignored, so pulls never remove it. Close Desktop, compare it with the TMDL, delete it, and reopen.

## Olist reporting-month rule (trend visuals)

`core.dim_date.is_reporting_month` (DE's flag) is loaded as the hidden column `Date[is_reporting_month]`, alongside `is_complete_month`.

**Reporting months are 2017-01 to 2018-08.** Two kinds of month are excluded:
- 2016-09 and 2018-10 are incomplete.
- 2016-10, 2016-11, 2016-12 and 2018-09 are complete but sparse: 2016-11 has 0 orders, 2016-12 has R$11 and 2018-09 has R$145.

**Visuals with the visual-level filter `Date[is_reporting_month] = TRUE`** (8 visuals):
- Executive Command Center: monthly GMV trend, GMV Growth % (MoM), and the bookmark monthly scorecard.
- Sales Performance: GMV trend.
- Customer Intelligence: active vs new customers trend, and the monthly retention table.
- Operations & Delivery: on-time delivery % by delivery month.
- Seller Detail: seller GMV trend.

Product Performance has no monthly trend. Cards and totals are not filtered.

**[GMV Growth %]** is BLANK when the prior month's GMV is 0 or blank, or when the current or prior month is not complete or not a reporting month. This is the stricter rule: kpis.yaml KPI_GMV_GROWTH names `is_complete_month`, and says `is_reporting_month` governs the default report range.
- First values: 2017-01 is BLANK (2016-12 is not a reporting month).
- 2017-02 is +105.5% (R$120,313 → R$247,303).
- 2017-03 is +51.4%.
- 2017-04 is −3.9%.

**Net GMV gap.** [Net GMV] matches kpis.yaml (it excludes canceled and unavailable orders).
- GMV is R$13,591,643.70 and Net GMV is R$13,494,400.74, so the gap is 0.715% overall (0.681% in reporting months).
- Monthly, the gap is 0.18–1.95% in reporting months.
- Because the two lines overlap, the Executive trend shows GMV as the line. [GMV Excluded from Net] (DERIVED, KPI_NET_GMV) is plotted on the secondary axis, and a subtitle states the gap.

## UCI Online Retail II (GBP) — separate domain

A separate UK online-retail dataset (UCI Online Retail II, 2009-12-01 to 2011-12-09, **GBP**). It is **not comparable with Olist (BRL)** and is never joined to it.

**Source parameters:** `PgSchemaUci` (default `uci_core`) and `PgSchemaUciMarts` (default `uci_marts`). They use the same `PgServer` / `PgDatabase` and the same `e360_app` Database credentials. No password is stored.

**Tables.** All are UCI-only, built from the real dbt models in `dbt_enterprise360/models/uci`:

| Table | dbt model | Grain / role |
|---|---|---|
| UCI Invoice Line | uci_core.uci_fct_invoice_lines | invoice line (1,033,036 rows); all value measures |
| UCI Invoice | uci_core.uci_fct_invoices | invoice (C-prefixed = cancellation); invoice and customer counts |
| UCI Date | uci_core.uci_dim_date | UCI calendar, marked as date table; `is_complete_month`, `is_reporting_month` |
| UCI Customer | uci_core.uci_dim_customer | Customer ID; -1 = no Customer ID |
| UCI Product | uci_core.uci_dim_product | stock code |
| UCI Country | uci_core.uci_dim_country | invoice country |
| UCI Cohort | uci_marts.uci_mart_customer_cohorts | standalone (no relationships) |
| UCI RFM | uci_marts.uci_mart_customer_rfm | standalone (no relationships) |
| _Measures UCI | — | 19 measures, display folder `UCI Retail (GBP)\…`, £ formats |

**Relationships:** 7, all UCI→UCI, single-direction many-to-one:
- Invoice Line → Product / Customer / Country / Date
- Invoice → Customer / Country / Date

There are **no relationships between any UCI table and any Olist table**. UCI has its own date, customer, product and country dimensions. The `Time Intelligence` calculation group targets the Olist `Date`, so do not apply it to UCI visuals.

**Measures.** Names, ids and statuses match kpis.yaml v2.0.0 (domain `uci`). Each description carries its KPI id.

| Measure | KPI id | Status |
|---|---|---|
| UCI Gross Product Sales (label "Invoiced Value (gross product sales)") | KPI_UCI_GROSS_SALES | SUPPORTED |
| UCI Product Cancellations | KPI_UCI_PRODUCT_CANCELLATIONS | SUPPORTED |
| UCI Cancellation Rate % (Value) | KPI_UCI_CANCEL_RATE_VALUE | SUPPORTED |
| UCI Cancellation Rate % (Lines) | KPI_UCI_CANCEL_RATE_LINES | SUPPORTED |
| UCI Cancellation Rate % (Invoices) | KPI_UCI_CANCEL_RATE_INVOICES | SUPPORTED |
| UCI Discounts | KPI_UCI_DISCOUNTS | SUPPORTED |
| UCI Net Sales (proxy) (label "Net Sales (proxy)") | KPI_UCI_NET_SALES_PROXY | SUPPORTED |
| UCI Sales Invoices | KPI_UCI_INVOICES | SUPPORTED |
| UCI AOV | KPI_UCI_AOV | SUPPORTED |
| UCI Units per Invoice | KPI_UCI_UNITS_PER_INVOICE | SUPPORTED |
| UCI Postage, UCI Fees | KPI_UCI_POSTAGE_FEES | SUPPORTED |
| UCI Active Customers | KPI_UCI_ACTIVE_CUSTOMERS | SUPPORTED |
| UCI New Customers | KPI_UCI_NEW_CUSTOMERS | SUPPORTED |
| UCI Repeat Rate % | KPI_UCI_REPEAT_RATE | SUPPORTED |
| UCI Lines Without Customer ID % | DERIVED (no coverage KPI in kpis.yaml) | DERIVED: project-lead approved; `has_customer = FALSE` lines / all lines; warehouse check 22.76% (235,151 / 1,033,036) |
| UCI Cohort Retention % | KPI_UCI_RETENTION | **PARTIAL** |
| UCI Customers by RFM Segment | KPI_UCI_RFM_SEGMENT | **PARTIAL** |
| UCI Product Contribution % | KPI_UCI_PRODUCT_CONTRIBUTION | SUPPORTED |
| UCI Country Contribution % | KPI_UCI_COUNTRY_CONTRIBUTION | SUPPORTED |

**How the measures work:**
- **AOV** = `[UCI Net Sales (proxy)] / [UCI Sales Invoices]`, a ratio of sums at every grain. It never averages `aov_gbp`. It does not hold under a UCI Product filter, because its denominator is counted per invoice.
- **Net Sales (proxy)** = gross product sales + product cancellations + discounts. Postage and fees are excluded. It is an operational proxy, not recognised sales.

**Verified against the warehouse (full coverage):**
- Net Sales (proxy) £18,914,519.44; Invoiced Value £19,643,861.64.
- Sales invoices 45,336; **AOV £417.21**.
- These match the line-level replication of the DAX and `uci_mart_sales_daily`.

**How 2011-12 is handled:** 2011-12 is a partial month (data ends 2011-12-09).
- **Overall totals and cards include it.** The kpis.yaml validation totals (net 18,914,519.437, AOV 417.21) are full-coverage figures.
- **Trend visuals exclude it** with a visual filter `UCI Date[is_reporting_month] = TRUE` (dbt/DE completeness flag), and each says so in its subtitle.
- Cohort retention blanks any active month where `is_complete_month` = FALSE.

**Pages.** They sit after the Olist pages in the page navigator under the "UCI …" prefix (label: UCI Online Retail II (GBP)). Each page carries the subtitle "UCI Online Retail II (GBP): separate UK dataset, not comparable with Olist (BRL)" and has its own UCI date and country slicers.
- **UCI Retail Overview:**
  - Cards: Net Sales (proxy), Invoiced Value, sales invoices, AOV, active customers, units per invoice.
  - Monthly trend (excludes 2011-12).
  - Net Sales (proxy) by country, plus a non-UK country contribution view.
  - Top products table, totals off.
- **UCI Customers & Retention:**
  - Active customers (identified only; 22.8% of lines have no Customer ID).
  - New customers (2009-12 overstated).
  - Repeat rate (full coverage).
  - RFM R×F matrix (PARTIAL caveat).
  - Cohort retention matrix (PARTIAL caveat from kpis.yaml).
- **UCI Cancellations & Discounts:**
  - The three cancellation rates, cancellations, discounts, postage and fees.
  - Monthly trend; by country; most-cancelled products.
  - These are cancellations (C invoices), not confirmed returns.

**RLS:** The "State Manager (demo)" role hides every UCI table with `FALSE()`. The state filter is Olist-only, and UCI has no Brazilian state.

**Validator checks** (`domain-separation`). The validator fails if:
- any relationship connects a UCI table to an Olist table;
- any visual mixes UCI and Olist fields;
- any measure references the other domain's tables or measures;
- a UCI page lacks the "not comparable with Olist" subtitle;
- the demo role does not hide every UCI table.

UCI tables are those named `UCI …` and `_Measures UCI`.

**NOT SUPPORTED (UCI)** — no measures or visuals were built for these:
- Recognised revenue, margin and profit. There is no cost data, and Net Sales (proxy) is not revenue.
- Confirmed returns and refunds. C invoices are cancellations and are not linked to their original invoice.
- Comparing or combining any figure with Olist (different country, currency and period).
- FX conversion of GBP.
- RFM segment names. Labels are to be set by the owner (KPI_UCI_RFM_SEGMENT PARTIAL).

**Pending on DE / owner:**
- RFM segment-label rules. I checked `uci_mart_customer_rfm` (dbt SQL and warehouse columns): it has only `r_score`, `f_score`, `m_score`, recency/frequency/monetary and snapshot columns, with **no segment label column**. The report therefore shows R, F and M scores only (R × F matrix, M Score available as a field). No segment names are defined anywhere in the model or report. Labels will be added only when DE/owner publishes them.
- Retention: the 2009-12 cohort mixes pre-existing customers.

## Regenerate and validate
```
python tools/build_pbip.py                       # regenerates both folders (deterministic ids)
/workspace/enterprise360/.venv/bin/python tools/validate_pbip.py --schemas <clone of github.com/microsoft/json-schemas> --model-json <tom-export.json>
```
`--model-json` is the TOM JSON export of the TMDL folder, produced by the TmdlSerializer check (a small .NET 8 console app using `Microsoft.AnalysisServices.NetCore.retail.amd64`: `TmdlSerializer.DeserializeDatabaseFromFolder`, then `Model.Validate()`, then `JsonSerializer.SerializeDatabase`).
Last run:
- All 119 JSON files are valid against their `$schema`, including 2 bookmarks, bookmarks.json, 2 tooltip pages and 2 drill-through pages.
- TMDL deserialised with 13 tables, 43 measures, 10 relationships and 1 role, and `Model.Validate()` reported no errors.
- RLS-safety scan: 51 expressions, 0 violations.
- Cross-references checked: relationships, sortBy columns, measure → column/measure references, role filter columns, every visual field, drill-through filter/binding and source visuals, tooltip assignments → Tooltip pages, and bookmark targets and button links. 0 errors.

Not done here (needs Desktop and the database): DAX evaluation and a refresh. After the first refresh, reconcile `[GMV]`, `[Orders]` and `[Payment Value]` to `marts.mart_sales_daily`.

## Known limitations
- Paginated MIS needs Premium, PPU or Fabric.
- Exports are capped (about 150k rows to xlsx).
- Bookmarks only toggle visibility.
- Button and page-navigator styling is minimal and may need polishing in Desktop.
- Geography is customer state only; seller state is a Seller attribute.
- Timestamps are local Brazil time with no time zone (assumption).
- The Time Intelligence calc group applies to every measure; use it on additive or ratio measures with care.
