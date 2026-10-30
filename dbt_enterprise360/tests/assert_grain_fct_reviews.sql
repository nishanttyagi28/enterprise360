-- grain: one row per (review_id, order_id) in fct_reviews. Returns duplicates.
select review_id, order_id, count(*) as n from {{ ref('fct_reviews') }} group by review_id, order_id having count(*) > 1
