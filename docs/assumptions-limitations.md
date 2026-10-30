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
