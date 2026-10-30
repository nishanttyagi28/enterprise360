-- Joining fact to its dims must not change row count (fan-out) or drop rows (inner-join loss).
with base as (select count(*) n from {{ ref('fct_order_items') }}),
joined as (select count(*) n from {{ ref('fct_order_items') }} f
  left join {{ ref('dim_product') }} p on f.product_sk = p.product_sk
  left join {{ ref('dim_seller') }} s on f.seller_sk = s.seller_sk
  left join {{ ref('dim_date') }} d on f.purchase_date_key = d.date_key)
select base.n, joined.n from base, joined where base.n <> joined.n
