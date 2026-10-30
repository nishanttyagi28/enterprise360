-- Grain: month x StockCode, product lines only (line_type='product'). GBP.
select
    date_trunc('month', f.invoice_ts)::date                                     as month_start,
    f.uci_product_sk,
    f.stock_code,
    p.description,
    count(distinct f.invoice) filter (where not f.is_cancellation)              as sales_invoices,
    coalesce(sum(f.quantity) filter (where not f.is_cancellation), 0)           as units_sold,
    coalesce(-sum(f.quantity) filter (where f.is_cancellation), 0)              as units_cancelled,
    coalesce(sum(f.line_value) filter (where not f.is_cancellation), 0)         as gross_sales,
    coalesce(sum(f.line_value) filter (where f.is_cancellation), 0)             as cancellations,
    sum(f.line_value)                                                           as net_sales_proxy_gbp,
    round(-coalesce(sum(f.line_value) filter (where f.is_cancellation), 0)
          / nullif(sum(f.line_value) filter (where not f.is_cancellation), 0), 4) as cancellation_value_rate,
    'GBP'::char(3)                                                              as currency
from {{ ref('uci_fct_invoice_lines') }} f
join {{ ref('uci_dim_product') }} p on p.uci_product_sk = f.uci_product_sk
where f.line_type = 'product'
group by 1, 2, 3, 4
