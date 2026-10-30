-- One review per order (latest by creation, then answer time). Source has 547 orders with >1 review;
-- order-level CSAT (KPI_REVIEW_SCORE, KPI_LOW_REVIEW_RATE) must not double count them.
select order_id, review_id, review_score, review_created_at, review_answered_at
from (
    select r.*,
           row_number() over (
               partition by order_id
               order by review_created_at desc, review_answered_at desc nulls last, review_id
           ) as rn
    from {{ ref('stg_olist__order_reviews') }} r
) x
where rn = 1
