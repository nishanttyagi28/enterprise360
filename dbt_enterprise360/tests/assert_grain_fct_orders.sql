-- grain: one row per (order_id) in fct_orders. Returns duplicates.
select order_id, count(*) as n from {{ ref('fct_orders') }} group by order_id having count(*) > 1
