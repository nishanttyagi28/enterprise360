# 02 — Business & Departmental Reporting Architecture

Owner: Power BI / BI Architecture · Status: PROPOSED (blueprint) · Tags: CONFIRMED FACT / PROPOSED / ASSUMPTION

## 1. Purpose
Defines how data flows from the PostgreSQL warehouse to governed Power BI semantic models and then to the three consumption tiers. It also covers environments, refresh and governance. Report content for each department is in 09, and page design is in 11. The semantic model is in 12 and DAX is in 13.

## 2. Layered architecture (PROPOSED)
```
Sources (Olist e-commerce, Olist marketing funnel, UCI Online Retail I/II candidates)
  → Python ingestion → PG raw  → dbt staging → intermediate → dimensional DW (core)
  → dbt marts (business, operations, marketing, product, bi)          [Data Eng, 05–08,15]
  → mart "bi" schema: Power BI-facing views (stable contract, typed, renamed)
  → Certified semantic model(s) (PBIP/TMDL, Import)                   [12, 13]
  → Thin reports (PBIR) + Paginated MIS (RDL) + Excel (live connection)  [11]
```
| Layer | Responsibility | Rule |
|---|---|---|
| DW core (dbt) | Grain, keys, business rules, KPI logic (authoritative per KPI dictionary README) | Any business logic that can be expressed in SQL lives here |
| `bi` mart views | Contract between DW and Power BI: only the needed columns, friendly names, surrogate keys, no snake-case leakage | Power BI reads **only** `bi.*`. Never raw or staging |
| Semantic model | Relationships, DAX measures (aggregation of dbt-defined logic), calc groups, RLS, formatting | No Power Query business transforms beyond type/rename; no calculated tables except Date helpers and parameter tables |
| Reports | Visuals only; no report-level measures except visual-specific formatting | Thin reports bound live to the certified model |

ASSUMPTION: the `bi` schema and mart names will be defined in 06/15 (Data Engineering). They are pending.

## 3. Consumption tiers (PROPOSED)
| Tier | Tool | Use | Licensing (CONFIRMED FACT, Microsoft licensing docs; re-check before go-live) |
|---|---|---|---|
| Interactive | Power BI reports (Service, apps, mobile) | Exploration, exec storytelling, drill-through | Pro per user for sharing in shared capacity. On Fabric F64+ or Premium P capacity, viewers need only Free licences. Below F64, viewers need Pro |
| Paginated MIS | Power BI paginated reports (Report Builder, .rdl) | Pixel-perfect, multi-page, print/PDF/Excel export, subscriptions (Daily/Monthly Sales MIS etc.) | Paginated reports are supported on Premium, PPU and Fabric F SKUs. Microsoft has extended support to Pro workspaces, but limits apply. ASSUMPTION: the target tenant has PPU or F SKU. Verify the current rules before relying on Pro |
| Excel MIS | Analyze in Excel / Excel live connection to the certified model | Finance and analysts who need pivots on governed measures | Users need **Build** permission on the semantic model plus a Pro/PPU licence (or a Free licence on F64+ for content). Only explicit measures are exposed meaningfully. Implicit measures are disabled (see 13) |

Export limits (CONFIRMED FACT, Microsoft docs, verify the current values): export from a visual to .xlsx is capped at roughly 150k rows (underlying data), and .csv at 30k rows. Admins can disable export. Paginated reports are the sanctioned route for large row-level exports. Bulk extracts must come from the DW/dbt layer rather than Power BI.

## 4. Refresh flow (PROPOSED)
1. Prefect flow: ingest → dbt build (run + tests). If any critical test fails, the flow **stops** and no Power BI refresh runs.
2. On success, Prefect calls the Power BI REST API to refresh the semantic model (enhanced refresh, per-table/partition), using a service principal.
3. Then it runs a post-refresh validation query (DAX via the XMLA/executeQueries API) that compares key measures (GMV, Orders) to the dbt reconciliation table. If they differ beyond tolerance, it raises an alert and marks the DQ page.
4. Paginated subscriptions run after the refresh window.

