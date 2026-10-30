-- No-fan-out proof: order-level item rollup in fct_orders equals line-level fct_order_items,
-- per order and in total (tolerance 0.00 BRL).
with lines as (
    select order_id, sum(item_price) p, sum(freight_value) f, count(*) n
    from {{ ref('fct_order_items') }} group by 1
)
select o.order_id, o.items_price_total, l.p, o.freight_total, l.f
from {{ ref('fct_orders') }} o
full outer join lines l on l.order_id = o.order_id
where coalesce(o.items_price_total, 0) <> coalesce(l.p, 0)
   or coalesce(o.freight_total, 0) <> coalesce(l.f, 0)
   or coalesce(o.item_count, 0) <> coalesce(l.n, 0)
