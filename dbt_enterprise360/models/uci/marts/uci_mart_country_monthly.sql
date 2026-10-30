-- Grain: month x invoice country (country as recorded per invoice; decision D5). GBP.
select
    date_trunc('month', invoice_ts)::date                            as month_start,
    uci_country_sk,
    country,
    count(*) filter (where not is_cancellation)                      as sales_invoices,
    count(*) filter (where is_cancellation)                          as cancellation_invoices,
    count(distinct customer_id) filter (where not is_cancellation)   as active_customers,
    sum(gross_product_sales)                                         as gross_product_sales,
    sum(product_cancellations)                                       as product_cancellations,
    sum(discounts)                                                   as discounts,
    sum(net_sales_proxy_gbp)                                         as net_sales_proxy_gbp,
    sum(postage)                                                     as postage,
    'GBP'::char(3)                                                   as currency
from {{ ref('uci_fct_invoices') }}
group by 1, 2, 3
