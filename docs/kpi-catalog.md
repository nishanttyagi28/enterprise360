# KPI Catalog (generated from governance/kpi_dictionary/kpis.yaml — do not hand-edit)

Dataset: Olist (BRL). GMV = SUM(item_price), freight excluded; **GMV is not recognized revenue**. Targets/benchmarks: to be set by owner.

Power BI measure names below are PROPOSED: no powerbi/ files existed at generation time (2026-10-30), so they need confirming with the Power BI teammate (see 02-reporting-architecture.md: each measure description must carry the KPI id).

| ID | Name | Status | Formula | Grain | dbt source | PBI measure (proposed) | Owner |
|---|---|---|---|---|---|---|---|
| KPI_GMV | Gross Merchandise Value | SUPPORTED | `SUM(fct_order_items.item_price)` | order line (order_id, order_item_id) | fct_order_items.item_price | [GMV] | Head of Sales |
| KPI_GMV_INCL_FREIGHT | GMV incl. Freight | SUPPORTED | `SUM(item_price + freight_value)` | order line | fct_order_items | [GMV incl Freight] | Head of Sales |
| KPI_NET_GMV | Net GMV (excl. canceled/unavailable) | SUPPORTED | `SUM(item_price) WHERE order_status NOT IN ('canceled','unavailable')` | order line | fct_order_items + fct_orders.is_canceled | [Net GMV] | Head of Sales |
| KPI_FREIGHT | Freight Value | SUPPORTED | `SUM(freight_value)` | order line | fct_order_items.freight_value | [Freight Value] | Head of Operations |
| KPI_FREIGHT_SHARE | Freight Share of GMV | SUPPORTED | `KPI_FREIGHT / KPI_GMV` | order line (ratio of sums) | fct_order_items | [Freight Share %] | Head of Operations |
| KPI_PAYMENT_VALUE | Payment Value | SUPPORTED | `SUM(fct_payments.payment_value)` | payment (order_id, payment_sequential) | fct_payments.payment_value | [Payment Value] | Finance |
| KPI_ORDERS | Orders | SUPPORTED | `COUNT(DISTINCT order_id)` | order | fct_orders | [Orders] | Head of Sales |
| KPI_AOV | Average Order Value | SUPPORTED | `KPI_GMV / COUNT(DISTINCT order_id with items)` | order (non-additive) | fct_order_items | [AOV] | Head of Sales |
| KPI_ITEMS_PER_ORDER | Items per Order | SUPPORTED | `COUNT(order lines)/COUNT(DISTINCT order_id)` | order | fct_order_items | [Items per Order] | Head of Sales |
| KPI_CANCEL_RATE | Cancellation Rate | SUPPORTED | `orders(status in canceled,unavailable)/KPI_ORDERS` | order | fct_orders.is_canceled | [Cancellation Rate %] | Head of Operations |
| KPI_ACTIVE_CUSTOMERS | Active Customers | SUPPORTED | `COUNT(DISTINCT customer_unique_id)` | customer × period (non-additive) | fct_orders.customer_sk | [Active Customers] | Head of CRM |
| KPI_NEW_CUSTOMERS | New Customers | SUPPORTED | `COUNT(DISTINCT customer_unique_id WHERE first_order_date in period)` | customer × period | dim_customer.first_order_date | [New Customers] | Head of CRM |
| KPI_REPEAT_RATE | Repeat Purchase Rate | SUPPORTED | `customers with ≥2 orders / customers` | customer | dim_customer.lifetime_orders | [Repeat Purchase Rate %] | Head of CRM |
| KPI_OTD_RATE | On-Time Delivery Rate | SUPPORTED | `on-time delivered / delivered with non-null delivered_customer_at` | order | fct_deliveries.is_on_time | [On-Time Delivery %] | Head of Operations |
| KPI_DELIVERY_DAYS | Average Delivery Days | SUPPORTED | `AVG(delivered_customer_at − purchased_at in days)` | order | fct_deliveries.delivery_days | [Avg Delivery Days] | Head of Operations |
| KPI_APPROVAL_HOURS | Order Approval Time | SUPPORTED | `AVG(approved_at − purchased_at)` | order | fct_orders.hours_to_approve | [Avg Approval Hours] | Head of Operations |
| KPI_REVIEW_SCORE | Average Review Score | SUPPORTED | `AVG(review_score) over int_olist__order_review_latest` | order (latest review) | int_olist__order_review_latest | [Avg Review Score] | Head of CX |
| KPI_LOW_REVIEW_RATE | Low Review Share | SUPPORTED | `orders score<=2 / orders reviewed` | order | int_olist__order_review_latest | [Low Review %] | Head of CX |
| KPI_GMV_GROWTH | GMV Growth % | PARTIAL | `(GMV_t − GMV_t−1)/GMV_t−1` | month | fct_order_items | [GMV Growth %] | Head of Sales |
| KPI_CUSTOMER_RETENTION | Customer Retention Rate | PARTIAL | `retained / prior active` | cohort × period | fct_orders | [Customer Retention %] | Head of CRM |
| KPI_DQ_SCORE | Data Quality Score | SUPPORTED | `Σ(pass×weight)/Σ(weight)` | check × run | core.dq_results | [DQ Score %] | Data Platform Lead |
| KPI_RECON_VARIANCE | Reconciliation Variance | SUPPORTED | `mart_value − source_value` | kpi × run | core.dq_results | [Reconciliation Variance] | Data Platform Lead |
| KPI_SELLER_HANDOVER_OTD | Seller Handover On-Time Rate | PARTIAL | `count(items with delivered_carrier_at <= shipping_limit_at) / count(items with both timestamps)` | order item | fct_order_items + fct_deliveries | [Seller Handover On-Time %] | Head of Operations |

