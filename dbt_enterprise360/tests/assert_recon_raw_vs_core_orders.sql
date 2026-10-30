-- Raw landing -> core: every raw order row reaches fct_orders exactly once (values in dq_reconciliation).
select * from {{ ref('dq_reconciliation') }} where check_name = 'assert_recon_raw_vs_core_orders' and variance <> 0
