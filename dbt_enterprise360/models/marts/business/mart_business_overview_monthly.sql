-- Grain: purchase month. Executive Command Center feed. Every measure is aggregated from its own
-- fact at month grain before the 1:1 month join (no fan-out). GMV is NOT revenue (KPI_GMV).
with orders as (
    select date_trunc('month', o.purchased_at)::date as month_start,
           count(*)                                            as orders,
           count(*) filter (where o.is_canceled)               as canceled_orders,
           count(distinct o.customer_sk)                       as active_customers,
           count(distinct o.customer_sk) filter (
               where date_trunc('month', o.purchased_at) = c.first_order_month) as new_customers,
           count(o.latest_review_score)                        as reviewed_orders,
           avg(o.latest_review_score)                          as avg_review_score,
           count(*) filter (where o.latest_review_score <= 2)  as low_review_orders
    from {{ ref('fct_orders') }} o
    inner join {{ ref('dim_customer') }} c on c.customer_sk = o.customer_sk
    group by 1
),
items as (
    select date_trunc('month', purchased_at)::date as month_start,
           sum(item_price) as gmv,
           sum(item_price) filter (where not is_canceled) as net_gmv,
           sum(freight_value) as freight_value
    from {{ ref('fct_order_items') }} group by 1
),
payments as (
    select date_trunc('month', o.purchased_at)::date as month_start, sum(p.payment_value) as payment_value
    from {{ ref('fct_payments') }} p
    inner join {{ ref('fct_orders') }} o on o.order_id = p.order_id   -- payment -> order is many:1
    group by 1
),
deliveries as (
    select date_trunc('month', purchased_at)::date as month_start,
           count(*) filter (where is_otd_eligible) as delivered_orders,
           count(*) filter (where is_otd_eligible and is_on_time) as on_time_orders
    from {{ ref('fct_deliveries') }} group by 1
),
months as (
    select month_start, is_complete_month, is_low_volume_month, is_reporting_month
    from {{ ref('int_olist__month_coverage') }}
)
select
    o.month_start,
    o.orders,
    o.active_customers,
    o.new_customers,                                                          -- KPI_NEW_CUSTOMERS
    o.active_customers - o.new_customers                                      as returning_customers,
    coalesce(i.gmv, 0)::numeric(14, 2)                                        as gmv,
    coalesce(i.net_gmv, 0)::numeric(14, 2)                                    as net_gmv,
    coalesce(i.freight_value, 0)::numeric(14, 2)                              as freight_value,
    coalesce(p.payment_value, 0)::numeric(14, 2)                              as payment_value,
    round((i.gmv - lag(i.gmv) over (order by o.month_start))
          / nullif(lag(i.gmv) over (order by o.month_start), 0), 4)           as gmv_growth_pct,  -- KPI_GMV_GROWTH (PARTIAL)
    round(o.canceled_orders::numeric / nullif(o.orders, 0), 4)                as cancel_rate,
    round(d.on_time_orders::numeric / nullif(d.delivered_orders, 0), 4)       as otd_rate,
    round(o.avg_review_score, 3)                                              as avg_review_score, -- KPI_REVIEW_SCORE
    round(o.low_review_orders::numeric / nullif(o.reviewed_orders, 0), 4)     as low_review_rate,  -- KPI_LOW_REVIEW_RATE
    o.canceled_orders,
    d.delivered_orders,
    d.on_time_orders,
    o.reviewed_orders,
    -- coverage flags from dim_date (KPI_GMV_GROWTH is PARTIAL: use is_reporting_month for trends)
    not dm.is_complete_month                                                  as is_partial_month,
    dm.is_complete_month,
    dm.is_low_volume_month,
    dm.is_reporting_month
from orders o
inner join months dm on dm.month_start = o.month_start
left join items i on i.month_start = o.month_start
left join payments p on p.month_start = o.month_start
left join deliveries d on d.month_start = o.month_start
