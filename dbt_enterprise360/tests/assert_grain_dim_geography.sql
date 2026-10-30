-- grain: one row per (zip_prefix) in dim_geography. Returns duplicates.
select zip_prefix, count(*) as n from {{ ref('dim_geography') }} group by zip_prefix having count(*) > 1
