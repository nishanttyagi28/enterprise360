# Assumptions & Limitations (KPI & Quality) — 2026-10-30

Dataset in scope: **Olist Brazilian E-Commerce Public Dataset** (Kaggle `olistbr/brazilian-ecommerce`, CC BY-NC-SA 4.0), 9 CSVs, BRL. CONFIRMED FACT: file list/headers inspected in `data/raw/olist/brazilian-ecommerce.zip`.

## Domains with NO real data in Olist — handling
| Domain / brief section | Missing | Handling |
|---|---|---|
| Finance GL / P&L | revenue recognition, COGS, opex, tax, AR/AP, cash | Excluded. No Revenue/GP/GM/OP measures. GMV labelled as GMV, never revenue. Payments = transaction value, not cash flow. |
| Margin / profitability | product cost | Excluded; no imputed costs. |
| Budget / targets | budgets, targets | Excluded; Target Achievement & Budget vs Actual "not available". Targets: to be set by owner. |
| Marketing | spend, impressions, campaigns | CAC/ROAS/ROI excluded. Olist Marketing Funnel (separate dataset, leads only) may be added as its own domain later. |
| Inventory / supply | stock, POs, suppliers | Excluded. Sellers are marketplace merchants, not suppliers. |
| Returns / refunds | returns table | No Return Rate. Only Cancellation Rate (canceled/unavailable status). |
| HR / workforce | all | Excluded from Olist; any HR dataset is a separate, unrelated domain, never joined. |
| Customer service | tickets, resolution time | Excluded; review score is a satisfaction proxy only. |

**No department is synthesized silently.** Unsupported visuals show "Not available from source" with the reason from `governance/kpi_dictionary/not_supported.yaml`.

## Assumptions to confirm
- A1 Timestamps are local Brazil time, no TZ (publisher silent).
- A2 One order_items row = one unit.
- A3 Payment vs items+freight (|diff|>0.01 BRL, exact numeric(12,2)): **1,076 orders** = 772 payments without items, 264 overpaid, 39 underpaid, 1 items without payment. WARN, categorised, logged under KPI_PAYMENT_VALUE. (An earlier float-based raw check reported 1,153; the extra 77 were float artefacts at exactly 0.01 BRL.)
- A4 dbt names CONFIRMED against DE models (2026-10-30), incl. int_olist__zip_prefix_centroid, int_olist__order_items_aggregated, int_olist__order_payments_aggregated, int_olist__order_items_enriched, int_olist__month_coverage; dim_date flags is_complete_month, is_low_volume_month, is_reporting_month.
- A5 Power BI measure names in docs/kpi-catalog.md are proposals; no powerbi/ files existed.
- A6 Estimated delivery date is Olist's customer estimate, not a contractual SLA.

## Olist Marketing Funnel (KPI dictionary 2.1.0, 2026-10-31)
- L-F1 Separate dataset: 8,000 MQLs (first_contact 2017-06-14..2018-05-31) and 842 closed deals (won 2017-12-05..2018-11-14); all 842 deals match an MQL. Only 380 of 842 closed-deal seller_ids appear in olist_order_items; funnel and order KPIs are not joined except via seller_id with that caveat.
- L-F2 No marketing spend/impressions: CAC, ROAS, CTR, ROI not supported. `declared_monthly_revenue` is seller self-declared (94.7% zero) — not revenue, not a KPI.
- L-F3 Conversion is by first-contact cohort (overall 10.53%). Deal capture starts Dec 2017, so 2017 cohorts look low (0.84%–5.5%) partly by data artefact; 2018 cohorts are right-censored. Maturity window locked at 210 days (observed p95 days-to-close; p90 162): cohort mature when month end + 210 days <= max(won_date) (2018-11-14), so Apr and May 2018 cohorts are immature. mart_funnel_monthly must expose converted_leads_in_cohort, mqls, is_cohort_mature.
- L-F4 Median days to close = 14 (841 deals; 1 negative duration of -2 days excluded, WARN). Non-additive; never average.
- L-F5 Sparse columns in closed deals: has_company 92.5% null, has_gtin 92.4%, average_stock 92.2%, declared_product_catalog_size 91.8%, lead_behaviour_profile 21.0%. MQL origin 0.75% null plus 1,099 'unknown'.
- L-F6 DE models core.fct_leads, core.fct_closed_deals, core.dim_lead_origin, marts.mart_funnel_monthly, marts.mart_funnel_time_to_close committed (bb277c9) and built; funnel_models_built=true (set by DE). KPI_FUNNEL_* sources CONFIRMED.
- L-F7 Funnel measures are not restricted to Olist reporting months (wins run to 2018-11-14). The time-to-close breakdown covers all dates (mart has no date grain) and totals 841 (negative bucket excluded).

## GMV forecast / anomaly (exploratory)
- L-G1 Forecasts and anomaly flags are exploratory and model-based; GMV only (item price), never revenue. Intervals are not guarantees.
- L-G2 ~20 usable complete reporting months (is_complete_month AND is_reporting_month); 2016 and Sep–Oct 2018 excluded. Black Friday 2017-11-24 and the May 2018 truckers' strike distort fits and will flag.
- L-G3 DE forecast committed (9972c3e): marts.mart_gmv_forecast, mart_gmv_anomalies, mart_gmv_forecast_backtest (latest run 58cb013e). Monthly, horizon 6, 20 complete reporting months. Selection by rolling-origin CV on train+validation only (holt_damped 16.80% vs naive 21.21% CV sMAPE). Backtest (3 points each): validation 5.80% vs 16.11%; TEST 28.25% vs 13.37% — the model LOSES to the naive baseline on test; baseline is the stronger reference and the forecast must not drive decisions.
- L-G4 Intervals: conformal_abs_cv (95%, CV absolute errors before each cutoff; no test leakage). 3/3 test months inside for GMV and orders, but bands are wide (~755k–1.64M BRL) and 3 points cannot show calibration.
- L-G5 Anomalies monthly (robust z > 3.5, 1.4826*MAD, in-sample expectation): 0 GMV anomaly months (Nov 2017 GMV z 2.84; orders z 4.76, 1 orders anomaly month). Use is_gmv_anomaly; is_any_anomaly = GMV OR orders; no is_anomaly column remains.
- L-F8 mart_funnel_monthly.is_deal_window_complete = false for cohorts 2017-06..2017-11 (deal recording starts 2017-12, left-censored); separate from is_cohort_mature (Apr–May 2018 immature).
