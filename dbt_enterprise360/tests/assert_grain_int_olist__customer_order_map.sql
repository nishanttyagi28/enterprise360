-- grain: one row per (customer_id) in int_olist__customer_order_map. Returns duplicates.
select customer_id, count(*) as n from {{ ref('int_olist__customer_order_map') }} group by customer_id having count(*) > 1
