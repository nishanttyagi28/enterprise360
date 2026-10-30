-- Grain: seller x purchase month. Built only from fct_order_items (+ dims, many-to-one).
select
    date_trunc('month', f.purchased_at)::date                 as month_start,
    f.seller_sk,
    s.seller_id,
    s.state                                                   as seller_state,
    s.city                                                    as seller_city,
    count(distinct f.order_id)                                as orders,
    count(*)                                                  as order_lines,
    sum(f.item_price)::numeric(14, 2)                         as gmv,
    coalesce(sum(f.item_price) filter (where not f.is_canceled), 0)::numeric(14, 2) as net_gmv,
    sum(f.freight_value)::numeric(14, 2)                      as freight_value,
    count(distinct f.product_sk)                              as distinct_products
from {{ ref('fct_order_items') }} f
inner join {{ ref('dim_seller') }} s on s.seller_sk = f.seller_sk
group by 1, 2, 3, 4, 5
