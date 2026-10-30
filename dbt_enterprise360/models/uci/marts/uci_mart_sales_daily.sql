-- Grain: invoice date. Aggregated from uci_fct_invoices only (invoice grain -> no line fan-out).
-- GBP. Net Sales (proxy) = gross product sales + product cancellations + discounts (signed).
-- Operational proxy only (no tax/cost/returns ledger); postage and fees are reported separately.
with bounds as (select min(invoice_date_key) lo, max(invoice_date_key) hi from {{ ref('uci_fct_invoices') }}),
days as (
    select d.date_key, d.date_day from {{ ref('uci_dim_date') }} d, bounds b
    where d.date_key between b.lo and b.hi
),
inv as (
    select invoice_date_key as date_key,
           count(*) filter (where not is_cancellation)                              as sales_invoices,
           count(*) filter (where not is_cancellation and product_line_count > 0)   as sales_invoices_with_products,
           count(*) filter (where is_cancellation)                                  as cancellation_invoices,
           count(distinct customer_id) filter (where not is_cancellation)           as active_customers, -- identified only
           sum(product_units) filter (where not is_cancellation)                    as units_sold,
           sum(gross_product_sales)                                                  as gross_product_sales,
           sum(product_cancellations)                                                as product_cancellations,
           sum(discounts)                                                            as discounts,
           sum(net_sales_proxy_gbp)                                                  as net_sales_proxy_gbp,
           sum(postage)                                                              as postage,
           sum(fees)                                                                 as fees,
           sum(other_non_product)                                                    as other_non_product,
           sum(invoiced_value_gbp)                                                   as invoiced_value_gbp
    from {{ ref('uci_fct_invoices') }} group by 1
)
select
    d.date_key,
    d.date_day,
    coalesce(i.sales_invoices, 0)               as sales_invoices,
    coalesce(i.sales_invoices, 0)               as sales_invoice_count, -- AOV denominator (non-C invoices)
    coalesce(i.sales_invoices_with_products, 0) as sales_invoices_with_products,
    coalesce(i.cancellation_invoices, 0)        as cancellation_invoices,
    coalesce(i.active_customers, 0)             as active_customers,
    coalesce(i.units_sold, 0)                   as units_sold,
    coalesce(i.gross_product_sales, 0)          as gross_product_sales,
    coalesce(i.product_cancellations, 0)        as product_cancellations,
    coalesce(i.discounts, 0)                    as discounts,
    coalesce(i.net_sales_proxy_gbp, 0)          as net_sales_proxy_gbp,
    coalesce(i.postage, 0)                      as postage,
    coalesce(i.fees, 0)                         as fees,
    coalesce(i.other_non_product, 0)            as other_non_product,
    coalesce(i.invoiced_value_gbp, 0)           as invoiced_value_gbp,
    -- KPI_UCI_AOV = Net Sales (proxy) / sales (non-C) invoices. Daily ratio is NON-ADDITIVE: for month/any
    -- rollup compute sum(net_sales_proxy_gbp) / sum(sales_invoice_count), never sum/avg of aov_gbp.
    round(i.net_sales_proxy_gbp / nullif(i.sales_invoices, 0), 2)               as aov_gbp,
    round(i.gross_product_sales / nullif(i.sales_invoices_with_products, 0), 2) as gross_product_value_per_product_invoice_gbp,
    round(i.cancellation_invoices::numeric / nullif(i.sales_invoices + i.cancellation_invoices, 0), 4) as cancellation_invoice_rate,
    'GBP'::char(3)                              as currency
from days d left join inv i on i.date_key = d.date_key
