{# Fails with one row per duplicated grain key. Usage (model yml):
   tests: [{grain_unique: {columns: ['order_id','order_item_id']}}] #}
{% test grain_unique(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
