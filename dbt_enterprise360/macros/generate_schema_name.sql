{# Use the configured schema verbatim (staging/intermediate/core/marts) instead of dbt's
   default <target>_<custom> concatenation: the warehouse layout is a contract with Power BI. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}{{ target.schema }}{%- else -%}{{ custom_schema_name | trim }}{%- endif -%}
{%- endmacro %}
