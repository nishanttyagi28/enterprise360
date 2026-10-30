-- Deduplicated invoice lines (grain: _source_file x _source_line_no of the surviving copy).
select
    _source_file, _source_line_no, _row_hash, _ingested_at,
    invoice, stock_code, description, quantity, invoice_ts, unit_price, customer_id, country,
    invoice like 'C%'                                   as is_cancellation
from {{ ref('stg_uci__invoice_lines_all') }}
where not is_exact_duplicate and not is_superseded
