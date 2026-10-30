-- Grain: first-purchase month x months since first purchase. Identified customers, sales invoices.
with activity as (
    select distinct c.customer_id, c.first_purchase_month as cohort_month,
           date_trunc('month', i.invoice_ts)::date as active_month
    from {{ ref('uci_fct_invoices') }} i
    join {{ ref('uci_dim_customer') }} c on c.uci_customer_sk = i.uci_customer_sk
    where c.is_identified and not i.is_cancellation
),
cohort_size as (
    select first_purchase_month as cohort_month, count(*) as cohort_customers
    from {{ ref('uci_dim_customer') }} where is_identified and first_purchase_month is not null group by 1
)
select
    a.cohort_month,
    ((extract(year from age(a.active_month, a.cohort_month)) * 12)
      + extract(month from age(a.active_month, a.cohort_month)))::int  as months_since_first_purchase,
    a.active_month,
    s.cohort_customers,
    count(*)                                                         as active_customers,
    round(count(*)::numeric / s.cohort_customers, 4)                 as retention_rate
from activity a join cohort_size s using (cohort_month)
group by 1, 2, 3, 4
