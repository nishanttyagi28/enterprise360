-- KPI_ORDERS: distinct orders preserved staging -> fact (tolerance 0)
select s.n, t.n from (select count(distinct order_id) n from {{ ref('stg_olist__orders') }}) s,
                     (select count(distinct order_id) n from {{ ref('fct_orders') }}) t
where s.n <> t.n
