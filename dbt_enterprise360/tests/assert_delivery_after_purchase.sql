{{ config(severity='warn') }}
-- KPI_DELIVERY_DAYS / KPI_OTD_RATE input sanity; violators flagged and excluded from KPIs
select order_id from {{ ref('fct_deliveries') }} where delivered_customer_at < purchased_at
