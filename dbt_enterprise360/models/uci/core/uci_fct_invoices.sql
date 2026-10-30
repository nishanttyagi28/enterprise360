-- Grain: invoice. Rolled up from uci_fct_invoice_lines (no other inputs -> no fan-out).
-- Net Sales (proxy) = product lines + discount lines (signed; C invoices negative). Operational proxy:
-- no tax, cost or returns ledger. Postage/fees/other non-product lines reported separately.
select
    uci_invoice_sk,
    invoice,
    min(invoice_ts)                                                              as invoice_ts,  -- 83 invoices span >1 minute
    {{ date_key('min(invoice_ts)') }}                                            as invoice_date_key,
    max(customer_id)                                                             as customer_id, -- unique per invoice (profiled)
    max(uci_customer_sk)                                                         as uci_customer_sk,
    bool_or(has_customer)                                                        as has_customer,
    max(country)                                                                 as country,     -- unique per invoice (profiled)
    max(uci_country_sk)                                                          as uci_country_sk,
    bool_or(is_cancellation)                                                     as is_cancellation,
    count(*)                                                                     as line_count,
    count(*) filter (where is_product_line)                                      as product_line_count,
    coalesce(sum(quantity) filter (where is_product_line), 0)                    as product_units,
    coalesce(sum(line_value) filter (where is_product_line and not is_cancellation), 0) as gross_product_sales,
    coalesce(sum(line_value) filter (where is_product_line and is_cancellation), 0)     as product_cancellations,
    coalesce(sum(line_value) filter (where line_type = 'discount'), 0)           as discounts,
    coalesce(sum(line_value) filter (where line_type in ('product', 'discount')), 0) as net_sales_proxy_gbp,
    coalesce(sum(line_value) filter (where line_type = 'postage'), 0)            as postage,
    coalesce(sum(line_value) filter (where line_type = 'fee'), 0)                as fees,
    coalesce(sum(line_value) filter (where line_type not in ('product', 'discount', 'postage', 'fee')), 0) as other_non_product,
    sum(line_value)                                                              as invoiced_value_gbp, -- all lines
    'GBP'::char(3)                                                               as currency
from {{ ref('uci_fct_invoice_lines') }}
group by uci_invoice_sk, invoice
