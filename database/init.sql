-- psql convenience: psql -d enterprise360 -f database/init.sql   (same as `python -m ingestion init-db`)
\ir ddl/000_audit.sql
\ir ddl/001_schemas.sql
\ir ddl/010_raw_olist.sql
\ir ddl/020_raw_uci.sql
\ir ddl/030_raw_funnel.sql
\ir ddl/040_analytics_forecast.sql
