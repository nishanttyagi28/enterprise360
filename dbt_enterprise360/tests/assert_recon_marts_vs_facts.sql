-- KPI_RECON_VARIANCE = 0 for the headline marts: totals in marts equal the facts they summarise.
with f as (
    select (select count(*) from {{ ref('fct_orders') }})                  as orders,
           (select sum(item_price) from {{ ref('fct_order_items') }})      as gmv,
           (select sum(payment_value) from {{ ref('fct_payments') }})      as pay
),
checks as (
    select 'mart_sales_daily' as mart, sum(orders) as orders, sum(gmv) as gmv, sum(payment_value) as pay
    from {{ ref('mart_sales_daily') }}
    union all
    select 'mart_business_overview_monthly', sum(orders), sum(gmv), sum(payment_value)
    from {{ ref('mart_business_overview_monthly') }}
    union all
    select 'mart_sales_by_seller_monthly', null, sum(gmv), null from {{ ref('mart_sales_by_seller_monthly') }}
    union all
    select 'mart_sales_by_category_monthly', null, sum(gmv), null from {{ ref('mart_sales_by_category_monthly') }}
    union all
    select 'mart_operations_delivery_performance', sum(orders), null, null
    from {{ ref('mart_operations_delivery_performance') }}
)
select c.* from checks c, f
where (c.orders is not null and c.orders <> f.orders)
   or (c.gmv is not null and c.gmv <> f.gmv)
   or (c.pay is not null and c.pay <> coalesce(f.pay, 0))
