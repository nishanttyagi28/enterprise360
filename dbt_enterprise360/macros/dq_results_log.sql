{#
  Persistent DQ history (dq.dq_results_log), appended once per dbt invocation.
  - on-run-start: dq_ensure_log_table() -> idempotent DDL, so the very first run (and a fresh
    laptop DB) works and core.dq_results (a view over the log) can always compile.
  - on-run-end:   dq_log_results(results) -> one row per executed test (run_id x check_id).
  Reconciliation values and seed config (kpi_id/weight/layer) are captured AT LOG TIME, so history
  shows the numbers of that run, not today's.
#}
{% macro dq_ensure_log_table() %}
create schema if not exists dq;
create table if not exists dq.dq_results_log (
    run_id          text        not null,
    run_at          timestamptz not null,
    check_id        text        not null,
    check_name      text        not null,
    test_type       text        not null,
    layer           text        not null,
    model_name      text,
    kpi_id          text,
    severity        text        not null check (severity in ('block', 'warn')),
    weight          numeric     not null,
    status          text        not null check (status in ('pass', 'warn', 'fail')),
    dbt_status      text        not null,
    failing_rows    integer,
    source_value    numeric,
    mart_value      numeric,
    variance        numeric,
    execution_seconds numeric,
    logged_at       timestamptz not null default now(),
    primary key (run_id, check_id)
);
{% endmacro %}

{% macro _dq_layer(model_name, resource_type) %}
    {%- if resource_type == 'source' -%}source
    {%- elif model_name.startswith('stg_') -%}staging
    {%- elif model_name.startswith('int_') -%}intermediate
    {%- elif model_name.startswith('mart_') -%}marts
    {%- elif model_name.startswith('snap_') -%}snapshots
    {%- else -%}core
    {%- endif -%}
{% endmacro %}

{% macro _q(v) -%}
    {%- if v is none -%}null{%- else -%}'{{ (v | string) | replace("'", "''") }}'{%- endif -%}
{%- endmacro %}

{% macro dq_log_results(results) %}
  {% if not execute %}{{ return('') }}{% endif %}
  {% set rows = [] %}
  {% for r in results if r.node.resource_type == 'test' %}
    {% set node = r.node %}
    {# attached model: generic tests carry attached_node; singular tests -> first model dependency #}
    {% set deps = [] %}
    {% for d in node.depends_on.nodes if d.split('.')[0] in ('model', 'source', 'snapshot') %}{% do deps.append(d) %}{% endfor %}
    {# singular tests: attribute to the most downstream layer referenced (mart > fct/dim > int > stg) #}
    {% set ranked = [] %}
    {% for prefix in ['.mart_', '.fct_', '.dim_', '.dq_', '.int_', '.'] %}
      {% for d in deps if prefix in d and d not in ranked %}{% do ranked.append(d) %}{% endfor %}
    {% endfor %}
    {% set target_id = node.attached_node or (ranked[0] if ranked else none) %}
    {% set rtype = target_id.split('.')[0] if target_id else 'model' %}
    {% set model_name = target_id.split('.')[-1] if target_id else none %}
    {% set dbt_status = (r.status | string) | lower %}
    {# status mapping: pass->pass, warn->warn, fail/error->fail, skipped->fail (a check that did not
       run proved nothing; counting it as fail keeps the DQ score conservative) #}
    {% set status = 'pass' if dbt_status == 'pass' else ('warn' if dbt_status == 'warn' else 'fail') %}
    {% set severity = 'block' if (node.config.severity | lower) == 'error' else 'warn' %}
    {% do rows.append("(" ~ _q(node.unique_id) ~ ", " ~ _q(node.name) ~ ", "
        ~ _q('generic' if node.test_metadata else 'singular') ~ ", "
        ~ _q(_dq_layer(model_name or '', rtype)) ~ ", " ~ _q(model_name) ~ ", "
        ~ _q(severity) ~ ", " ~ _q(status) ~ ", " ~ _q(dbt_status) ~ ", "
        ~ (r.failures if r.failures is not none else 'null') ~ ", "
        ~ (r.execution_time | round(3)) ~ ")") %}
  {% endfor %}
  {% if rows | length == 0 %}{{ return('') }}{% endif %}

  {% set cfg = adapter.get_relation(database=target.database, schema='core', identifier='dq_check_config') %}
  {% set rec = adapter.get_relation(database=target.database, schema='core', identifier='dq_reconciliation') %}
  {% set sql %}
    insert into dq.dq_results_log
        (run_id, run_at, check_id, check_name, test_type, layer, model_name, kpi_id, severity,
         weight, status, dbt_status, failing_rows, source_value, mart_value, variance, execution_seconds)
    select '{{ invocation_id }}', '{{ run_started_at }}'::timestamptz,
           v.check_id, v.check_name, v.test_type,
           coalesce({{ 'c.layer_override' if cfg else 'null' }}, v.layer), v.model_name,
           {{ 'c.kpi_id' if cfg else 'null' }}, v.severity,
           coalesce({{ 'c.weight' if cfg else 'null' }}, case v.severity when 'block' then 3 else 1 end), v.status, v.dbt_status, v.failing_rows,
           {{ 'rc.source_value, rc.mart_value, rc.variance' if rec else 'null, null, null' }},
           v.execution_seconds
    from (values {{ rows | join(',\n') }})
        as v(check_id, check_name, test_type, layer, model_name, severity, status, dbt_status,
             failing_rows, execution_seconds)
    {% if cfg %}
    -- most specific matching config row wins (longest LIKE pattern)
    left join lateral (
        select c.kpi_id, c.weight, nullif(c.layer_override, '') as layer_override
        from {{ cfg }} c
        where v.check_name like c.check_pattern or v.check_id = c.check_pattern
        order by length(c.check_pattern) desc
        limit 1
    ) c on true
    {% endif %}
    {% if rec %}left join {{ rec }} rc on rc.check_name = v.check_name{% endif %}
    on conflict (run_id, check_id) do nothing
  {% endset %}
  {% do run_query(sql) %}
  {% do run_query('commit') %}
  {{ log('dq_results_log: logged ' ~ (rows | length) ~ ' checks for run ' ~ invocation_id, info=true) }}
{% endmacro %}
