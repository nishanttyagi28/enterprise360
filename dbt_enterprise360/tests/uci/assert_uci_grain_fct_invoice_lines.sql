{{ config(enabled=var('uci_models_built', false)) }}
-- ASSUMPTION: uci_* models not built yet; names from docs/blueprint/uci-online-retail-plan.md. Confirm with DE.
select _source_file, _source_line_no, count(*) n from {{ ref('uci_fct_invoice_lines') }} group by 1,2 having count(*)>1
