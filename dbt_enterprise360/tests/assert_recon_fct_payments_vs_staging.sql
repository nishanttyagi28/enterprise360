-- KPI_PAYMENT_VALUE: fact == staging (tolerance 0.00)
select s.v, t.v from (select count(*) n, sum(payment_value) v from {{ ref('stg_olist__order_payments') }}) s,
                     (select count(*) n, sum(payment_value) v from {{ ref('fct_payments') }}) t
where s.n <> t.n or s.v <> t.v
