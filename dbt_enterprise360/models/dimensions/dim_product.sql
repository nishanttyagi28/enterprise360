-- Grain: product_id. 610 products have no category -> 'unknown' member; 2 categories have no
-- English translation (pc_gamer, portateis_cozinha...) -> fall back to the Portuguese name, flagged.
select
    {{ dbt_utils.generate_surrogate_key(['p.product_id']) }}           as product_sk,
    p.product_id,
    coalesce(p.category_name_pt, 'unknown')                            as category_name_pt,
    coalesce(t.category_name_en, p.category_name_pt, 'unknown')        as category_name_en,
    t.category_name_en is not null                                     as is_category_translated,
    p.product_name_length,
    p.product_description_length,
    p.product_photos_qty,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm,
    p.product_length_cm * p.product_height_cm * p.product_width_cm     as product_volume_cm3
from {{ ref('stg_olist__products') }} p
left join {{ ref('stg_olist__category_translation') }} t on t.category_name_pt = p.category_name_pt
