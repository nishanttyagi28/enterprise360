-- Grain: Customer ID (+ unknown member customer_id = -1 for blank IDs, so every line joins).
-- primary_country = country with most invoices (decision D5: facts keep per-invoice country).
with inv as (select * from {{ ref('uci_fct_invoices') }} where has_customer),
countries as (
    select distinct on (customer_id) customer_id, country
    from (select customer_id, country, count(*) n, max(invoice_ts) last_ts from inv group by 1, 2) x
    order by customer_id, n desc, last_ts desc
),
agg as (
    select customer_id,
           count(distinct country)                                  as country_count,
           min(invoice_ts) filter (where not is_cancellation)       as first_purchase_ts,
           max(invoice_ts) filter (where not is_cancellation)       as last_purchase_ts,
           count(*) filter (where not is_cancellation)              as sales_invoices,
           count(*) filter (where is_cancellation)                  as cancellation_invoices
    from inv group by 1
)
select
    {{ dbt_utils.generate_surrogate_key(['a.customer_id']) }}  as uci_customer_sk,
    a.customer_id,
    true                                                       as is_identified,
    c.country                                                  as primary_country,
    a.country_count > 1                                        as is_multi_country,
    a.first_purchase_ts,
    date_trunc('month', a.first_purchase_ts)::date             as first_purchase_month,
    a.last_purchase_ts,
    a.sales_invoices,
    a.cancellation_invoices,
    a.sales_invoices >= 2                                      as is_repeat_customer
from agg a join countries c using (customer_id)
union all
select {{ dbt_utils.generate_surrogate_key(["-1"]) }}, -1, false, null, false, null, null, null, null, null, false
