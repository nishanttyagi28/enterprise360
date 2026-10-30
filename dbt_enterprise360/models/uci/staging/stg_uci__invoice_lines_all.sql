{{ config(materialized='table') }}
-- Every raw line, typed, with the two dedup flags (nothing dropped here, so DQ can count drops):
--   is_exact_duplicate  : same _row_hash (all 8 source columns) as an earlier line of the SAME file
--                         -> dropped (decision D1), logged as a DQ warn.
--   is_superseded       : line of an earlier file dated at/after the first timestamp of a LATER file
--                         -> the later file restates that window (2010-12-01..09) -> keep the later
--                         file's copy only. Rule is by file window, not row matching, so it stays
--                         correct even if a restatement changed values (matching is tested, warn).
-- Timestamps: UK local time as recorded (zone not stated by the source); never shifted.
with typed as (
    select
        _source_file,
        _source_line_no,
        _row_hash,
        _ingested_at,
        trim("Invoice")                                         as invoice,
        trim("StockCode")                                       as stock_code,
        {{ clean_text('"Description"') }}                       as description,
        ({{ clean_text('"Quantity"') }})::integer               as quantity,
        ({{ clean_text('"InvoiceDate"') }})::timestamp          as invoice_ts,
        ({{ clean_text('"Price"') }})::numeric(12, 3)           as unit_price,
        -- exported as float text ("13085.0") -> integer id
        (({{ clean_text('"Customer ID"') }})::numeric)::integer as customer_id,
        {{ clean_text('"Country"') }}                           as country
    from {{ source('uci', 'uci_online_retail_ii_lines') }}
),
file_bounds as (
    select _source_file, min(invoice_ts) as first_at, max(invoice_ts) as last_at from typed group by 1
),
file_cutoff as (
    -- earliest start of any LATER file = point from which this file is superseded
    select a._source_file, min(b.first_at) as superseded_from
    from file_bounds a join file_bounds b on b.first_at > a.first_at
    group by 1
)
select
    t.*,
    row_number() over (partition by t._source_file, t._row_hash order by t._source_line_no) > 1 as is_exact_duplicate,
    coalesce(t.invoice_ts >= c.superseded_from, false)                                       as is_superseded,
    c.superseded_from
from typed t
left join file_cutoff c on c._source_file = t._source_file
