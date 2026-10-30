-- In month 0 every cohort member is active by definition -> retention_rate must be exactly 1.
select * from {{ ref('mart_customer_cohorts') }}
where months_since_first_order = 0 and active_customers <> cohort_customers
