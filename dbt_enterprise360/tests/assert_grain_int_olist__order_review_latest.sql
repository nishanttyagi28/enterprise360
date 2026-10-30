-- grain: one row per (order_id) in int_olist__order_review_latest. Returns duplicates.
select order_id, count(*) as n from {{ ref('int_olist__order_review_latest') }} group by order_id having count(*) > 1
