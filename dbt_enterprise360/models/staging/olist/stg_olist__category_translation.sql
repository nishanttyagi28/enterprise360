with src as (select * from {{ source('olist', 'olist_product_category_name_translation') }}),
deduped as ({{ dedupe('src', ['product_category_name']) }})
select
    lower({{ clean_text('product_category_name') }})          as category_name_pt,
    lower({{ clean_text('product_category_name_english') }})  as category_name_en,
    _ingested_at
from deduped
