-- Grain: zip_prefix (5-digit Brazilian CEP prefix). Universe = every prefix seen in geolocation,
-- customers or sellers, so every fact FK resolves (157 customer / 7 seller prefixes have no
-- geolocation points -> coordinates NULL, has_coordinates=false; city/state from the entity rows).
with entity_places as (
    select customer_zip_prefix as zip_prefix, customer_city as city, customer_state as state
    from {{ ref('stg_olist__customers') }}
    union all
    select seller_zip_prefix, seller_city, seller_state from {{ ref('stg_olist__sellers') }}
),
entity_mode as (
    select zip_prefix,
           mode() within group (order by city)  as city,
           mode() within group (order by state) as state
    from entity_places
    where zip_prefix is not null
    group by zip_prefix
),
all_prefixes as (
    select zip_prefix from {{ ref('int_olist__zip_prefix_centroid') }}
    union
    select zip_prefix from entity_mode
)
select
    {{ dbt_utils.generate_surrogate_key(['p.zip_prefix']) }}   as geography_sk,
    p.zip_prefix,
    coalesce(g.city, e.city)                                   as city,
    coalesce(g.state, e.state)                                 as state,
    g.lat,
    g.lng,
    coalesce(g.geo_point_count, 0)                             as geo_point_count,
    g.zip_prefix is not null                                   as has_coordinates
from all_prefixes p
left join {{ ref('int_olist__zip_prefix_centroid') }} g on g.zip_prefix = p.zip_prefix
left join entity_mode e on e.zip_prefix = p.zip_prefix
