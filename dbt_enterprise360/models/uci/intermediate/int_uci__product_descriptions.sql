-- Description history per StockCode (up to 9 variants): the SCD context behind uci_dim_product,
-- which carries the most frequent description as an SCD1 attribute (no effective dates in source).
select
    stock_code,
    description,
    count(*)            as line_count,
    min(invoice_ts)     as first_seen_at,
    max(invoice_ts)     as last_seen_at
from {{ ref('stg_uci__invoice_lines') }}
where description is not null
group by 1, 2
