-- Grain: product category (English, with pt fallback) x purchase month. Line-level measures only:
-- order-level measures (reviews, payments) are NOT allocated to categories, because an order can
-- span categories and any allocation rule would be an invented assumption.
select
    date_trunc('month', f.purchased_at)::date                 as month_start,
    p.category_name_en,
    p.category_name_pt,
    p.is_category_translated,
    count(distinct f.order_id)                                as orders,
    count(*)                                                  as order_lines,
    sum(f.item_price)::numeric(14, 2)                         as gmv,
    coalesce(sum(f.item_price) filter (where not f.is_canceled), 0)::numeric(14, 2) as net_gmv,
    sum(f.freight_value)::numeric(14, 2)                      as freight_value,
    round(avg(f.item_price), 2)                               as avg_item_price,
    count(distinct f.seller_sk)                               as active_sellers
from {{ ref('fct_order_items') }} f
inner join {{ ref('dim_product') }} p on p.product_sk = f.product_sk
group by 1, 2, 3, 4
