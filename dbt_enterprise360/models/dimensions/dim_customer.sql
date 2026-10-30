-- Grain: customer_unique_id (the real person). Olist issues a fresh customer_id per order, so keying
-- on customer_id would make every order a "new customer" and break KPI_REPEAT_RATE/NEW_CUSTOMERS.
-- Attributes (location) = those on the person's LATEST order (SCD1; history is not needed by any KPI).
with person_orders as (
    select m.customer_unique_id, m.customer_sk, m.customer_zip_prefix, m.customer_city,
           m.customer_state, o.order_id, o.purchased_at
    from {{ ref('int_olist__customer_order_map') }} m
    inner join {{ ref('stg_olist__orders') }} o on o.customer_id = m.customer_id
),
latest as (
    select distinct on (customer_unique_id) *
    from person_orders
    order by customer_unique_id, purchased_at desc, order_id
),
lifetime as (
    select customer_unique_id,
           min(purchased_at)        as first_order_at,
           max(purchased_at)        as last_order_at,
           count(distinct order_id) as lifetime_orders
    from person_orders
    group by customer_unique_id
)
select
    l.customer_sk,
    l.customer_unique_id,
    l.customer_zip_prefix                                          as zip_prefix,
    {{ dbt_utils.generate_surrogate_key(['l.customer_zip_prefix']) }} as geography_sk,
    l.customer_city                                                as city,
    l.customer_state                                               as state,
    t.first_order_at,
    t.first_order_at::date                                         as first_order_date,
    date_trunc('month', t.first_order_at)::date                    as first_order_month,
    t.last_order_at,
    t.lifetime_orders,
    t.lifetime_orders >= 2                                         as is_repeat_customer
from latest l
inner join lifetime t using (customer_unique_id)
