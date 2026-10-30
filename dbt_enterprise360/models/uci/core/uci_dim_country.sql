-- Grain: country name as recorded (43 values incl. 'Unspecified', 'EIRE', 'RSA', 'European Community').
-- No ISO mapping yet (non-standard names need a reviewed seed).
select
    {{ dbt_utils.generate_surrogate_key(['country']) }} as uci_country_sk,
    country,
    country = 'United Kingdom'                          as is_domestic,
    country = 'Unspecified'                             as is_unspecified
from (select distinct country from {{ ref('stg_uci__invoice_lines') }}) c