## Validation rules

- **KPI_GMV**: GMV must never be named or labelled 'Revenue' in any model, measure or visual; GMV >= KPI_NET_GMV for every period; sum(fct_order_items.item_price) == sum(stg_olist__order_items.item_price) (tolerance 0); freight excluded; see KPI_GMV_INCL_FREIGHT
- **KPI_GMV_INCL_FREIGHT**: == KPI_GMV + KPI_FREIGHT (tolerance 0.00)
- **KPI_NET_GMV**: <= KPI_GMV; label must say 'Net GMV' not 'Net Revenue'
- **KPI_FREIGHT**: freight_value >= 0
- **KPI_FREIGHT_SHARE**: ratio of sums; never average of line ratios
- **KPI_PAYMENT_VALUE**: fct_payments never joined to fct_order_items (fan-out); Per order: |sum(payment_value) − sum(item_price+freight_value)| <= 0.01 BRL else flagged (warn) — known exceptions: orders with payments but no items, vouchers, installment interest; exceptions counted in dq_results, not failed
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
- **KPI_GMV_GROWTH**: suppress periods flagged partial in dim_date coverage
- **KPI_CUSTOMER_RETENTION**: show cohort size
- **KPI_DQ_SCORE**: weights per 16 DQ framework
- **KPI_RECON_VARIANCE**: counts tolerance 0; amounts 0.01 BRL

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


## Supporting measures (same KPI, no new definition)

| PBI measure | KPI id | Purpose |
|---|---|---|
| [Payment Mix %] | KPI_PAYMENT_VALUE | Share of payment value by payment type. Labelled payment mix and never used as sales. |
| [Retention Cohort Size] | KPI_CUSTOMER_RETENTION | Denominator of retention (prior-month active customers), shown next to the PARTIAL rate. |
| [On-Time Delivery % (by Delivery Date)] | KPI_OTD_RATE | The same KPI on the delivery-date role instead of the purchase date. |
| [Items Sold] | KPI_ITEMS_PER_ORDER | Numerator of items per order (count of order lines). |
| [Late Orders] | KPI_OTD_RATE | OTD-eligible orders that are not on time. |
| [OTD Eligible Orders] | KPI_OTD_RATE | Denominator of the OTD rate. |
| [Delivered Missing Timestamp] | KPI_OTD_RATE | DQ exclusion count: status delivered with no delivered_customer_at. |
| [Delivered Before Purchase] | KPI_DELIVERY_DAYS | DQ exclusion count: delivered_customer_at earlier than purchased_at. |
| [Payment Mismatch Orders] | KPI_PAYMENT_VALUE | Orders where payments differ from items + freight by more than 0.01 BRL (warn). |
| [Payment Records] | KPI_PAYMENT_VALUE | Count of payment rows (order_id, payment_sequential). |
| [Checks Failed] | KPI_DQ_SCORE | Checks with status fail in the selected run. |
| [Checks Warned] | KPI_DQ_SCORE | Checks with status warn in the selected run. |
| [Blocking Failures] | KPI_DQ_SCORE | Checks with severity block and status fail. |
| [Failing Rows] | KPI_DQ_SCORE | Sum of failing_rows in the selected run. |
| [DQ Status Colour] | KPI_DQ_SCORE | Formatting only, not a KPI value. |

### Order-level KPIs under Product or Seller filters
When a product, category or seller filter is active, order-level KPIs (Orders, On-Time Delivery %, Avg Delivery Days, Avg Review Score, Avg Approval Hours) count orders that contain at least one matching line. A multi-category or multi-seller order counts once in each category or seller, so the breakdown does not add up to the company total. Reviews belong to orders, not products, so review score by category means the score of orders containing that category, not a product rating.
