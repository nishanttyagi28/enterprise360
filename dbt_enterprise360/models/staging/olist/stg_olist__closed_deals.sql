-- Grain: mql_id (one closed deal per lead; source has no deal id). Seller-declared attributes are
-- sparse (has_company/has_gtin/average_stock ~92% null) and self-reported, not verified by Olist.
with src as (select * from {{ source('olist_funnel', 'olist_closed_deals') }}),
deduped as ({{ dedupe('src', ['mql_id']) }})
select
    trim(mql_id)                                             as mql_id,
    {{ clean_text('seller_id') }}                            as seller_id,
    {{ clean_text('sdr_id') }}                               as sdr_id,
    {{ clean_text('sr_id') }}                                as sr_id,
    {{ clean_text('won_date') }}::timestamp                  as won_date,
    lower({{ clean_text('business_segment') }})              as business_segment,
    lower({{ clean_text('lead_type') }})                     as lead_type,
    lower({{ clean_text('lead_behaviour_profile') }})        as lead_behaviour_profile,
    case lower({{ clean_text('has_company') }}) when 'true' then true when 'false' then false end as has_company,
    case lower({{ clean_text('has_gtin') }}) when 'true' then true when 'false' then false end    as has_gtin,
    lower({{ clean_text('average_stock') }})                 as average_stock,
    lower({{ clean_text('business_type') }})                 as business_type,
    {{ clean_text('declared_product_catalog_size') }}::numeric::integer as declared_product_catalog_size,
    {{ clean_text('declared_monthly_revenue') }}::numeric(18,2)        as declared_monthly_revenue_brl,
    _ingested_at
from deduped
