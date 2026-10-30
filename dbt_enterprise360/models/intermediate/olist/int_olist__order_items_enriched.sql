-- Order lines + order context needed at line grain (status for KPI_NET_GMV, purchase date for
-- time slicing). orders is the "one" side (order_id unique) -> no fan-out.
select
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    i.shipping_limit_at,
    i.item_price,
    i.freight_value,
    o.order_status,
    o.order_status in ('canceled', 'unavailable')  as is_canceled,
    o.purchased_at,
    o.delivered_carrier_at,   -- order-level; repeats per line (used for per-line handover SLA)
    i._ingested_at
from {{ ref('stg_olist__order_items') }} i
inner join {{ ref('stg_olist__orders') }} o on o.order_id = i.order_id
