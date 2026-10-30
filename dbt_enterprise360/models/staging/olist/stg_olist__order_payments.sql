with src as (select * from {{ source('olist', 'olist_order_payments') }}),
deduped as ({{ dedupe('src', ['order_id', 'payment_sequential']) }})
select
    trim(order_id)                                         as order_id,
    ({{ clean_text('payment_sequential') }})::smallint     as payment_sequential,
    lower({{ clean_text('payment_type') }})                as payment_type,
    ({{ clean_text('payment_installments') }})::smallint   as payment_installments,
    ({{ clean_text('payment_value') }})::numeric(12, 2)    as payment_value,
    _ingested_at
from deduped
