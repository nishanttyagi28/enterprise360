-- Grain: lead acquisition origin (channel). Includes an unknown member 'not_recorded' for leads with
-- a null origin (distinct from the source value 'unknown'), so every lead has an origin key.
with origins as (
    select distinct coalesce(origin, 'not_recorded') as origin
    from {{ ref('stg_olist__marketing_qualified_leads') }}
    union
    select 'not_recorded'
)
select
    {{ dbt_utils.generate_surrogate_key(['origin']) }} as origin_sk,
    origin,
    origin = 'not_recorded'                            as is_unknown_member,
    case
        when origin in ('organic_search', 'paid_search') then 'search'
        when origin in ('social', 'display', 'other_publicities', 'email', 'referral') then 'marketing'
        when origin = 'direct_traffic' then 'direct'
        else 'other/unknown'
    end                                                as origin_group
from origins
