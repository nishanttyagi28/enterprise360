-- Grain: country name as recorded (43 values incl. 'Unspecified', 'EIRE', 'RSA', 'European Community').
-- ISO codes from seed uci_country_iso (null for regions / non-countries; see mapping_note).
select
    {{ dbt_utils.generate_surrogate_key(['c.country']) }} as uci_country_sk,
    c.country,
    c.country = 'United Kingdom'                          as is_domestic,
    c.country = 'Unspecified'                             as is_unspecified,
    iso.iso_alpha2,
    iso.iso_alpha3,
    iso.mapping_note                                      as iso_mapping_note,
    iso.country is not null                               as is_in_iso_seed
from (select distinct country from {{ ref('stg_uci__invoice_lines') }}) c
left join {{ ref('uci_country_iso') }} iso on iso.country = c.country
