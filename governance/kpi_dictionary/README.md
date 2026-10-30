# KPI Dictionary
- **One source of truth:** `kpis.yaml` (validated against `schema.yaml`). dbt models are the authoritative implementation; SQL, DAX and Streamlit reference/reconcile to them — never redefine logic.
- **Versioning:** semver per KPI. MAJOR = meaning/formula change (breaks comparability); MINOR = new dimension/source support; PATCH = wording/docs. Every change adds a `change_log` entry.
- **Change process:** PR required; reviewed by KPI owner + analytics engineering; CI validates YAML schema and runs KPI reconciliation tests.
- **Status:** SUPPORTED | PARTIAL | NOT SUPPORTED, per 10-kpi-dictionary.md; data dependencies are ASSUMPTIONs until 03/04 verify the datasets.
- **Generated docs:** human-readable catalogue (dbt docs / markdown) is generated from YAML; do not hand-edit generated output.
- Targets/benchmarks stay `TBD (set by owner once baseline measured)`.
