-- grain: one row per (product_id) in dim_product. Returns duplicates.
select product_id, count(*) as n from {{ ref('dim_product') }} group by product_id having count(*) > 1
