with src as (select * from {{ source('olist', 'olist_order_items') }}),
deduped as ({{ dedupe('src', ['order_id', 'order_item_id']) }})
select
    trim(order_id)                                    as order_id,
    ({{ clean_text('order_item_id') }})::smallint     as order_item_id,
    trim(product_id)                                  as product_id,
    trim(seller_id)                                   as seller_id,
    {{ to_ts('shipping_limit_date') }}                as shipping_limit_at,
    ({{ clean_text('price') }})::numeric(12, 2)       as item_price,
    ({{ clean_text('freight_value') }})::numeric(12, 2) as freight_value,
    _ingested_at
from deduped
