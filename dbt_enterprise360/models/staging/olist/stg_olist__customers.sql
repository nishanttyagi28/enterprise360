with src as (select * from {{ source('olist', 'olist_customers') }}),
deduped as ({{ dedupe('src', ['customer_id']) }})
select
    trim(customer_id)                                  as customer_id,
    trim(customer_unique_id)                           as customer_unique_id,
    {{ zip_prefix('customer_zip_code_prefix') }}       as customer_zip_prefix,
    lower({{ clean_text('customer_city') }})           as customer_city,
    upper({{ clean_text('customer_state') }})          as customer_state,
    _ingested_at
from deduped
