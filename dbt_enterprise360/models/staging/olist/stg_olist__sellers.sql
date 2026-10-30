with src as (select * from {{ source('olist', 'olist_sellers') }}),
deduped as ({{ dedupe('src', ['seller_id']) }})
select
    trim(seller_id)                                  as seller_id,
    {{ zip_prefix('seller_zip_code_prefix') }}       as seller_zip_prefix,
    lower({{ clean_text('seller_city') }})           as seller_city,
    upper({{ clean_text('seller_state') }})          as seller_state,
    _ingested_at
from deduped
