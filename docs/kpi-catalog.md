# KPI Catalog (generated from governance/kpi_dictionary/kpis.yaml — do not hand-edit)

Dataset: Olist (BRL). GMV = SUM(item_price), freight excluded; **GMV is not recognized revenue**. Targets/benchmarks: to be set by owner.

Model/column names and Power BI measure names CONFIRMED against dbt_enterprise360/models and powerbi/Enterprise360.SemanticModel/_Measures.tmdl (2026-10-30): all 22 PBI measure names match.
Relevant DE models: int_olist__order_items_enriched → int_olist__order_items_aggregated / int_olist__order_payments_aggregated (order grain, no fan-out), int_olist__zip_prefix_centroid (geography), int_olist__month_coverage → dim_date flags is_complete_month, is_low_volume_month, is_reporting_month.

| ID | Name | Status | v | Formula | Grain | dbt source | PBI measure | Owner |
|---|---|---|---|---|---|---|---|---|
| KPI_GMV | Gross Merchandise Value | SUPPORTED | 1.1.0 | `SUM(fct_order_items.item_price)` | order line (order_id, order_item_id) | fct_order_items.item_price; order grain via int_olist__order_items_aggregated (from int_olist__order_items_enriched) | [GMV] | Head of Sales |
| KPI_GMV_INCL_FREIGHT | GMV incl. Freight | SUPPORTED | 1.1.0 | `SUM(item_price + freight_value)` | order line | fct_order_items | [GMV incl Freight] | Head of Sales |
| KPI_NET_GMV | Net GMV (excl. canceled/unavailable) | SUPPORTED | 1.1.0 | `SUM(item_price) WHERE order_status NOT IN ('canceled','unavailable')` | order line | fct_order_items + fct_orders.is_canceled; order grain via int_olist__order_items_aggregated (from int_olist__order_items_enriched) | [Net GMV] | Head of Sales |
| KPI_FREIGHT | Freight Value | SUPPORTED | 1.1.0 | `SUM(freight_value)` | order line | fct_order_items.freight_value; order grain via int_olist__order_items_aggregated (from int_olist__order_items_enriched) | [Freight Value] | Head of Operations |
| KPI_FREIGHT_SHARE | Freight Share of GMV | SUPPORTED | 1.1.0 | `KPI_FREIGHT / KPI_GMV` | order line (ratio of sums) | fct_order_items | [Freight Share %] | Head of Operations |
| KPI_PAYMENT_VALUE | Payment Value | SUPPORTED | 1.1.0 | `SUM(fct_payments.payment_value)` | payment (order_id, payment_sequential) | fct_payments.payment_value; order grain via int_olist__order_payments_aggregated → fct_orders | [Payment Value] | Finance |
| KPI_ORDERS | Orders | SUPPORTED | 1.1.0 | `COUNT(DISTINCT order_id)` | order | fct_orders | [Orders] | Head of Sales |
| KPI_AOV | Average Order Value | SUPPORTED | 1.1.0 | `KPI_GMV / COUNT(DISTINCT order_id with items)` | order (non-additive) | fct_order_items; order grain via int_olist__order_items_aggregated (from int_olist__order_items_enriched) | [AOV] | Head of Sales |
| KPI_ITEMS_PER_ORDER | Items per Order | SUPPORTED | 1.1.0 | `COUNT(order lines)/COUNT(DISTINCT order_id)` | order | fct_order_items; order grain via int_olist__order_items_aggregated (from int_olist__order_items_enriched) | [Items per Order] | Head of Sales |
| KPI_CANCEL_RATE | Cancellation Rate | SUPPORTED | 1.1.0 | `orders(status in canceled,unavailable)/KPI_ORDERS` | order | fct_orders.is_canceled | [Cancellation Rate %] | Head of Operations |
| KPI_ACTIVE_CUSTOMERS | Active Customers | SUPPORTED | 1.1.0 | `COUNT(DISTINCT customer_unique_id)` | customer × period (non-additive) | fct_orders.customer_sk | [Active Customers] | Head of CRM |
| KPI_NEW_CUSTOMERS | New Customers | SUPPORTED | 1.1.0 | `COUNT(DISTINCT customer_unique_id WHERE first_order_date in period)` | customer × period | dim_customer.first_order_date | [New Customers] | Head of CRM |
| KPI_REPEAT_RATE | Repeat Purchase Rate | SUPPORTED | 1.1.0 | `customers with ≥2 orders / customers` | customer | dim_customer.lifetime_orders | [Repeat Purchase Rate %] | Head of CRM |
| KPI_OTD_RATE | On-Time Delivery Rate | SUPPORTED | 1.1.0 | `count(is_otd_eligible AND is_on_time) / count(is_otd_eligible)` | order | fct_deliveries.is_on_time | [On-Time Delivery %] | Head of Operations |
| KPI_DELIVERY_DAYS | Average Delivery Days | SUPPORTED | 1.1.0 | `AVG(delivered_customer_at − purchased_at in days)` | order | fct_deliveries.delivery_days | [Avg Delivery Days] | Head of Operations |
| KPI_APPROVAL_HOURS | Order Approval Time | SUPPORTED | 1.1.0 | `AVG(approved_at − purchased_at)` | order | fct_orders.hours_to_approve | [Avg Approval Hours] | Head of Operations |
| KPI_REVIEW_SCORE | Average Review Score | SUPPORTED | 1.1.0 | `AVG(review_score) over int_olist__order_review_latest` | order (latest review) | int_olist__order_review_latest | [Avg Review Score] | Head of CX |
| KPI_LOW_REVIEW_RATE | Low Review Share | SUPPORTED | 1.1.0 | `orders score<=2 / orders reviewed` | order | int_olist__order_review_latest | [Low Review %] | Head of CX |
| KPI_GMV_GROWTH | GMV Growth % | PARTIAL | 1.1.0 | `(GMV_t − GMV_t−1)/GMV_t−1` | month | fct_order_items | [GMV Growth %] | Head of Sales |
| KPI_CUSTOMER_RETENTION | Customer Retention Rate | PARTIAL | 1.1.0 | `retained / prior active` | cohort × period | fct_orders | [Customer Retention %] | Head of CRM |
| KPI_DQ_SCORE | Data Quality Score | SUPPORTED | 1.1.0 | `Σ(pass×weight)/Σ(weight)` | check × run | core.dq_results | [DQ Score %] | Data Platform Lead |
| KPI_RECON_VARIANCE | Reconciliation Variance | SUPPORTED | 1.1.0 | `mart_value − source_value` | kpi × run | core.dq_results | [Reconciliation Variance] | Data Platform Lead |
| KPI_SELLER_HANDOVER_OTD | Seller Handover On-Time Rate | PARTIAL | 1.1.0 | `count(items where delivered_carrier_at <= shipping_limit_at) / count(items with both timestamps)` | order item | fct_order_items.shipping_limit_at joined to fct_deliveries.delivered_carrier_at on order_id (no fan-out, deliveries is one row per order) | [Seller Handover On-Time %] | Head of Operations |

