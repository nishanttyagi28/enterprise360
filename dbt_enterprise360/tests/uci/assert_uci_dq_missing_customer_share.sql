{{ config(enabled=var('uci_models_built', false)) }}
-- ASSUMPTION: uci_* models not built yet; names from docs/blueprint/uci-online-retail-plan.md. Confirm with DE.
{{ config(severity='warn') }}
-- DQ: share of lines without Customer ID (~22.8% on raw). Warns whenever > 0; value logged.
select count(*) filter (where not has_customer)::numeric / count(*) as missing_share from {{ ref('uci_fct_invoice_lines') }} having count(*) filter (where not has_customer) > 0
