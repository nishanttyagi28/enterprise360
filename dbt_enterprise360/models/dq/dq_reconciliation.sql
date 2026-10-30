-- One row per reconciliation check (check_name == the dbt test name it quantifies). Computed every
-- build and captured into dq.dq_results_log by the on-run-end hook (source_value / mart_value /
-- variance = mart - source, KPI_RECON_VARIANCE). UCI dedup rows: source = rows before, mart = after. Aggregates per side before comparing (no fan-out).
with raw_orders as (select count(*)::numeric v from {{ source('olist', 'olist_orders') }}),
     stg_orders as (select count(distinct order_id)::numeric v from {{ ref('stg_olist__orders') }}),
     fct_orders as (select count(*)::numeric v from {{ ref('fct_orders') }}),
     stg_items  as (select sum(item_price)::numeric v from {{ ref('stg_olist__order_items') }}),
     fct_items  as (select sum(item_price)::numeric v, sum(item_price + freight_value)::numeric g
                    from {{ ref('fct_order_items') }}),
     stg_pay    as (select sum(payment_value)::numeric v from {{ ref('stg_olist__order_payments') }}),
     fct_pay    as (select sum(payment_value)::numeric v from {{ ref('fct_payments') }}),
     mart_gmv   as (select sum(gmv)::numeric v from {{ ref('mart_sales_daily') }})
select check_name, source_value, mart_value, mart_value - source_value as variance
from (
    select 'assert_recon_fct_orders_vs_staging' as check_name, s.v as source_value, f.v as mart_value
    from stg_orders s, fct_orders f
    union all select 'assert_recon_raw_vs_core_orders', r.v, f.v from raw_orders r, fct_orders f
    union all select 'assert_recon_fct_order_items_vs_staging', s.v, f.v from stg_items s, fct_items f
    union all select 'assert_recon_fct_payments_vs_staging', s.v, f.v from stg_pay s, fct_pay f
    -- payments vs items+freight: source = items+freight (what was ordered), mart = paid
    union all select 'assert_payments_vs_items_freight', f.g, p.v from fct_items f, fct_pay p
    union all select 'assert_recon_marts_vs_facts', f.v, m.v from fct_items f, mart_gmv m
    -- UCI (independent domain; metrics only side by side, never joined to Olist rows)
    union all select check_name, rows_before, rows_after from {{ ref('int_uci__dedup_stats') }}
    union all select 'assert_uci_recon_lines_vs_staging',
        (select sum(quantity * unit_price) from {{ ref('stg_uci__invoice_lines') }}),
        (select sum(line_value) from {{ ref('uci_fct_invoice_lines') }})
    union all select 'assert_uci_recon_mart_sales_daily_vs_fact',
        (select sum(line_value) from {{ ref('uci_fct_invoice_lines') }}
          where line_type = 'product' and not is_cancellation and quantity > 0 and unit_price > 0),
        (select sum(gross_product_sales) from {{ ref('uci_mart_sales_daily') }})
    union all select 'assert_uci_recon_mart_product_vs_fact',
        (select sum(line_value) from {{ ref('uci_fct_invoice_lines') }}
          where line_type = 'product' and not is_cancellation and quantity > 0 and unit_price > 0),
        (select sum(gross_sales) from {{ ref('uci_mart_product_monthly') }})
) x
