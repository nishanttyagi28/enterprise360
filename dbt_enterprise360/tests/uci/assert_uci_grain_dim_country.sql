{{ config(enabled=var('uci_models_built', false)) }}
-- ASSUMPTION: uci_* models not built yet; names from docs/blueprint/uci-online-retail-plan.md. Confirm with DE.
select country, count(*) n from {{ ref('uci_dim_country') }} group by 1 having count(*)>1