Olist is a static historical snapshot (CONFIRMED FACT: the Kaggle dataset covers 2016–2018 and is not updated). Daily refresh is therefore **demonstrative**. The pipeline must stay idempotent, and incremental refresh is designed but adds little value on static data (see 12).
Gateway: the on-premises data gateway is needed if PostgreSQL is not reachable from the cloud. For local development, Desktop connects directly.

## 5. Environments & deployment (PROPOSED)
| Env | Workspace | Data source | Who |
|---|---|---|---|
| Dev | `E360-Dev` | PG dev DB / sample | BI developers (Member/Contributor) |
| Test | `E360-Test` | PG test DB, full data | Developers, testers, KPI owners (UAT) |
| Prod | `E360-Prod` + Org App "Enterprise360" | PG prod | Consumers via App (Viewer); no direct workspace access |

- **Source control:** PBIP (TMDL + PBIR) in Git under `/workspace/enterprise360/powerbi` (later on the laptop repo). Every change goes through a PR. CI runs Tabular Editor 2 CLI / BPA rules and checks that TMDL is schema-valid.
- **Promotion:** use Fabric **deployment pipelines** (Dev→Test→Prod) with deployment rules that swap the server/database parameters. CONFIRMED FACT: deployment pipelines require Premium/PPU/Fabric capacity workspaces. Fallback without capacity: Fabric Git integration (also capacity-bound) or scripted deployment via the REST API/`pbi-tools`/Tabular Editor to Pro workspaces.
- Parameters: `PG_Server`, `PG_Database` as Power Query parameters, so there are no hard-coded connection strings. Secrets go in gateway/service credentials, never in Git.

## 6. Governance & certified dataset approach (PROPOSED)
- **One certified core semantic model** ("E360 Commerce Core – Olist") serves all Olist reports. Domain models (e.g. UCI Online Retail) are separate and promoted/certified on their own. They are never merged into the Olist model as one company (brief: preserve provenance).
- Endorsement: Dev content is unendorsed. Test content is *Promoted*. Prod is *Certified* by the BI CoE after KPI reconciliation passes (KPI dictionary README: dbt is authoritative and DAX reconciles to it).
- Every measure carries a description that includes the KPI id (e.g. `KPI_GMV`) from `governance/kpi_dictionary/kpis.yaml`.
- Reports are thin and connect live to the certified model. Local measures in reports are discouraged and caught by review.
- Sensitivity label: *Confidential – Internal*. **Publish to web is prohibited** (tenant setting disabled for these workspaces). The data is public, but the reports present it as internal enterprise MIS, and Publish to web bypasses RLS and authentication.
- RLS is enforced in the Service for Viewer-role users only. Workspace Admin/Member/Contributor roles bypass RLS (see 12).
- Monitoring: refresh history, capacity metrics app (if on capacity), and the Fabric/Power BI activity log feeding the IT & Data/DQ page.

## 7. Limitations (critical)
- Paginated reports, deployment pipelines, XMLA read/write, larger model sizes and >8 scheduled refreshes/day depend on capacity (PPU/F SKU). On Pro, the limits are 8 refreshes/day and a 1 GB model size. Olist fits comfortably in Import (ASSUMPTION pending 03 volumes).
- Mobile: each key page needs a separately authored mobile layout. Calc-group/field-parameter UX is weaker on mobile.
- Power BI cannot provide accounting truth. GMV ≠ recognized revenue, and payment value ≠ cash flow (brief).

## Dependencies & open assumptions
- ASSUMPTION: `bi` schema/mart names and DW grains are pending 06, 07, 08 and 15.
- ASSUMPTION: dataset volumes/coverage are pending 03/04. Olist is believed to be about 100k orders, 2016–2018 (unverified here).
- ASSUMPTION: licensing is PPU or Fabric F SKU (paginated, pipelines). If Pro only, use the fallbacks noted.
- ASSUMPTION: the KPI ids referenced are pending 10 / `kpis.yaml` (not yet written).
