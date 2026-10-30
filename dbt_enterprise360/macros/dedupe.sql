{# Keep the most recently ingested row per business key. Raw is batch-replaced per file, so this is a
   guard against duplicate keys inside one file, not routine logic; exact-dup counts are tested on raw. #}
{% macro dedupe(cte, keys, order_by='_ingested_at desc, _row_hash') -%}
    select * from (
        select *, row_number() over (partition by {{ keys | join(', ') }} order by {{ order_by }}) as _rn
        from {{ cte }}
    ) d where _rn = 1
{%- endmacro %}
