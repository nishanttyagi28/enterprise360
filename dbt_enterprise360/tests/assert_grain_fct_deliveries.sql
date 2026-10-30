-- grain: one row per (order_id) in fct_deliveries. Returns duplicates.
select order_id, count(*) as n from {{ ref('fct_deliveries') }} group by order_id having count(*) > 1
