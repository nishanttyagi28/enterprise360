{# STTM §1 null normalisation: '', whitespace, NA, nan, null, none -> NULL; otherwise trimmed.
   Python reference implementation: ingestion.validators.normalise_null #}
{% macro clean_text(col) -%}
    case when lower(trim({{ col }})) in ('', 'na', 'nan', 'null', 'none') then null else trim({{ col }}) end
{%- endmacro %}

{% macro zip_prefix(col) -%}
    lpad({{ clean_text(col) }}, 5, '0')
{%- endmacro %}

{% macro to_ts(col) -%}
    ({{ clean_text(col) }})::timestamp
{%- endmacro %}

{% macro date_key(ts) -%}
    (to_char({{ ts }}, 'YYYYMMDD'))::integer
{%- endmacro %}
