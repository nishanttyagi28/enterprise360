# Source-to-target column mapping — Olist → core
Concise column map (implemented). Rules and grains: `docs/blueprint/05-source-to-target-mapping.md` §2.
Staging applies to every text column: trim + null tokens ('', NA, nan, null, none) → NULL.

| Source file.column | staging column (type) | core column | Rule |
|---|---|---|---|
| orders.order_id | order_id | fct_orders.order_id, order_sk | BK; sk = hash(order_id) |
| orders.customer_id | customer_id | fct_orders.customer_id → customer_sk | via int_olist__customer_order_map |
| orders.order_status | order_status | fct_orders.order_status, is_canceled, is_delivered | lower; canceled/unavailable → is_canceled |
| orders.order_purchase_timestamp | purchased_at (timestamp) | purchased_at, purchase_date_key | date_key = YYYYMMDD |
| orders.order_approved_at | approved_at | fct_orders.hours_to_approve | (approved − purchased) h |
| orders.order_delivered_carrier_date | delivered_carrier_at | fct_deliveries.delivered_carrier_at; fct_order_items.delivered_carrier_at | order-level |
| orders.order_delivered_customer_date | delivered_customer_at | fct_deliveries.delivery_days, is_on_time | |
| orders.order_estimated_delivery_date | estimated_delivery_at | fct_deliveries.days_vs_estimate | |
| customers.customer_unique_id | customer_unique_id | dim_customer.customer_unique_id, customer_sk | BK of dim_customer |
| customers.customer_zip_code_prefix | customer_zip_prefix (char 5) | dim_customer.zip_prefix, geography_sk | lpad 5 |
| customers.customer_city / _state | customer_city / customer_state | dim_customer.city / state | latest order's values |
| order_items.order_id, order_item_id | order_id, order_item_id (smallint) | fct_order_items.order_id, order_item_id, order_item_sk | PK pair |
| order_items.product_id / seller_id | product_id / seller_id | product_sk / seller_sk | hash(BK) |
| order_items.shipping_limit_date | shipping_limit_at (timestamp) | fct_order_items.shipping_limit_at, is_handover_on_time | carrier ≤ limit |
| order_items.price | item_price (numeric 12,2) | fct_order_items.item_price; fct_orders.items_price_total | KPI_GMV |
| order_items.freight_value | freight_value (numeric 12,2) | fct_order_items.freight_value; fct_orders.freight_total | KPI_FREIGHT |
| order_payments.payment_sequential | payment_sequential | fct_payments.payment_sequential, payment_sk | PK with order_id |
| order_payments.payment_type | payment_type | fct_payments.payment_type; fct_orders.primary_payment_type | |
| order_payments.payment_installments | payment_installments | fct_payments.payment_installments | |
| order_payments.payment_value | payment_value (numeric 12,2) | fct_payments.payment_value; fct_orders.payment_value_total | KPI_PAYMENT_VALUE |
| order_reviews.review_id, order_id | review_id, order_id | fct_reviews.review_id, order_id, review_sk | PK pair |
| order_reviews.review_score | review_score (smallint) | fct_reviews.review_score; fct_orders.latest_review_score | latest per order |
| order_reviews.review_comment_title / _message | review_title / review_message | fct_reviews.has_comment | text not carried to core |
| order_reviews.review_creation_date / review_answer_timestamp | review_created_at / review_answered_at | fct_reviews.hours_to_answer | |
| products.product_id | product_id | dim_product.product_id, product_sk | BK |
| products.product_category_name | category_name_pt | dim_product.category_name_pt | NULL → 'unknown' |
| translation.product_category_name_english | category_name_en | dim_product.category_name_en | fallback pt name |
| products.product_name_lenght / product_description_lenght | product_name_length / product_description_length | same | typo fixed |
| products.product_photos_qty, weight_g, length/height/width_cm | same (int) | same + product_volume_cm3 | l×h×w |
| sellers.seller_id | seller_id | dim_seller.seller_id, seller_sk | BK |
| sellers.seller_zip_code_prefix / city / state | seller_zip_prefix / seller_city / seller_state | dim_seller.zip_prefix, geography_sk, city, state | |
| geolocation.geolocation_zip_code_prefix | zip_prefix | dim_geography.zip_prefix, geography_sk | one row per prefix |
| geolocation.geolocation_lat / _lng | lat / lng (numeric 9,6), is_within_brazil | dim_geography.lat / lng | median of in-Brazil points |
| geolocation.geolocation_city / _state | city / state | dim_geography.city / state | mode; fallback customer/seller values |

## Marketing Funnel → core (Kaggle olistbr/marketing-funnel-olist)
| Source file.column | staging column (type) | core column | Rule |
|---|---|---|---|
| mql.mql_id | mql_id | fct_leads.mql_id, lead_sk | BK; sk = hash(mql_id); unique (8,000) |
| mql.first_contact_date | first_contact_date (date) | fct_leads.first_contact_date, first_contact_date_key, first_contact_month | cohort = month |
| mql.landing_page_id | landing_page_id | fct_leads.landing_page_id | as-is (495 values) |
| mql.origin | origin (lower) | dim_lead_origin.origin → fct_leads.origin_sk | null → unknown member 'not_recorded' (60); source 'unknown' kept |
| deals.mql_id | mql_id | fct_closed_deals.mql_id, deal_sk; fct_leads.is_closed | 1:1 to lead (842, all match) |
| deals.seller_id | seller_id | fct_closed_deals.seller_id, seller_sk, is_seller_in_olist_orders | seller_sk only if in dim_seller (380/842 = 45.1%) |
| deals.sdr_id / sr_id | sdr_id / sr_id | fct_closed_deals.sdr_id / sr_id | as-is |
| deals.won_date | won_date (timestamp) | fct_leads.won_date, won_date_key, days_to_close; fct_closed_deals.won_date, won_month | days_to_close = won_date::date − first_contact_date; < 0 flagged, excluded from stats |
| deals.business_segment, lead_type, lead_behaviour_profile, average_stock, business_type | lower | fct_closed_deals.* | as-is (sparse) |
| deals.has_company / has_gtin | boolean | fct_closed_deals.* | 'True'/'False' → bool; else null |
| deals.declared_product_catalog_size | integer | fct_closed_deals.* | numeric text → int |
| deals.declared_monthly_revenue | declared_monthly_revenue_brl numeric(18,2) | fct_closed_deals.declared_monthly_revenue_brl | self-declared, descriptive only; never a KPI |

## Forecast (Python) → marts
| Source | Target | Rule |
|---|---|---|
| marts.mart_business_overview_monthly.gmv / orders (complete ∧ reporting months) | analytics.forecast_monthly.actual_gmv / actual_orders | 2017-01..2018-08 |
| ETS model / naive | forecast_* / baseline_* (+ lower/upper, 95%) | see docs/forecasting.md |
| residual robust z | analytics.forecast_anomalies.*_robust_z, is_*_anomaly | z > 3.5 |
| latest successful run | marts.mart_gmv_forecast / mart_gmv_anomalies / mart_gmv_forecast_backtest | int_latest_forecast_run |
