-- Grain: one deduplicated invoice line (_source_file, _source_line_no). GBP. Signed measures:
-- cancellation lines (Invoice 'C…') carry negative quantity/value in the SAME fact, so
-- net = gross + cancellations is additive. No natural line key exists (11,162 Invoice x StockCode
-- pairs repeat), hence the source position key. Independent domain: no Olist joins.
select
    {{ dbt_utils.generate_surrogate_key(['_source_file', '_source_line_no']) }}   as uci_invoice_line_sk,
    {{ dbt_utils.generate_surrogate_key(['invoice']) }}                            as uci_invoice_sk,
    invoice,
    stock_code,
    {{ dbt_utils.generate_surrogate_key(['stock_code']) }}                         as uci_product_sk,
    customer_id,
    -- blank Customer ID (22.8% of lines) -> unknown member (customer_id -1 in uci_dim_customer)
    {{ dbt_utils.generate_surrogate_key(["coalesce(customer_id, -1)"]) }}          as uci_customer_sk,
    customer_id is not null                                                        as has_customer,
    country,
    {{ dbt_utils.generate_surrogate_key(['country']) }}                            as uci_country_sk,
    {{ date_key('invoice_ts') }}                                                   as invoice_date_key,
    invoice_ts,
    quantity,
    unit_price,
    line_value,
    is_cancellation,
    line_type,
    line_type = 'product'                                                          as is_product_line,
    'GBP'::char(3)                                                                 as currency,
    description,
    _source_file,
    _source_line_no
from {{ ref('int_uci__invoice_lines_classified') }}
