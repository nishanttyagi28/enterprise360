-- Order lines rolled up to ORDER grain so they can be joined to orders/payments without fan-out.
select
    order_id,
    count(*)                                  as item_count,
    count(distinct product_id)                as distinct_products,
    count(distinct seller_id)                 as distinct_sellers,
    sum(item_price)                           as items_price_total,
    sum(freight_value)                        as freight_total,
    sum(item_price + freight_value)           as items_gross_total
from {{ ref('stg_olist__order_items') }}
group by order_id
