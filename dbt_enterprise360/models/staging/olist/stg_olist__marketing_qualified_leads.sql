-- Grain: mql_id (one marketing-qualified lead). origin: null -> null here (unknown member is assigned in
-- dim_lead_origin); the literal source value 'unknown' is kept as its own origin.
with src as (select * from {{ source('olist_funnel', 'olist_marketing_qualified_leads') }}),
deduped as ({{ dedupe('src', ['mql_id']) }})
select
    trim(mql_id)                              as mql_id,
    {{ clean_text('first_contact_date') }}::date as first_contact_date,
    {{ clean_text('landing_page_id') }}       as landing_page_id,
    lower({{ clean_text('origin') }})         as origin,
    _ingested_at
from deduped
