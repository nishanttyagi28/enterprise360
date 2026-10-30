-- grain: one row per (customer_unique_id) in dim_customer. Returns duplicates.
select customer_unique_id, count(*) as n from {{ ref('dim_customer') }} group by customer_unique_id having count(*) > 1
