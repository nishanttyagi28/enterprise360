# ENTERPRISE360 — Project Brief (from Jolly Tyagi, owner)

Enterprise-wide BI, Analytics & Reporting Infrastructure for a realistic mid-to-large retail & e-commerce company.
Primary interface: Microsoft Power BI (PBIP). Secondary: Streamlit (supporting only).
Engineering standard: production-oriented code equivalent to 2–3+ yrs professional experience (a quality bar, not an employment claim).
NOT a Kaggle dashboard, NOT disconnected reports, NOT beginner SQL, NOT notebooks, NOT a fabricated enterprise simulation.

## Must answer
Company performance; revenue; where money is made/lost; department over/under-performance; budget efficiency; inventory; supplier performance; operational efficiency; marketing ROI; workforce; customer experience; recommended management decisions.

## Departments & reports
Executive (overview, revenue/profitability, growth, dept performance, KPI scorecards, budget, risks, exec review, quarterly)
Sales (daily/weekly/monthly, target achievement, salesperson, region, store, product, category, channel, orders, returns/cancellations, AOV, purchase behaviour)
Finance (P&L, revenue, expenses, GP, OP, margins, budget vs actual, dept spend, AP, AR, cash flow, variance, product/region profitability, forecasting) — only where source data supports accounting definitions; GMV ≠ recognized revenue; transaction value ≠ cash flow.
Marketing (spend, campaigns, ROI, ROAS, CAC, conversion, leads, response, funnel, channel, segmentation, acquisition/retention)
HR (headcount, dept workforce, recruitment, hiring funnel, attrition, tenure, attendance, absenteeism, payroll, compensation, workforce cost, performance where valid)
Operations (performance, store productivity, order processing, fulfilment, delivery SLA, warehouse, returns mgmt, opex, service levels)
Inventory (levels, ageing, turnover, movement, stockouts, excess, valuation, reorder, ABC, slow-moving)
Procurement (POs, spend, vendor performance, lead time, PPV, concentration, cycle time, reliability)
Supply chain (delivery perf, transport cost, warehouse efficiency, supplier delays, fulfilment, logistics cost, OTD, distribution)
Customer service (complaints, categories, resolution time, CSAT, SLA, returns/refunds, workload)
Product & merchandising (performance, profitability, category, returns, ratings, pricing, demand)
Risk & compliance (anomalies, fraud indicators, chargebacks, supplier risk, operational risk, compliance exceptions, exposure)
IT & data (pipeline monitoring, freshness, DQ, failures, refresh status, reconciliation, availability)
MIS (Daily/Monthly Sales MIS, Target Achievement, Daily Collections, Purchase Register, Vendor Performance, Inventory Ageing, Stock Movement, Returns & Cancellation, Attendance, Payroll Summary, Recruitment, Budget vs Actual, Dept Expenses, Monthly Financial Report, Exec/Management Review) — export-friendly; distinguish interactive dashboards vs paginated reports vs scheduled distribution vs Excel exports.

## Data — NON-NEGOTIABLE
Real public datasets only. No fabricated transactions, employees, salaries, invoices, POs, payroll or financials.
Candidates (to verify, not pre-approved): UCI Online Retail, UCI Online Retail II, Olist Brazilian E-Commerce, Olist Marketing Funnel, Walmart M5, Kaggle Store Sales (Favorita), SEC EDGAR / XBRL, gov financial data, Maven Analytics marketing, IBM HR Attrition, US BLS, CFPB Complaint DB, public review datasets, public procurement DBs, supply-chain research datasets, retail inventory and logistics/delivery datasets.
Per dataset: exact name, original publisher, direct download URL, #records, #tables, coverage, data dictionary, license, usage restrictions, dimensions, measures, KPIs supported, missing fields, DQ issues, reporting limitations. Never invent stats/links. Verify with original publisher.
Classify REAL / DERIVED / SIMULATED (avoid simulated). State limitations explicitly. Don't join unrelated datasets as one company; preserve provenance and source IDs. Olist = primary e-commerce case study; others = independent functional domains → multi-source architecture, not false relationships.

## Power BI (primary)
Sections per data availability: Executive Command Center, Sales, Revenue, Financial, Budget vs Actual, Marketing, HR, Recruitment & Attendance, Operations, Inventory, Procurement & Vendor, Supply Chain Control Tower, Customer, Product, Risk & Compliance, MIS, Data Quality & Governance, Forecasting & Planning.
Exec Command Center: Net Revenue, Gross Profit, Operating Profit, Orders, Active Customers, Gross Margin, Revenue Growth, Target Achievement; revenue/profit trends, dept/region/channel, actual vs target; risks, underperformers, negative variances, positives, action items. CEO understands in 30s.
Features: PBIP, enterprise semantic model, star schema, advanced DAX, reusable measures, calc groups, field parameters, dynamic titles, drill-through, tooltips, bookmarks, what-if, RLS, conditional formatting, decomposition tree, waterfall, time intelligence, dynamic KPI cards, perf optimization.
Design: dark navy/charcoal, restrained cyan/blue accents, professional type, consistent spacing, clean hierarchy, context-aware slicers, intuitive nav, exec storytelling, no clutter.

## Stack
Python ingestion; Pandas/NumPy; PostgreSQL; SQL; dbt Core; Prefect; dbt tests + Great Expectations; SciPy/Statsmodels; scikit-learn; Power BI; Streamlit; Pytest; Docker; GitHub Actions; Git.
Flow: sources → Python ingestion → PG raw → dbt staging → intermediate → dimensional DW → departmental marts → PBI semantic model → reporting. No Kafka/Spark/K8s/microservices without justification.

