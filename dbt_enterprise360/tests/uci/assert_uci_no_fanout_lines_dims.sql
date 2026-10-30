{{ config(enabled=var('uci_models_built', false)) }}
-- ASSUMPTION: uci_* models not built yet; names from docs/blueprint/uci-online-retail-plan.md. Confirm with DE.
-- joining dims must preserve fact rows (unknown customer member -1 must exist)
select b.n, j.n from (select count(*) n from {{ ref('uci_fct_invoice_lines') }}) b,
 (select count(*) n from {{ ref('uci_fct_invoice_lines') }} f
   left join {{ ref('uci_dim_product') }} p on f.uci_product_sk=p.uci_product_sk
   left join {{ ref('uci_dim_customer') }} c on f.uci_customer_sk=c.uci_customer_sk
   left join {{ ref('uci_dim_country') }} k on f.uci_country_sk=k.uci_country_sk) j where b.n<>j.n
