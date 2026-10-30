-- Grain: purchase date. Each fact is aggregated to day SEPARATELY and the aggregates are joined on
-- date_key (1:1) -> no items x payments fan-out. Column names follow governance/kpi_dictionary.
-- Ratios are stored with their numerator/denominator so Power BI can re-aggregate correctly.
with bounds as (
    select min(purchase_date_key) as lo, max(purchase_date_key) as hi from {{ ref('fct_orders') }}
),
days as (
    select d.date_key, d.date_day from {{ ref('dim_date') }} d, bounds b
    where d.date_key between b.lo and b.hi
),
orders as (
    select purchase_date_key as date_key,
           count(*)                                         as orders,               -- KPI_ORDERS
           count(*) filter (where has_items)                as orders_with_items,
           count(*) filter (where is_canceled)              as canceled_orders,
           count(distinct customer_sk)                      as active_customers      -- KPI_ACTIVE_CUSTOMERS (non-additive)
    from {{ ref('fct_orders') }} group by 1
),
items as (
    select purchase_date_key as date_key,
           count(*)                                              as order_lines,
           sum(item_quantity)                                    as units,
           sum(item_price)                                       as gmv,              -- KPI_GMV
           sum(item_price) filter (where not is_canceled)        as net_gmv,          -- KPI_NET_GMV
           sum(freight_value)                                    as freight_value,    -- KPI_FREIGHT
           sum(item_price + freight_value)                       as gmv_incl_freight  -- KPI_GMV_INCL_FREIGHT
    from {{ ref('fct_order_items') }} group by 1
),
payments as (
    select purchase_date_key as date_key, sum(payment_value) as payment_value       -- KPI_PAYMENT_VALUE
    from {{ ref('fct_payments') }} group by 1
)
select
    d.date_key,
    d.date_day,
    coalesce(o.orders, 0)                                   as orders,
    coalesce(o.orders_with_items, 0)                        as orders_with_items,
    coalesce(o.canceled_orders, 0)                          as canceled_orders,
    coalesce(o.active_customers, 0)                         as active_customers,
    coalesce(i.order_lines, 0)                              as order_lines,
    coalesce(i.units, 0)                                    as units,
    coalesce(i.gmv, 0)::numeric(14, 2)                      as gmv,
    coalesce(i.net_gmv, 0)::numeric(14, 2)                  as net_gmv,
    coalesce(i.freight_value, 0)::numeric(14, 2)            as freight_value,
    coalesce(i.gmv_incl_freight, 0)::numeric(14, 2)         as gmv_incl_freight,
    coalesce(p.payment_value, 0)::numeric(14, 2)            as payment_value,
    round(i.gmv / nullif(o.orders_with_items, 0), 2)        as aov,               -- KPI_AOV
    round(i.order_lines::numeric / nullif(o.orders_with_items, 0), 3) as items_per_order, -- KPI_ITEMS_PER_ORDER
    round(o.canceled_orders::numeric / nullif(o.orders, 0), 4)       as cancel_rate,     -- KPI_CANCEL_RATE
    round(i.freight_value / nullif(i.gmv, 0), 4)                     as freight_share    -- KPI_FREIGHT_SHARE
from days d
left join orders o on o.date_key = d.date_key
left join items i on i.date_key = d.date_key
left join payments p on p.date_key = d.date_key
