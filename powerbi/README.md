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
│   └── StaticResources/RegisteredResources/Enterprise360Dark.json   # theme
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

## Report pages (1280×720, dark theme; page navigator on every page lists all visible pages)
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

## Regenerate and validate
```
python tools/build_pbip.py                       # regenerates both folders (deterministic ids)
python tools/validate_pbip.py --schemas <clone of github.com/microsoft/json-schemas> --model-json <tom-export.json>
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
