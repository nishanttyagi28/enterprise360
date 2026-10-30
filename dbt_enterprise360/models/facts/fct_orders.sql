-- Grain: one row per order (all statuses). Business process: order placement.
-- Items and payments arrive PRE-AGGREGATED to order grain (int_*_aggregated), so this model is a
-- chain of 1:1 left joins on order_id -> row count == stg_olist__orders (tested).
-- Full rebuild (table): it depends on 5 inputs, and ~100k rows rebuild in seconds; an incremental
-- version would need change tracking across all of them for no material gain.
select
    {{ dbt_utils.generate_surrogate_key(['o.order_id']) }}          as order_sk,
    o.order_id,
    o.customer_id,
    m.customer_sk,
    {{ dbt_utils.generate_surrogate_key(['m.customer_zip_prefix']) }} as geography_sk,
    {{ date_key('o.purchased_at') }}                                as purchase_date_key,
    o.order_status,
    o.order_status in ('canceled', 'unavailable')                   as is_canceled,   -- KPI_CANCEL_RATE
    o.order_status = 'delivered'                                    as is_delivered,
    o.purchased_at,
    o.approved_at,
    round(extract(epoch from (o.approved_at - o.purchased_at)) / 3600.0, 2) as hours_to_approve, -- KPI_APPROVAL_HOURS
    coalesce(i.item_count, 0)                                       as item_count,
    coalesce(i.items_price_total, 0)::numeric(14, 2)                as items_price_total,   -- KPI_GMV at order grain
    coalesce(i.freight_total, 0)::numeric(14, 2)                    as freight_total,
    coalesce(i.items_gross_total, 0)::numeric(14, 2)                as items_gross_total,   -- KPI_GMV_INCL_FREIGHT
    coalesce(p.payment_value_total, 0)::numeric(14, 2)              as payment_value_total, -- KPI_PAYMENT_VALUE
    coalesce(p.payment_count, 0)                                    as payment_count,
    p.primary_payment_type,
    p.max_installments,
    coalesce(p.used_voucher, false)                                 as used_voucher,
    i.order_id is not null                                          as has_items,
    p.order_id is not null                                          as has_payment,
    -- payments vs items+freight gap: known non-zero for vouchers/interest/no-item orders (warn test)
    (coalesce(p.payment_value_total, 0) - coalesce(i.items_gross_total, 0))::numeric(14, 2) as payment_vs_items_diff,
    r.review_score                                                  as latest_review_score
from {{ ref('stg_olist__orders') }} o
left join {{ ref('int_olist__customer_order_map') }} m on m.customer_id = o.customer_id
left join {{ ref('int_olist__order_items_aggregated') }} i on i.order_id = o.order_id
left join {{ ref('int_olist__order_payments_aggregated') }} p on p.order_id = o.order_id
left join {{ ref('int_olist__order_review_latest') }} r on r.order_id = o.order_id