## Validation rules

- **KPI_GMV**: GMV must never be named or labelled 'Revenue' in any model, measure or visual; GMV >= KPI_NET_GMV for every period; sum(fct_order_items.item_price) == sum(stg_olist__order_items.item_price) (tolerance 0); freight excluded; see KPI_GMV_INCL_FREIGHT; fct_orders item rollup == fct_order_items (assert_recon_fct_orders_items_rollup)
- **KPI_GMV_INCL_FREIGHT**: == KPI_GMV + KPI_FREIGHT (tolerance 0.00)
- **KPI_NET_GMV**: <= KPI_GMV; label must say 'Net GMV' not 'Net Revenue'
- **KPI_FREIGHT**: freight_value >= 0
- **KPI_FREIGHT_SHARE**: ratio of sums; never average of line ratios
- **KPI_PAYMENT_VALUE**: fct_payments never joined to fct_order_items (fan-out); Per order: |sum(payment_value) − sum(item_price+freight_value)| > 0.01 BRL, computed in exact numeric(12,2) (never float), is WARN not fail (dbt assert_payments_vs_items_freight). Known exceptions on 2026-10-30 build: 1,076 orders = 772 payment_without_items, 264 overpaid (installment interest?), 39 underpaid (voucher/discount?), 1 items_without_payment. Counts logged to dq_results with kpi_id KPI_PAYMENT_VALUE.
- **KPI_ORDERS**: order_id unique in fct_orders; count == distinct order_id in stg_olist__orders (tolerance 0)
- **KPI_AOV**: ratio of sums; never average of AOVs; denominator excludes orders with no items (e.g. some canceled/unavailable)
- **KPI_ITEMS_PER_ORDER**: >= 1
- **KPI_CANCEL_RATE**: 0..1; order_status accepted_values test passes
- **KPI_ACTIVE_CUSTOMERS**: must use customer_unique_id, NOT customer_id (customer_id is per order)
- **KPI_NEW_CUSTOMERS**: new + returning = active
- **KPI_REPEAT_RATE**: report numerator & denominator with rate (low base expected; report as observed)
- **KPI_OTD_RATE**: exclude delivered orders missing delivered_customer_at (counted as DQ); estimate is Olist's estimate, not a contractual SLA
- **KPI_DELIVERY_DAYS**: delivered_customer_at >= purchased_at else flagged & excluded; timestamps local, no TZ (ASSUMPTION)
- **KPI_APPROVAL_HOURS**: approved_at >= purchased_at
- **KPI_REVIEW_SCORE**: score in 1..5; one review per order in KPI basis
- **KPI_LOW_REVIEW_RATE**: 0..1
- **KPI_GMV_GROWTH**: BLANK unless is_complete_month for current and prior month (int_olist__month_coverage → dim_date); is_low_volume_month months shown with caution flag; is_reporting_month governs default report range; assert_month_coverage_consistent passes
- **KPI_CUSTOMER_RETENTION**: show cohort size
- **KPI_DQ_SCORE**: weights per 16 DQ framework
- **KPI_RECON_VARIANCE**: counts tolerance 0; amounts 0.01 BRL
- **KPI_SELLER_HANDOVER_OTD**: exclude items missing either timestamp (count separately as DQ); flag multi-seller orders; seller-level values for them share one order-level handover time; shipping_limit_at is Olist's seller deadline, not a contractual SLA; timestamp comparison, not date-only

