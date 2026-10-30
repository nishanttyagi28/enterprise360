with src as (select * from {{ source('olist', 'olist_order_reviews') }}),
deduped as ({{ dedupe('src', ['review_id', 'order_id']) }})
select
    trim(review_id)                                     as review_id,
    trim(order_id)                                      as order_id,
    ({{ clean_text('review_score') }})::smallint        as review_score,
    {{ clean_text('review_comment_title') }}            as review_title,
    {{ clean_text('review_comment_message') }}          as review_message,
    {{ to_ts('review_creation_date') }}                 as review_created_at,
    {{ to_ts('review_answer_timestamp') }}              as review_answered_at,
    _ingested_at
from deduped
