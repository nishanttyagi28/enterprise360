{{ config(severity='warn') }}
-- Decision D1: exact duplicate lines within one file are dropped; this lists them (WARN = logged).
select _source_file, _source_line_no, invoice, stock_code
from {{ ref('stg_uci__invoice_lines_all') }} where is_exact_duplicate
