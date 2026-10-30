-- Grain: mql_id (one closed deal per lead). seller_sk is set ONLY when seller_id exists in dim_seller
-- (the e-commerce dataset covers orders to 2018-10, so most newly-won sellers never appear); unmatched
-- deals keep seller_id with seller_sk null. dim_seller is unique on seller_id -> the left join cannot fan out.
select
    {{ dbt_utils.generate_surrogate_key(['d.mql_id']) }}  as deal_sk,
    d.mql_id,
    f.lead_sk,
    f.origin_sk,
    f.origin,
    d.seller_id,
    s.seller_sk,
    s.seller_sk is not null                               as is_seller_in_olist_orders,
    d.sdr_id,
    d.sr_id,
    d.won_date,                                           -- timestamp
    f.won_date_key,
    date_trunc('month', d.won_date)::date                   as won_month,
    f.first_contact_date,
    f.first_contact_month,
    f.days_to_close,
    f.is_won_before_first_contact,
    d.business_segment,
    d.lead_type,
    d.lead_behaviour_profile,
    d.has_company,
    d.has_gtin,
    d.average_stock,
    d.business_type,
    d.declared_product_catalog_size,
    d.declared_monthly_revenue_brl                        -- self-declared descriptive attribute only
from {{ ref('stg_olist__closed_deals') }} d
inner join {{ ref('fct_leads') }} f on f.mql_id = d.mql_id
left join {{ ref('dim_seller') }} s on s.seller_id = d.seller_id
