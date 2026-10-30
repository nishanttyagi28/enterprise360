-- Grain: acquisition cohort month x months since first order. Customers = customer_unique_id.
-- KPI_CUSTOMER_RETENTION is PARTIAL: Olist's repeat base is tiny (~3% repeat), so rates are unstable.
with activity as (
    select distinct c.customer_sk, c.first_order_month as cohort_month,
           date_trunc('month', o.purchased_at)::date as active_month
    from {{ ref('fct_orders') }} o
    inner join {{ ref('dim_customer') }} c on c.customer_sk = o.customer_sk
),
cohort_size as (
    select first_order_month as cohort_month, count(*) as cohort_customers
    from {{ ref('dim_customer') }} group by 1
)
select
    a.cohort_month,
    ((extract(year from age(a.active_month, a.cohort_month)) * 12)
      + extract(month from age(a.active_month, a.cohort_month)))::int  as months_since_first_order,
    a.active_month,
    s.cohort_customers,
    count(*)                                                         as active_customers,
    round(count(*)::numeric / s.cohort_customers, 4)                 as retention_rate
from activity a
inner join cohort_size s on s.cohort_month = a.cohort_month
group by 1, 2, 3, 4
