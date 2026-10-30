{# No fan-out / no loss: model row count must equal compare_model row count (optionally distinct on a key). #}
{% test row_count_matches(model, compare_model, key=None) %}
with a as (select count({{ 'distinct ' ~ key if key else '*' }}) as n from {{ model }}),
     b as (select count({{ 'distinct ' ~ key if key else '*' }}) as n from {{ compare_model }})
select a.n as model_rows, b.n as compare_rows from a, b where a.n <> b.n
{% endtest %}
