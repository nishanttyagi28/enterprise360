-- customer_id -> customer_unique_id map must be 1:1 per customer_id, so orders don't multiply.
select o.n, j.n from (select count(*) n from {{ ref('fct_orders') }}) o,
 (select count(*) n from {{ ref('fct_orders') }} f left join {{ ref('dim_customer') }} c on f.customer_sk = c.customer_sk) j
where o.n <> j.n
