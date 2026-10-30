-- Overlap 2010-12-01..09: no line of an earlier file may survive at/after the start of a later file.
-- Before/after counts land in core.dq_reconciliation (source_value/mart_value/variance).
with cutoff as (
    select distinct _source_file, superseded_from
    from {{ ref('stg_uci__invoice_lines_all') }} where superseded_from is not null
)
select l._source_file, l.invoice_ts
from {{ ref('stg_uci__invoice_lines') }} l
join cutoff c on c._source_file = l._source_file and l.invoice_ts >= c.superseded_from
