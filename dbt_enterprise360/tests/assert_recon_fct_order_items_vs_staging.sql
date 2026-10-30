-- KPI_GMV / KPI_FREIGHT: fact totals must equal staging (tolerance 0.00 BRL, counts 0)
with s as (select count(*) n, sum(item_price) p, sum(freight_value) f from {{ ref('stg_olist__order_items') }}),
     t as (select count(*) n, sum(item_price) p, sum(freight_value) f from {{ ref('fct_order_items') }})
select s.*, t.* from s, t where s.n <> t.n or s.p <> t.p or s.f <> t.f
