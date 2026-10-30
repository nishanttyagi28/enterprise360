-- grain: one row per (order_id, order_item_id) in fct_order_items. Returns duplicates.
select order_id, order_item_id, count(*) as n from {{ ref('fct_order_items') }} group by order_id, order_item_id having count(*) > 1
