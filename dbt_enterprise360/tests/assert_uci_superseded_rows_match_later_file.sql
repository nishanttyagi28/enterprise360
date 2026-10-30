{{ config(severity='warn') }}
-- The overlap rule drops earlier-file lines by window. Verify each dropped line has an identical
-- line (same _row_hash) in another file, so nothing unique is lost. Expected 0.
with in_several_files as (
    select _row_hash from {{ ref('stg_uci__invoice_lines_all') }}
    group by 1 having count(distinct _source_file) > 1
)
select a._source_file, a._source_line_no
from {{ ref('stg_uci__invoice_lines_all') }} a
left join in_several_files m on m._row_hash = a._row_hash
where a.is_superseded and not a.is_exact_duplicate and m._row_hash is null
