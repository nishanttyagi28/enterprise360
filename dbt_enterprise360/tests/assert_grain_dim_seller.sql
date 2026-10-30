-- grain: one row per (seller_id) in dim_seller. Returns duplicates.
select seller_id, count(*) as n from {{ ref('dim_seller') }} group by seller_id having count(*) > 1
