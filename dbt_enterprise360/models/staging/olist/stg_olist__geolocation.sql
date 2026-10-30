-- Point-level (NOT one row per zip). No dedupe: duplicate points are legitimate repeated observations
-- and are collapsed by aggregation in int_olist__zip_prefix_centroid.
select
    {{ zip_prefix('geolocation_zip_code_prefix') }}               as zip_prefix,
    ({{ clean_text('geolocation_lat') }})::numeric(9, 6)          as lat,
    ({{ clean_text('geolocation_lng') }})::numeric(9, 6)          as lng,
    lower({{ clean_text('geolocation_city') }})                   as city,
    upper({{ clean_text('geolocation_state') }})                  as state,
    ({{ clean_text('geolocation_lat') }})::numeric between {{ var('brazil_lat_min') }} and {{ var('brazil_lat_max') }}
      and ({{ clean_text('geolocation_lng') }})::numeric between {{ var('brazil_lng_min') }} and {{ var('brazil_lng_max') }}
                                                                  as is_within_brazil,
    _ingested_at
from {{ source('olist', 'olist_geolocation') }}
