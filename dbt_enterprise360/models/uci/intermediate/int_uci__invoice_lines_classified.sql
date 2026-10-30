-- line_type per line. Order of rules: StockCode class seed (postage, fees, discount, manual, ...)
-- -> 'A' invoices = bad_debt -> remaining price-0 lines = stock_adjustment (incl. the 3,457
-- negative-quantity write-offs; kept with value 0, decision D4) -> product.
with codes as (
    -- classify each distinct StockCode once (5k codes) instead of per line (1M lines)
    select c.stock_code,
           (select s.line_type from {{ ref('uci_stockcode_class') }} s
            where upper(c.stock_code) like s.stock_code_pattern
            order by s.priority, length(s.stock_code_pattern) desc limit 1) as seed_line_type
    from (select distinct stock_code from {{ ref('stg_uci__invoice_lines') }}) c
),
cls as (
    select l.*, codes.seed_line_type
    from {{ ref('stg_uci__invoice_lines') }} l
    join codes using (stock_code)
)
select
    cls.*,
    case
        when seed_line_type is not null then seed_line_type
        when invoice like 'A%'          then 'bad_debt'
        when invoice not like 'C%' and quantity < 0 and unit_price = 0 then 'stock_writeoff'
        when unit_price <= 0            then 'zero_price'
        else 'product'
    end                                         as line_type,
    (quantity * unit_price)::numeric(14, 3)     as line_value
from cls
