{{ config(enabled=var('uci_models_built', false)) }}
-- ASSUMPTION: uci_* models not built yet; names from docs/blueprint/uci-online-retail-plan.md. Confirm with DE.
-- exact numeric, tolerance 0
select * from (select count(*) n, sum(quantity) q, sum(quantity*unit_price) v from {{ ref('stg_uci__invoice_lines') }}) s,
 (select count(*) n2, sum(quantity) q2, sum(line_value) v2 from {{ ref('uci_fct_invoice_lines') }}) t where n<>n2 or q<>q2 or v<>v2