## Payments vs items+freight known exceptions (KPI_PAYMENT_VALUE, WARN)

| Category | Orders |
|---|---|
| payment_without_items | 772 |
| overpaid (installment interest?) | 264 |
| underpaid (voucher/discount?) | 39 |
| items_without_payment | 1 |
| **Total** | **1,076** |

Compared in exact numeric(12,2). Float comparison inflates this to 1,153 (77 diffs of exactly 0.01 BRL).

## Not supported by Olist

| KPIs | Reason |
|---|---|
| Net/recognized revenue, Gross Profit, Gross Margin, Operating Profit/Margin, P&L, Cost per Order | No COGS, opex, invoicing, tax or GL in Olist |
| Target Achievement, Budget vs Actual, Budget Variance | No real targets/budgets; fabrication prohibited |
| CAC, ROAS, CTR, Marketing ROI | No marketing spend/impressions in Olist (Marketing Funnel has leads/deals only, separate dataset) |
| Return Rate / Refunds | No returns or refunds table |
| Inventory Turnover, Stockout, Fill Rate, Ageing | No inventory or stock data |
| Supplier/procurement KPIs (PPV, lead time, POs) | Sellers are marketplace merchants, not suppliers; no POs |
| Headcount, Attrition, Absenteeism, Hiring, Payroll | No HR data in Olist |
| Cash flow, AR/AP, Collections | Payments are transaction values, not cash settlement |
| Complaint Resolution Time | No complaint/ticket data; reviews are not tickets |
| Margin-based CLV | No cost data; revenue-based CLV would need explicit 'GMV-based' label |