## Engineering quality
Python: modular, separation of concerns, type hints, structured logging, meaningful exceptions, config mgmt, env secrets, reusable, deps mgmt, unit+integration tests, idempotent, incremental, transactional, validated, documented, DRY, no monoliths.
SQL: correct grain, joins, CTEs, window functions, optimization, indexing, constraints, RI, incremental, materializations, no fan-out/double counting, naming conventions, documented logic, reconciliation queries.
dbt: staging, intermediate, domain marts, sources, freshness, schema + custom tests, docs, lineage, snapshots, incremental where useful.
Every decision technically justified; no syntax for show.

## Warehouse
Candidate dims: date, customer, product, store, seller, supplier, employee, channel, geography, campaign.
Candidate facts: orders, order_items, payments, returns, inventory, procurement, marketing, web_events, attendance, payroll, recruitment, expenses, budget, deliveries, complaints, risk_events. Build only what real data supports.
Facts: business process, grain, PK, FKs, measures, source, transformation rules, refresh. Dims: business key, surrogate key, attributes, SCD. Source-specific marts where dimensions can't be legitimately conformed.

## KPI framework
Version-controlled dictionary: id, name, definition, formula, numerator, denominator, source, fact/dim deps, grain, refresh, owner, target/benchmark, validation rules. One definition across SQL/dbt/PBI/Streamlit. Candidate KPIs: Net Sales, Revenue Growth, GP, GM, OP, AOV, Target Achievement; Total Expenses, Budget Variance, Op Margin, Cost/Order, Profitability; CAC, ROAS, CTR, Conversion, Mktg ROI; Headcount, Attrition, Absenteeism, Hiring Rate, Cost/Hire; OTD, Fill Rate, Order Cycle Time, Inventory Turnover, Stockout Rate; Retention, Repeat Purchase, Return Rate, Complaint Resolution Time; Pipeline Success, Freshness, DQ Score, Reconciliation Variance. Only those supported by data.

## Advanced analytics (only where data supports)
Demand/sales forecasting, segmentation, RFM, retention, churn, anomaly detection, return analysis, attribution, inventory optimization, financial forecasting, hypothesis tests. Per model: objective, target, features, observation window, prep, train/val/test, baseline, metrics, limitations. No leakage. Never invent accuracy. HR predictive = exploratory, privacy & fairness, not automated employment decisions.

## Streamlit (supporting)
Enterprise overview, dept navigation, decision register, insights, DQ monitoring, forecast scenarios, pipeline monitoring.

## Repo
enterprise360/ with README, LICENSE, .gitignore, .env.example, docker-compose.yml, Makefile; docs/ (project-charter, business-requirements, architecture, data-dictionary, dimensional-model, kpi-catalog, data-lineage, source-to-target-mapping, governance, assumptions-limitations); data/ (raw, samples, processed); ingestion/ (sources, extractors, validators, loaders, pipeline.py); database/ (ddl, migrations, init.sql); dbt_enterprise360/ (staging, intermediate, dimensions, marts/{business,finance,marketing,people,operations,product,risk,bi}, tests, snapshots, macros, analyses); analytics/; ml/ (forecasting, segmentation, churn, anomaly_detection); orchestration/ (flows, monitoring); powerbi/ (Enterprise360.pbip, semantic-model, reports, dax, documentation); app/ (Home.py, pages, components, services, queries); tests/ (unit, integration, data_quality, business_rules); .github/workflows. Large data outside git; document downloads, licenses, checksums; no secrets.

## Testing & acceptance
Data tests (PK, nulls, RI, dupes, freshness, reconciliation, business rules); Python (unit, integration, ingestion, error handling, idempotency); SQL (aggregation, joins, grain, financial reconciliation, performance); Power BI (DAX validation, filters, relationships, RLS, Performance Analyzer).
Done only when: sources load reproducibly, provenance documented, relationships validated, critical dbt tests pass, KPIs reconcile, semantic model works, exec + dept reports work, MIS exports exist, Python/SQL tests pass, docs complete, another dev can set up the repo.

## Roadmap
P1 research & requirements → P2 DE foundation → P3 analytics engineering → P4 reporting foundation (KPIs, marts, reconciliation) → P5 Power BI → P6 advanced analytics → P7 Streamlit → P8 production readiness (Docker, Prefect, CI, tests, docs, demo video). Vertical slice first. Never trade data quality for deadlines.

## Critical review required
Act as enterprise data architect / senior DE / AE lead / senior PBI dev / BI architect / consultant. Challenge the proposal: missing functions, missing datasets, incompatible sources, unavailable metrics, wrong assumptions, modeling weaknesses, SQL perf risks, PBI limits, complexity, unnecessary tech, security/privacy risks, unrealistic timelines.

## REQUIRED FIRST DELIVERABLE — blueprint only, NO full codebase yet. Exact order:
1 Executive assessment; 2 Business & departmental reporting architecture; 3 Verified real-world dataset catalogue; 4 Dataset feasibility matrix; 5 Source-to-target mapping; 6 Data warehouse architecture; 7 PostgreSQL schema; 8 Fact & dimension modeling; 9 Department-wise reporting matrix; 10 Complete KPI dictionary; 11 Power BI report architecture; 12 Power BI semantic model; 13 DAX development strategy; 14 Python engineering architecture; 15 SQL & dbt architecture; 16 Data quality framework; 17 Advanced analytics scope; 18 GitHub repo structure; 19 Testing strategy; 20 Implementation roadmap; 21 Risks & limitations; 22 Production-readiness acceptance criteria.
Clearly tag CONFIRMED FACT / PROPOSED / ASSUMPTION. Cite sources for dataset claims. Say explicitly when a dataset can't support a report. Never invent data, metrics, sources or relationships.

## Working arrangement
Final code will live on Jolly's laptop (Windows, VS Code). Team drafts in /workspace/enterprise360 on the shared computer; the master bot copies to the laptop.
