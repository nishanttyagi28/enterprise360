-- customer_id (per-order account id) -> customer_unique_id (the person) + the deterministic
-- customer_sk that dim_customer is keyed on. Grain: customer_id (1:1, tested), so joining facts
-- through it can never multiply rows.
select
    c.customer_id,
    c.customer_unique_id,
    {{ dbt_utils.generate_surrogate_key(['c.customer_unique_id']) }} as customer_sk,
    c.customer_zip_prefix,
    c.customer_city,
    c.customer_state
from {{ ref('stg_olist__customers') }} c
