# dbt tests (KPI & Quality)
Written 2026-10-30 **before any dbt models existed**. Model/column names come from docs/blueprint/05-source-to-target-mapping.md
and MUST be confirmed by Data Engineering: fct_orders, fct_order_items, fct_payments, fct_reviews, fct_deliveries, dim_customer,
dim_product, dim_seller, dim_geography, dim_date, stg_olist__orders/order_items/order_payments, int_olist__order_review_latest,
int_olist__customer_order_map; columns item_price, freight_value, payment_value, purchased_at, delivered_customer_at,
product_sk, seller_sk, customer_sk, purchase_date_key, date_key, date_day, zip_prefix.
- generic/: `grain_unique(columns)`, `row_count_matches(compare_model, key)` — attach in model yml.
- assert_grain_*: PK/grain per fact & dim. assert_recon_*: fact vs staging totals (tolerance 0). 
- assert_payments_vs_items_freight: WARN with categorised known exceptions. assert_no_fanout_*: join row preservation.
