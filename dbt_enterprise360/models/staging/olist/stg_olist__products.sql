with src as (select * from {{ source('olist', 'olist_products') }}),
deduped as ({{ dedupe('src', ['product_id']) }})
select
    trim(product_id)                                          as product_id,
    lower({{ clean_text('product_category_name') }})          as category_name_pt,
    -- source column names are misspelled ("lenght"); fixed here, once
    ({{ clean_text('product_name_lenght') }})::integer        as product_name_length,
    ({{ clean_text('product_description_lenght') }})::integer as product_description_length,
    ({{ clean_text('product_photos_qty') }})::integer         as product_photos_qty,
    ({{ clean_text('product_weight_g') }})::integer           as product_weight_g,
    ({{ clean_text('product_length_cm') }})::integer          as product_length_cm,
    ({{ clean_text('product_height_cm') }})::integer          as product_height_cm,
    ({{ clean_text('product_width_cm') }})::integer           as product_width_cm,
    _ingested_at
from deduped
