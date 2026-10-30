-- Row counts before/after each dedup rule; feeds core.dq_reconciliation -> core.dq_results.
with a as (select * from {{ ref('stg_uci__invoice_lines_all') }}),
window_bounds as (
    -- overlap window = [start of later file, end of earlier file]
    select min(superseded_from) as w_start,
           (select max(invoice_ts) from a where superseded_from is not null) as w_end
    from a
)
select 'assert_uci_exact_duplicates_dropped' as check_name,
       count(*)::numeric                                          as rows_before,
       count(*) filter (where not is_exact_duplicate)::numeric    as rows_after
from a
union all
select 'assert_uci_overlap_deduped',
       count(*) filter (where not is_exact_duplicate)::numeric,
       count(*) filter (where not is_exact_duplicate and not is_superseded)::numeric
from a, window_bounds w
where a.invoice_ts between w.w_start and w.w_end
