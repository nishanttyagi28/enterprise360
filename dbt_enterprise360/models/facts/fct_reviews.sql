-- Grain: (review_id, order_id). review_id is NOT unique alone: the same review text is attached to
-- several orders (789 ids). Keep both keys; is_latest_for_order marks the row used for order CSAT.
select
    {{ dbt_utils.generate_surrogate_key(['r.review_id', 'r.order_id']) }} as review_sk,
    {{ dbt_utils.generate_surrogate_key(['r.order_id']) }}                as order_sk,
    r.review_id,
    r.order_id,
    {{ date_key('r.review_created_at') }}                                 as review_created_date_key,
    r.review_score,
    r.review_score <= 2                                                   as is_low_score,
    r.review_title is not null or r.review_message is not null           as has_comment,
    r.review_created_at,
    r.review_answered_at,
    round(extract(epoch from (r.review_answered_at - r.review_created_at)) / 3600.0, 2) as hours_to_answer,
    l.review_id is not null                                               as is_latest_for_order
from {{ ref('stg_olist__order_reviews') }} r
left join {{ ref('int_olist__order_review_latest') }} l
    on l.order_id = r.order_id and l.review_id = r.review_id
