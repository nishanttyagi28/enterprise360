{{ config(materialized='table') }}
-- Geolocation collapsed to ONE row per zip prefix (1M points -> ~19k prefixes) BEFORE any join;
-- a raw join to customers/sellers would multiply rows. Points outside Brazil's bounding box are
-- dropped (known bad coordinates). Centroid = MEDIAN lat/lng of the remaining points (robust to
-- residual bad points inside the bbox; lat and lng medians are taken independently); city/state =
-- most frequent spelling (mode), which neutralises accent/typo variants.
select
    zip_prefix,
    (percentile_cont(0.5) within group (order by lat))::numeric(9, 6) as lat,
    (percentile_cont(0.5) within group (order by lng))::numeric(9, 6) as lng,
    mode() within group (order by city)                        as city,
    mode() within group (order by state)                       as state,
    count(*)                                                   as geo_point_count
from {{ ref('stg_olist__geolocation') }}
where is_within_brazil
group by zip_prefix
