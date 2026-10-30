{{ config(severity='warn') }}
-- DQ: exact duplicate lines remaining after staging dedup. Line identity = ALL 8 source columns
-- (Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country), i.e. the
-- columns DE's _row_hash covers in stg_uci__invoice_lines_all; lineage (_source_file,
-- _source_line_no, _row_hash, _ingested_at) excluded. Must return 0 rows after D1 dedup + overlap rule.
-- (Previous version omitted description/country and flagged 2 lines that differ only in description.)
select invoice, stock_code, description, quantity, invoice_ts, unit_price, customer_id, country, count(*) as n
from {{ ref('stg_uci__invoice_lines') }}
group by invoice, stock_code, description, quantity, invoice_ts, unit_price, customer_id, country
having count(*) > 1
