-- Grain: seller_id (SCD1 here; history is captured by snapshots/snap_olist__sellers).
select
    {{ dbt_utils.generate_surrogate_key(['seller_id']) }}          as seller_sk,
    seller_id,
    seller_zip_prefix                                              as zip_prefix,
    {{ dbt_utils.generate_surrogate_key(['seller_zip_prefix']) }}  as geography_sk,
    seller_city                                                    as city,
    seller_state                                                   as state
from {{ ref('stg_olist__sellers') }}
