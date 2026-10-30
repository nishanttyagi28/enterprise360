-- Grain: mql_id (one row per marketing-qualified lead). Closed-deal attributes come from a 1:1 left
-- join on mql_id (closed_deals.mql_id is tested unique), so no fan-out. Cohort = first_contact_month.
-- days_to_close = won_date::date - first_contact_date (calendar days); negative only for source anomalies
-- (flagged by is_won_before_first_contact and excluded from duration statistics in marts).
select
    {{ dbt_utils.generate_surrogate_key(['l.mql_id']) }}                   as lead_sk,
    l.mql_id,
    o.origin_sk,
    coalesce(l.origin, 'not_recorded')                                     as origin,
    l.landing_page_id,
    l.first_contact_date,
    to_char(l.first_contact_date, 'YYYYMMDD')::int                         as first_contact_date_key,
    date_trunc('month', l.first_contact_date)::date                        as first_contact_month,
    d.mql_id is not null                                                   as is_closed,
    d.won_date,                                                            -- timestamp
    to_char(d.won_date, 'YYYYMMDD')::int                                   as won_date_key,
    (d.won_date::date - l.first_contact_date)                              as days_to_close,
    coalesce(d.won_date::date < l.first_contact_date, false)                 as is_won_before_first_contact
from {{ ref('stg_olist__marketing_qualified_leads') }} l
inner join {{ ref('dim_lead_origin') }} o on o.origin = coalesce(l.origin, 'not_recorded')
left join {{ ref('stg_olist__closed_deals') }} d on d.mql_id = l.mql_id
