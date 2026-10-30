"""Generates the Enterprise360 PBIP (TMDL semantic model + PBIR report).

Deterministic: GUID-like ids are derived from names (uuid5), so re-running produces
identical files and clean git diffs. Edit this script, not the generated files,
or edit generated files and stop using the script -- pick one (README).
"""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SM = ROOT / "Enterprise360.SemanticModel"
RP = ROOT / "Enterprise360.Report"
NS = uuid.UUID("6f1c7a52-6b8e-4b7c-9a0e-2b1f3e3c0e36")
MS = "https://developer.microsoft.com/json-schemas/fabric"
V_VISUAL, V_PAGE, V_REPORT = "2.5.0", "2.0.0", "3.1.0"
V_BOOKMARK = "2.0.0"

# dim_date completeness flag (TRUE = whole calendar month inside Olist coverage). [GMV Growth %]
# returns BLANK when the current or prior month is not complete. Set to None to drop the check.
DATE_COMPLETE_FLAG_COLUMN: str | None = "is_complete_month"

# core.dq_run_summary (one row per dbt run, strict dq_score, is_latest_run). True = [DQ Score %] reads it;
# False = fall back to the weighted calculation over core.dq_results.
USE_DQ_RUN_SUMMARY = True


def gid(*parts: str) -> str:
    return str(uuid.uuid5(NS, "|".join(parts)))


def hid(*parts: str) -> str:  # 20-char hex names for pages/visuals (PBIR convention)
    return uuid.uuid5(NS, "|".join(parts)).hex[:20]


def q(name: str) -> str:
    """Quote a TMDL object name when needed."""
    if name.replace("_", "").isalnum() and not name[0].isdigit():
        return name
    return "'" + name.replace("'", "''") + "'"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def wjson(path: Path, obj) -> None:
    write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------------------
# Semantic model definition
# --------------------------------------------------------------------------------------
# column spec: (model name, source column, dataType, options dict)
KEY = {"hidden": True, "summarize": "none"}


def pg_source(dbt_model: str, cols: list[str], extra_steps: list[str] | None = None,
              optional: bool = False, schema: str = "PgSchema") -> list[str]:
    """M for one dbt relation. optional=True: an absent relation yields an empty table with the same
    columns instead of failing the whole refresh (used for core.dq_results until it is built)."""
    sel = ", ".join(f'"{c}"' for c in cols)
    nav = f'Source{{[Schema = {schema}, Item = "{dbt_model}"]}}[Data]'
    if optional:
        empty = "#table(type table [" + ", ".join(f"{c} = any" for c in cols) + "], {})"
        nav = f"try {nav} otherwise {empty}"
    lines = [
        "let",
        "    Source = PostgreSQL.Database(PgServer, PgDatabase),",
        f"    Data = {nav},",
        f"    Selected = Table.SelectColumns(Data, {{{sel}}})" + ("," if extra_steps else ""),
    ]
    steps = extra_steps or []
    for i, s in enumerate(steps):
        lines.append("    " + s + ("," if i < len(steps) - 1 else ""))
    last = steps[-1].split("=")[0].strip() if steps else "Selected"
    lines += ["in", f"    {last}"]
    return lines


UF = [("AC", "Acre", "North"), ("AL", "Alagoas", "Northeast"), ("AP", "Amapá", "North"),
      ("AM", "Amazonas", "North"), ("BA", "Bahia", "Northeast"), ("CE", "Ceará", "Northeast"),
      ("DF", "Distrito Federal", "Center-West"), ("ES", "Espírito Santo", "Southeast"),
      ("GO", "Goiás", "Center-West"), ("MA", "Maranhão", "Northeast"), ("MT", "Mato Grosso", "Center-West"),
      ("MS", "Mato Grosso do Sul", "Center-West"), ("MG", "Minas Gerais", "Southeast"),
      ("PA", "Pará", "North"), ("PB", "Paraíba", "Northeast"), ("PR", "Paraná", "South"),
      ("PE", "Pernambuco", "Northeast"), ("PI", "Piauí", "Northeast"), ("RJ", "Rio de Janeiro", "Southeast"),
      ("RN", "Rio Grande do Norte", "Northeast"), ("RS", "Rio Grande do Sul", "South"),
      ("RO", "Rondônia", "North"), ("RR", "Roraima", "North"), ("SC", "Santa Catarina", "South"),
      ("SP", "São Paulo", "Southeast"), ("SE", "Sergipe", "Northeast"), ("TO", "Tocantins", "North")]
uf_rows = ", ".join(f'{{"{a}", "{b}", "{c}"}}' for a, b, c in UF)

TABLES: list[dict] = [
    {
        "name": "Order Item", "dbt": "fct_order_items",
        "desc": "Fact at order-line grain (order_id, order_item_id). One row = one unit (Olist has no quantity column).",
        "cols": [
            ("order_id", "order_id", "string", KEY),
            ("order_item_id", "order_item_id", "int64", KEY),
            ("product_sk", "product_sk", "string", KEY),
            ("seller_sk", "seller_sk", "string", KEY),
            ("item_price", "item_price", "decimal", {"hidden": True, "summarize": "sum", "fmt": "#,0.00"}),
            ("freight_value", "freight_value", "decimal", {"hidden": True, "summarize": "sum", "fmt": "#,0.00"}),
            ("Shipping Limit At", "shipping_limit_at", "dateTime", {"summarize": "none", "fmt": "yyyy-mm-dd hh:nn"}),
            ("is_handover_on_time", "is_handover_on_time", "boolean", {"hidden": True, "summarize": "none"}),
        ],
    },
    {
        "name": "Order", "dbt": "fct_orders",
        "desc": "Fact at order grain (order_id). Carries customer, status and purchase date; filters Order Item, Payment, Review and Delivery.",
        "cols": [
            ("Order ID", "order_id", "string", {"summarize": "none"}),
            ("customer_sk", "customer_sk", "string", KEY),
            ("order_status", "order_status", "string", KEY),
            ("purchase_date_key", "purchase_date_key", "int64", KEY),
            ("Purchased At", "purchased_at", "dateTime", {"summarize": "none", "fmt": "yyyy-mm-dd hh:nn"}),
            ("Approved At", "approved_at", "dateTime", {"summarize": "none", "fmt": "yyyy-mm-dd hh:nn"}),
            ("hours_to_approve", "hours_to_approve", "double", {"hidden": True, "summarize": "none", "fmt": "#,0.0"}),
            ("Review Score", "latest_review_score", "int64", {"summarize": "none"}),
            ("payment_vs_items_diff", "payment_vs_items_diff", "decimal", {"hidden": True, "summarize": "none", "fmt": "#,0.00"}),
            ("has_items", "has_items", "boolean", {"hidden": True, "summarize": "none"}),
            ("has_payment", "has_payment", "boolean", {"hidden": True, "summarize": "none"}),
        ],
    },
    {
        "name": "Payment", "dbt": "fct_payments",
        "desc": "Fact at payment grain (order_id, payment_sequential). Transaction value, NOT sales and NOT cash flow. Never related to Order Item.",
        "cols": [
            ("order_id", "order_id", "string", KEY),
            ("payment_sequential", "payment_sequential", "int64", KEY),
            ("Payment Type", "payment_type", "string", {"summarize": "none"}),
            ("Payment Installments", "payment_installments", "int64", {"summarize": "none"}),
            ("payment_value", "payment_value", "decimal", {"hidden": True, "summarize": "sum", "fmt": "#,0.00"}),
        ],
    },
    {
        "name": "Delivery", "dbt": "fct_deliveries",
        "desc": "Fact at order grain for fulfilment. Estimated date is Olist's customer estimate, not a contractual SLA.",
        "cols": [
            ("order_id", "order_id", "string", KEY),
            ("delivered_date_key", "delivered_date_key", "int64", KEY),
            ("Delivered At", "delivered_customer_at", "dateTime", {"summarize": "none", "fmt": "yyyy-mm-dd hh:nn"}),
            ("Estimated Delivery At", "estimated_delivery_at", "dateTime", {"summarize": "none", "fmt": "yyyy-mm-dd"}),
            ("Carrier Handover At", "delivered_carrier_at", "dateTime", {"summarize": "none", "fmt": "yyyy-mm-dd hh:nn"}),
            ("is_on_time", "is_on_time", "boolean", {"hidden": True, "summarize": "none"}),
            ("is_otd_eligible", "is_otd_eligible", "boolean", {"hidden": True, "summarize": "none"}),
            ("delivery_days", "delivery_days", "double", {"hidden": True, "summarize": "none", "fmt": "#,0.0"}),
            ("dq_missing_delivery_ts", "dq_missing_delivery_ts", "boolean", {"hidden": True, "summarize": "none"}),
            ("dq_delivered_before_purchase", "dq_delivered_before_purchase", "boolean", {"hidden": True, "summarize": "none"}),
        ],
    },
    {
        "name": "Customer", "dbt": "dim_customer",
        "desc": "One row per customer_unique_id (the real person). customer_id is per-order in Olist and is not used for repeat logic.",
        "cols": [
            ("customer_sk", "customer_sk", "string", KEY),
            ("Customer Unique ID", "customer_unique_id", "string", {"summarize": "none"}),
            ("customer_state", "state", "string", KEY),
            ("Customer City", "city", "string", {"summarize": "none"}),
            ("First Order Date", "first_order_date", "dateTime", {"summarize": "none", "fmt": "yyyy-mm-dd"}),
            ("Lifetime Orders", "lifetime_orders", "int64", {"summarize": "none"}),
        ],
    },
    {
        "name": "Geography", "dbt": "dim_customer",
        "desc": "Customer state (UF) level. State-level on purpose: zip-prefix geolocation has many rows per prefix. State name/region are IBGE reference data.",
        "cols": [
            ("State", "state_code", "string", {"summarize": "none"}),
            ("State Name", "state_name", "string", {"summarize": "none"}),
            ("Region", "region", "string", {"summarize": "none"}),
        ],
        "select": ["state"],
        "steps": [
            'States = Table.Distinct(Table.RenameColumns(Selected, {{"state", "state_code"}}))',
            f'Ref = #table(type table [uf = text, state_name = text, region = text], {{{uf_rows}}})',
            'Joined = Table.NestedJoin(States, {"state_code"}, Ref, {"uf"}, "ref", JoinKind.LeftOuter)',
            'Expanded = Table.ExpandTableColumn(Joined, "ref", {"state_name", "region"})',
        ],
    },
    {
        "name": "Seller", "dbt": "dim_seller",
        "desc": "Marketplace seller (merchant), not a supplier. Seller state is an attribute only (no Geography relationship, to avoid ambiguous paths).",
        "cols": [
            ("seller_sk", "seller_sk", "string", KEY),
            ("Seller ID", "seller_id", "string", {"summarize": "none"}),
            ("Seller City", "city", "string", {"summarize": "none"}),
            ("Seller State", "state", "string", {"summarize": "none"}),
        ],
    },
    {
        "name": "Product", "dbt": "dim_product",
        "desc": "Product with English category (falls back to Portuguese name where no translation exists, per STTM 2.7).",
        "cols": [
            ("product_sk", "product_sk", "string", KEY),
            ("Product ID", "product_id", "string", {"summarize": "none"}),
            ("Category", "category_name_en", "string", {"summarize": "none"}),
            ("Category (PT)", "category_name_pt", "string", {"summarize": "none"}),
        ],
    },
    {
        "name": "Order Status", "dbt": "fct_orders",
        "desc": "Distinct Olist order statuses with a display group.",
        "cols": [
            ("order_status", "order_status", "string", KEY),
            ("Order Status", "Order Status", "string", {"summarize": "none"}),
            ("Status Group", "Status Group", "string", {"summarize": "none"}),
        ],
        "select": ["order_status"],
        "steps": [
            "Distinct = Table.Distinct(Selected)",
            'Named = Table.AddColumn(Distinct, "Order Status", each Text.Proper([order_status]), type text)',
            'Grouped = Table.AddColumn(Named, "Status Group", each if List.Contains({"canceled", "unavailable"}, [order_status]) then "Canceled / Unavailable" else if [order_status] = "delivered" then "Delivered" else "In Progress", type text)',
        ],
    },
    {
        "name": "Date", "dbt": "dim_date", "date_table": True,
        "desc": "Warehouse calendar core.dim_date (spine 2016-01-01..2019-12-31). Marked as date table on Date.",
        "cols": [
            ("date_key", "date_key", "int64", KEY),
            ("Date", "date_day", "dateTime", {"summarize": "none", "fmt": "yyyy-mm-dd", "key": True}),
            ("Year", "year", "int64", {"summarize": "none", "fmt": "0"}),
            ("Quarter", "quarter", "int64", {"summarize": "none", "fmt": "0"}),
            ("Month No", "month", "int64", {"hidden": True, "summarize": "none", "fmt": "0"}),
            ("Month", "month_name", "string", {"summarize": "none", "sortby": "Month No"}),
            ("Month Start", "month_start", "dateTime", {"hidden": True, "summarize": "none", "fmt": "yyyy-mm-dd"}),
            ("Year Month", "year_month", "string", {"summarize": "none", "sortby": "Month Start"}),
        ],
        "steps": ['Typed = Table.TransformColumnTypes(Selected, {{"date_day", type date}, {"month_start", type date}})'],
    },
]

TABLES.append({
    "name": "DQ Results", "dbt": "dq_results", "optional": True,
    "desc": "core.dq_results: one row per run_id x check_id, appended history. Standalone: no relationships to the Olist star.",
    "cols": [
        ("Run ID", "run_id", "string", {"summarize": "none"}),
        ("Run At", "run_at", "dateTime", {"summarize": "none", "fmt": "yyyy-mm-dd hh:nn"}),
        ("check_id", "check_id", "string", KEY),
        ("Check", "check_name", "string", {"summarize": "none"}),
        ("Layer", "layer", "string", {"summarize": "none"}),
        ("Model", "model_name", "string", {"summarize": "none"}),
        ("KPI ID", "kpi_id", "string", {"summarize": "none"}),
        ("Severity", "severity", "string", {"summarize": "none"}),
        ("weight", "weight", "double", {"hidden": True, "summarize": "none"}),
        ("Status", "status", "string", {"summarize": "none"}),
        ("failing_rows", "failing_rows", "int64", {"hidden": True, "summarize": "none"}),
        ("source_value", "source_value", "double", {"hidden": True, "summarize": "none"}),
        ("mart_value", "mart_value", "double", {"hidden": True, "summarize": "none"}),
        ("variance", "variance", "double", {"hidden": True, "summarize": "none"}),
    ],
    "steps": ['Typed = Table.TransformColumnTypes(Selected, {{"run_id", type text}, {"check_id", type text}, {"run_at", type datetime}, {"weight", type number}, {"failing_rows", Int64.Type}, {"source_value", type number}, {"mart_value", type number}, {"variance", type number}})'],
})

if USE_DQ_RUN_SUMMARY:
    TABLES.append({
        "name": "DQ Run Summary", "dbt": "dq_run_summary", "optional": True,
        "desc": "core.dq_run_summary: one row per dbt run with strict weighted dq_score (warn earns 0) and is_latest_run. Standalone from the Olist star; filters DQ Results by run_id.",
        "cols": [
            ("Run ID", "run_id", "string", {"summarize": "none"}),
            ("Run At", "run_at", "dateTime", {"summarize": "none", "fmt": "yyyy-mm-dd hh:nn"}),
            ("Total Checks", "total_checks", "int64", {"summarize": "none"}),
            ("Passed Checks", "passed_checks", "int64", {"summarize": "none"}),
            ("Warned Checks", "warned_checks", "int64", {"summarize": "none"}),
            ("Failed Checks", "failed_checks", "int64", {"summarize": "none"}),
            ("Failed Blocking Checks", "failed_block_checks", "int64", {"summarize": "none"}),
            ("total_weight", "total_weight", "double", {"hidden": True, "summarize": "none"}),
            ("passed_weight", "passed_weight", "double", {"hidden": True, "summarize": "none"}),
            ("warned_weight", "warned_weight", "double", {"hidden": True, "summarize": "none"}),
            ("dq_score", "dq_score", "double", {"hidden": True, "summarize": "none", "fmt": "0.0%"}),
            ("is_latest_run", "is_latest_run", "boolean", {"hidden": True, "summarize": "none"}),
        ],
        "steps": ['Typed = Table.TransformColumnTypes(Selected, {{"run_id", type text}, {"run_at", type datetime}, {"total_checks", Int64.Type}, {"passed_checks", Int64.Type}, {"warned_checks", Int64.Type}, {"failed_checks", Int64.Type}, {"failed_block_checks", Int64.Type}, {"total_weight", type number}, {"passed_weight", type number}, {"warned_weight", type number}, {"dq_score", type number}, {"is_latest_run", type logical}})'],
    })

if DATE_COMPLETE_FLAG_COLUMN:
    _date = next(t for t in TABLES if t["name"] == "Date")
    _date["cols"].append((DATE_COMPLETE_FLAG_COLUMN, DATE_COMPLETE_FLAG_COLUMN, "boolean", {"hidden": True, "summarize": "none"}))

# --------------------------------------------------------------------------------------
# UCI Online Retail II (GBP) -- separate domain. NO relationship to any Olist table.
# --------------------------------------------------------------------------------------
UCI_PREFIX = "UCI "
UCI_MEASURES_TABLE = "_Measures UCI"
U = {"schema": "PgSchemaUci"}
UM = {"schema": "PgSchemaUciMarts"}
UCI_TABLES: list[dict] = [
    {**U, "name": "UCI Invoice Line", "dbt": "uci_fct_invoice_lines",
     "desc": "UCI fact at invoice-line grain (1,033,036 deduplicated lines). GBP. Source of all value measures.",
     "cols": [
         ("uci_product_sk", "uci_product_sk", "string", KEY),
         ("uci_customer_sk", "uci_customer_sk", "string", KEY),
         ("uci_country_sk", "uci_country_sk", "string", KEY),
         ("invoice_date_key", "invoice_date_key", "int64", KEY),
         ("line_value", "line_value", "decimal", {"hidden": True, "summarize": "none", "fmt": "#,0.00"}),
         ("quantity", "quantity", "int64", {"hidden": True, "summarize": "none"}),
         ("is_cancellation", "is_cancellation", "boolean", {"hidden": True, "summarize": "none"}),
         ("is_product_line", "is_product_line", "boolean", {"hidden": True, "summarize": "none"}),
         ("has_customer", "has_customer", "boolean", {"hidden": True, "summarize": "none"}),
         ("Line Type", "line_type", "string", {"summarize": "none"}),
     ]},
    {**U, "name": "UCI Invoice", "dbt": "uci_fct_invoices",
     "desc": "UCI fact at invoice grain (C-prefixed invoices = cancellations). Source of invoice/customer counts. GBP.",
     "cols": [
         ("Invoice", "invoice", "string", {"summarize": "none"}),
         ("uci_customer_sk", "uci_customer_sk", "string", KEY),
         ("uci_country_sk", "uci_country_sk", "string", KEY),
         ("invoice_date_key", "invoice_date_key", "int64", KEY),
         ("has_customer", "has_customer", "boolean", {"hidden": True, "summarize": "none"}),
         ("is_cancellation", "is_cancellation", "boolean", {"hidden": True, "summarize": "none"}),
         ("product_line_count", "product_line_count", "int64", {"hidden": True, "summarize": "none"}),
         ("product_units", "product_units", "int64", {"hidden": True, "summarize": "none"}),
     ],
     "steps": ['Typed = Table.TransformColumnTypes(Selected, {{"invoice", type text}})']},
    {**U, "name": "UCI Date", "dbt": "uci_dim_date", "date_table": True,
     "desc": "UCI-only calendar (uci_dim_date, 2009-01-01..2012-12-31). Never shared with Olist. Trends filter is_reporting_month = TRUE (excludes partial 2011-12).",
     "cols": [
         ("date_key", "date_key", "int64", KEY),
         ("Date", "date_day", "dateTime", {"summarize": "none", "fmt": "yyyy-mm-dd", "key": True}),
         ("Year", "year", "int64", {"summarize": "none", "fmt": "0"}),
         ("Month No", "month", "int64", {"hidden": True, "summarize": "none", "fmt": "0"}),
         ("Month", "month_name", "string", {"summarize": "none", "sortby": "Month No"}),
         ("Month Start", "month_start", "dateTime", {"hidden": True, "summarize": "none", "fmt": "yyyy-mm-dd"}),
         ("Year Month", "year_month", "string", {"summarize": "none", "sortby": "Month Start"}),
         ("is_complete_month", "is_complete_month", "boolean", {"hidden": True, "summarize": "none"}),
         ("is_reporting_month", "is_reporting_month", "boolean", {"hidden": True, "summarize": "none"}),
     ],
     "steps": ['Typed = Table.TransformColumnTypes(Selected, {{"date_day", type date}, {"month_start", type date}})']},
    {**U, "name": "UCI Customer", "dbt": "uci_dim_customer",
     "desc": "UCI customer (Customer ID); unknown member -1 = lines without Customer ID (is_identified = false). UCI only.",
     "cols": [
         ("uci_customer_sk", "uci_customer_sk", "string", KEY),
         ("Customer ID", "customer_id", "int64", {"summarize": "none", "fmt": "0"}),
         ("is_identified", "is_identified", "boolean", {"hidden": True, "summarize": "none"}),
         ("Primary Country", "primary_country", "string", {"summarize": "none"}),
         ("First Purchase Month", "first_purchase_month", "dateTime", {"summarize": "none", "fmt": "yyyy-mm"}),
         ("is_repeat_customer", "is_repeat_customer", "boolean", {"hidden": True, "summarize": "none"}),
     ],
     "steps": ['Typed = Table.TransformColumnTypes(Selected, {{"first_purchase_month", type date}})']},
    {**U, "name": "UCI Product", "dbt": "uci_dim_product",
     "desc": "UCI stock code with most frequent description. UCI only (never Olist Product).",
     "cols": [
         ("uci_product_sk", "uci_product_sk", "string", KEY),
         ("Stock Code", "stock_code", "string", {"summarize": "none"}),
         ("Description", "description", "string", {"summarize": "none"}),
         ("Primary Line Type", "primary_line_type", "string", {"summarize": "none"}),
     ]},
    {**U, "name": "UCI Country", "dbt": "uci_dim_country",
     "desc": "UCI invoice country ('Unspecified' kept as its own member). UCI only (never Olist Geography).",
     "cols": [
         ("uci_country_sk", "uci_country_sk", "string", KEY),
         ("Country", "country", "string", {"summarize": "none"}),
         ("is_domestic", "is_domestic", "boolean", {"hidden": True, "summarize": "none"}),
         ("ISO Alpha-2", "iso_alpha2", "string", {"summarize": "none"}),
     ]},
    {**UM, "name": "UCI Cohort", "dbt": "uci_mart_customer_cohorts",
     "desc": "uci_mart_customer_cohorts: first-purchase cohort month x months since first purchase. Standalone (no relationships).",
     "cols": [
         ("Cohort Month", "cohort_month", "dateTime", {"summarize": "none", "fmt": "yyyy-mm"}),
         ("Months Since First Purchase", "months_since_first_purchase", "int64", {"summarize": "none"}),
         ("Active Month", "active_month", "dateTime", {"summarize": "none", "fmt": "yyyy-mm"}),
         ("cohort_customers", "cohort_customers", "int64", {"hidden": True, "summarize": "none"}),
         ("active_customers", "active_customers", "int64", {"hidden": True, "summarize": "none"}),
     ],
     "steps": ['Typed = Table.TransformColumnTypes(Selected, {{"cohort_month", type date}, {"active_month", type date}})']},
    {**UM, "name": "UCI RFM", "dbt": "uci_mart_customer_rfm",
     "desc": "uci_mart_customer_rfm: one row per identified customer at snapshot 2011-12-10. Descriptive NTILE(5) scores, not a prediction. Standalone.",
     "cols": [
         ("Customer ID", "customer_id", "int64", {"summarize": "none", "fmt": "0"}),
         ("R Score", "r_score", "int64", {"summarize": "none"}),
         ("F Score", "f_score", "int64", {"summarize": "none"}),
         ("M Score", "m_score", "int64", {"summarize": "none"}),
         ("Recency Days", "recency_days", "int64", {"summarize": "none"}),
         ("Frequency", "frequency", "int64", {"summarize": "none"}),
         ("monetary_net_sales_proxy_gbp", "monetary_net_sales_proxy_gbp", "decimal", {"hidden": True, "summarize": "none", "fmt": "#,0.00"}),
     ]},
]
TABLES.extend(UCI_TABLES)
UCI_TABLE_NAMES = {t["name"] for t in UCI_TABLES} | {UCI_MEASURES_TABLE}
UCI_RELS = [
    ("UCI Invoice Line", "uci_product_sk", "UCI Product", "uci_product_sk", True),
    ("UCI Invoice Line", "uci_customer_sk", "UCI Customer", "uci_customer_sk", True),
    ("UCI Invoice Line", "uci_country_sk", "UCI Country", "uci_country_sk", True),
    ("UCI Invoice Line", "invoice_date_key", "UCI Date", "date_key", True),
    ("UCI Invoice", "uci_customer_sk", "UCI Customer", "uci_customer_sk", True),
    ("UCI Invoice", "uci_country_sk", "UCI Country", "uci_country_sk", True),
    ("UCI Invoice", "invoice_date_key", "UCI Date", "date_key", True),
]

ROLES = [
    # DEMO ONLY: static filter. Geography -> Customer -> Order -> Order Item / Payment / Delivery.
    ("State Manager (demo)", "DEMO ONLY: static row filter to customer state SP. Replace with a user-to-state mapping table + USERPRINCIPALNAME() for production.",
     [("Geography", '[State] = "SP"'), ("DQ Results", "FALSE ()")] + ([("DQ Run Summary", "FALSE ()")] if USE_DQ_RUN_SUMMARY else [])
     + [(t["name"], "FALSE ()") for t in UCI_TABLES]),
]

# Relationships: (from table, from col [many], to table, to col [one], active)
RELS = [
    ("Order Item", "order_id", "Order", "Order ID", True),
    ("Order Item", "product_sk", "Product", "product_sk", True),
    ("Order Item", "seller_sk", "Seller", "seller_sk", True),
    ("Payment", "order_id", "Order", "Order ID", True),
    ("Delivery", "order_id", "Order", "Order ID", True),
    ("Order", "customer_sk", "Customer", "customer_sk", True),
    ("Order", "order_status", "Order Status", "order_status", True),
    ("Order", "purchase_date_key", "Date", "date_key", True),
    ("Customer", "customer_state", "Geography", "State", True),
] + ([("DQ Results", "Run ID", "DQ Run Summary", "Run ID", True)] if USE_DQ_RUN_SUMMARY else []) + [
] + UCI_RELS

BRL = "R$ #,0"
BRL2 = "R$ #,0.00"
PCT = "0.0%"
INT = "#,0"



def line_aware(expr: list[str]) -> list[str]:
    """Order-grain measure that must also respond to Product/Seller filters.

    Product and Seller filter only Order Item (many side of Order). When either is cross-filtered,
    the expression runs with a bidirectional Order Item<->Order filter so it counts the orders that
    contain the filtered lines; otherwise it runs unchanged (orders without items stay included).
    """
    body = ["    " + e for e in expr]
    return (["VAR _lineFiltered = ISCROSSFILTERED ( 'Product' ) || ISCROSSFILTERED ( 'Seller' )",
             "RETURN", "    IF (", "        _lineFiltered,", "        CALCULATE ("]
            + ["        " + b for b in body[:-1]] + ["        " + body[-1] + ","]
            + ["            CROSSFILTER ( 'Order Item'[order_id], 'Order'[Order ID], BOTH )", "        ),"]
            + ["    " + b for b in body[:-1]] + ["    " + body[-1]] + ["    )"])


def latest_run(expr: list[str]) -> list[str]:
    """DQ measure evaluated on the latest run unless a run (Run ID / Run At) is in the filter context."""
    sel = "ISFILTERED ( 'DQ Results'[Run ID] ) || ISFILTERED ( 'DQ Results'[Run At] )"
    if USE_DQ_RUN_SUMMARY:
        sel += " || ISFILTERED ( 'DQ Run Summary'[Run ID] ) || ISFILTERED ( 'DQ Run Summary'[Run At] )"
    extra = ["        REMOVEFILTERS ( 'DQ Run Summary' ),"] if USE_DQ_RUN_SUMMARY else []
    return ([f"VAR _runSelected = {sel}",
             "VAR _runAt =",
             "    IF (",
             "        _runSelected,",
             "        MAX ( 'DQ Results'[Run At] ),",
             "        CALCULATE ( MAX ( 'DQ Results'[Run At] ), REMOVEFILTERS ( 'DQ Results' ) )",
             "    )",
             "RETURN",
             "    CALCULATE ("]
            + ["        " + e for e in expr[:-1]] + ["        " + expr[-1] + ","]
            + extra + ["        REMOVEFILTERS ( 'DQ Results'[Run ID] ),",
               "        'DQ Results'[Run At] = _runAt", "    )"])


growth = ["VAR _current = [GMV]",
          "VAR _previous = CALCULATE ( [GMV], DATEADD ( 'Date'[Date], -1, MONTH ) )"]
if DATE_COMPLETE_FLAG_COLUMN:
    growth += [f"VAR _currentIncomplete = CALCULATE ( COUNTROWS ( 'Date' ), KEEPFILTERS ( 'Date'[{DATE_COMPLETE_FLAG_COLUMN}] = FALSE () ) ) > 0",
               f"VAR _previousIncomplete = CALCULATE ( COUNTROWS ( 'Date' ), DATEADD ( 'Date'[Date], -1, MONTH ), KEEPFILTERS ( 'Date'[{DATE_COMPLETE_FLAG_COLUMN}] = FALSE () ) ) > 0"]
growth_cond = "ISBLANK ( _current ) || ISBLANK ( _previous ) || _previous = 0" + (
    " || _currentIncomplete || _previousIncomplete" if DATE_COMPLETE_FLAG_COLUMN else "")
growth += ["RETURN", f"    IF ( {growth_cond}, BLANK (), DIVIDE ( _current - _previous, _previous ) )"]

HIDDEN_MEASURES = {"DQ Status Colour"}
MM = "KEEPFILTERS ( ABS ( 'Order'[payment_vs_items_diff] ) > 0.01 )"
ELIG = "KEEPFILTERS ( 'Delivery'[is_otd_eligible] = TRUE () )"
MEASURES = [
    # (folder, name, kpi_id, status, fmt, expression lines, description)
    ("Sales", "GMV", "KPI_GMV", "SUPPORTED", BRL, ["SUM ( 'Order Item'[item_price] )"],
     "Gross Merchandise Value: SUM(item_price), freight excluded. Not recognized revenue."),
    ("Sales", "GMV incl Freight", "KPI_GMV_INCL_FREIGHT", "SUPPORTED", BRL, ["[GMV] + [Freight Value]"],
     "GMV plus customer-paid freight."),
    ("Sales", "Net GMV", "KPI_NET_GMV", "SUPPORTED", BRL,
     ["CALCULATE (", "    [GMV],", "    KEEPFILTERS ( NOT 'Order'[order_status] IN { \"canceled\", \"unavailable\" } )", ")"],
     "GMV of orders not canceled/unavailable."),
    ("Sales", "Freight Value", "KPI_FREIGHT", "SUPPORTED", BRL, ["SUM ( 'Order Item'[freight_value] )"],
     "Freight charged to customers (customer freight, not logistics cost)."),
    ("Sales", "Freight Share %", "KPI_FREIGHT_SHARE", "SUPPORTED", PCT, ["DIVIDE ( [Freight Value], [GMV] )"],
     "Freight Value / GMV (ratio of sums)."),
    ("Sales", "GMV Growth %", "KPI_GMV_GROWTH", "PARTIAL", PCT, growth,
     "Month-over-month GMV growth on calendar months by purchase date (evaluate at Year Month). BLANK when prior GMV is 0/blank"
     + (" or when the current or prior month is not complete (dim_date.is_complete_month = false)." if DATE_COMPLETE_FLAG_COLUMN else "; partial-month suppression disabled.")
     + " PARTIAL: first/last coverage months are partial and sparse."),
    ("Payments", "Payment Value", "KPI_PAYMENT_VALUE", "SUPPORTED", BRL, ["SUM ( 'Payment'[payment_value] )"],
     "Sum of recorded payments. Transaction value, not sales, not cash flow; does not reconcile to items+freight for some orders."),
    ("Payments", "Payment Mix %", "KPI_PAYMENT_VALUE", "SUPPORTED", PCT,
     ["DIVIDE (", "    [Payment Value],", "    CALCULATE ( [Payment Value], REMOVEFILTERS ( 'Payment'[Payment Type] ) )", ")"],
     "Supporting measure: share of Payment Value by payment type. Payment mix, never sales."),
    ("Orders", "Orders", "KPI_ORDERS", "SUPPORTED", INT, line_aware(["COUNTROWS ( 'Order' )"]),
     "Distinct orders (fct_orders unique on order_id). Under Product/Seller filters counts orders containing those lines."),
    ("Orders", "Items Sold", "KPI_ITEMS_PER_ORDER", "SUPPORTED", INT, ["COUNTROWS ( 'Order Item' )"],
     "Supporting measure: order lines (= units; Olist has one unit per line). Numerator of Items per Order."),
    ("Orders", "AOV", "KPI_AOV", "SUPPORTED", BRL2,
     ["VAR _ordersWithItems = DISTINCTCOUNT ( 'Order Item'[order_id] )", "RETURN", "    DIVIDE ( [GMV], _ordersWithItems )"],
     "GMV / distinct orders with items (ratio of sums)."),
    ("Orders", "Items per Order", "KPI_ITEMS_PER_ORDER", "SUPPORTED", "#,0.00",
     ["DIVIDE ( [Items Sold], DISTINCTCOUNT ( 'Order Item'[order_id] ) )"],
     "Order lines / distinct orders with items."),
    ("Orders", "Cancellation Rate %", "KPI_CANCEL_RATE", "SUPPORTED", PCT,
     ["VAR _canceled =", "    CALCULATE ( [Orders], KEEPFILTERS ( 'Order'[order_status] IN { \"canceled\", \"unavailable\" } ) )",
      "RETURN", "    DIVIDE ( _canceled, [Orders] )"],
     "Orders canceled or unavailable / Orders."),
    ("Orders", "Avg Approval Hours", "KPI_APPROVAL_HOURS", "SUPPORTED", "#,0.0",
     line_aware(["CALCULATE ( AVERAGE ( 'Order'[hours_to_approve] ), KEEPFILTERS ( 'Order'[hours_to_approve] >= 0 ) )"]),
     "Average hours purchase -> approval (negative values excluded)."),
    ("Customers", "Active Customers", "KPI_ACTIVE_CUSTOMERS", "SUPPORTED", INT,
     line_aware(["DISTINCTCOUNT ( 'Order'[customer_sk] )"]),
     "Distinct customer_unique_id (via customer_sk) with >=1 order in context."),
    ("Customers", "New Customers", "KPI_NEW_CUSTOMERS", "SUPPORTED", INT,
     ["VAR _start = MIN ( 'Date'[Date] )", "VAR _end = MAX ( 'Date'[Date] )", "RETURN",
      "    CALCULATE (", "        COUNTROWS ( 'Customer' ),", "        'Order',",
      "        KEEPFILTERS ( 'Customer'[First Order Date] >= _start && 'Customer'[First Order Date] <= _end )", "    )"],
     "Active customers whose first order date falls in the selected period (by month = first-order cohort size)."),
    ("Customers", "Repeat Purchase Rate %", "KPI_REPEAT_RATE", "SUPPORTED", PCT,
     ["VAR _customers = VALUES ( 'Order'[customer_sk] )",
      "VAR _repeat = COUNTROWS ( FILTER ( _customers, CALCULATE ( COUNTROWS ( 'Order' ) ) >= 2 ) )",
      "RETURN", "    DIVIDE ( _repeat, COUNTROWS ( _customers ) )"],
     "Customers (customer_unique_id) with 2+ distinct orders within the selected period / active customers in the period."),
    ("Customers", "Customer Retention %", "KPI_CUSTOMER_RETENTION", "PARTIAL", PCT,
     ["VAR _current = VALUES ( 'Order'[customer_sk] )",
      "VAR _prior = CALCULATETABLE ( VALUES ( 'Order'[customer_sk] ), DATEADD ( 'Date'[Date], -1, MONTH ) )",
      "RETURN", "    DIVIDE ( COUNTROWS ( INTERSECT ( _current, _prior ) ), COUNTROWS ( _prior ) )"],
     "Customers active in the previous calendar month who order again in the current month / previous-month active. Evaluate at Year Month. PARTIAL: unstable on Olist's low repeat volume; show with [Retention Cohort Size]."),
    ("Customers", "Retention Cohort Size", "KPI_CUSTOMER_RETENTION", "PARTIAL", INT,
     ["CALCULATE ( [Active Customers], DATEADD ( 'Date'[Date], -1, MONTH ) )"],
     "Supporting measure: denominator of Customer Retention % (previous-month active customers)."),
    ("Delivery", "On-Time Delivery %", "KPI_OTD_RATE", "SUPPORTED", PCT,
     line_aware(["DIVIDE (", f"    CALCULATE ( COUNTROWS ( 'Delivery' ), {ELIG}, KEEPFILTERS ( 'Delivery'[is_on_time] = TRUE () ) ),",
                 f"    CALCULATE ( COUNTROWS ( 'Delivery' ), {ELIG} )", ")"]),
     "Eligible orders (is_otd_eligible: delivered, delivered_customer_at present and >= purchased_at) delivered on/before the estimated date (date comparison) / eligible orders. Estimate is Olist's, not a contractual SLA. Dated by purchase date."),
    ("Delivery", "On-Time Delivery % (by Delivery Date)", "KPI_OTD_RATE", "SUPPORTED", PCT,
     ["CALCULATE (", "    [On-Time Delivery %],", "    REMOVEFILTERS ( 'Date' ),",
      "    TREATAS ( VALUES ( 'Date'[date_key] ), 'Delivery'[delivered_date_key] )", ")"],
     "Supporting measure: same KPI on the delivery-date role. The Date selection is moved from the purchase date (Date->Order) to Delivery[delivered_date_key] via TREATAS; Customer, Geography, Status and RLS still reach Delivery through Order."),
    ("Delivery", "Late Orders", "KPI_OTD_RATE", "SUPPORTED", INT,
     line_aware([f"CALCULATE ( COUNTROWS ( 'Delivery' ), {ELIG}, KEEPFILTERS ( 'Delivery'[is_on_time] = FALSE () ) )"]),
     "Supporting measure: eligible orders delivered after the estimated date (complement of the OTD numerator)."),
    ("Delivery", "Seller Handover On-Time %", "KPI_SELLER_HANDOVER_OTD", "PARTIAL", PCT,
     ["DIVIDE (", "    CALCULATE ( COUNTROWS ( 'Order Item' ), KEEPFILTERS ( 'Order Item'[is_handover_on_time] = TRUE () ) ),",
      "    CALCULATE ( COUNTROWS ( 'Order Item' ), KEEPFILTERS ( NOT ISBLANK ( 'Order Item'[is_handover_on_time] ) ) )", ")"],
     "Order items handed to the carrier (fct_deliveries.delivered_carrier_at) at or before the item's shipping_limit_at (full timestamp comparison, computed in dbt as fct_order_items.is_handover_on_time) / items with both timestamps. shipping_limit_at is Olist's seller shipping deadline, not a contractual SLA. PARTIAL: carrier handover is recorded per order, so sellers in multi-seller orders share one handover time."),
    ("Data Quality", "Handover Missing Timestamp", "KPI_SELLER_HANDOVER_OTD", "PARTIAL", INT,
     ["CALCULATE ( COUNTROWS ( 'Order Item' ), KEEPFILTERS ( ISBLANK ( 'Order Item'[is_handover_on_time] ) ) )"],
     "Data-quality exclusion count, not an operational KPI: order items missing delivered_carrier_at or shipping_limit_at (is_handover_on_time is NULL), excluded from Seller Handover On-Time %."),
    ("Delivery", "Avg Delivery Days", "KPI_DELIVERY_DAYS", "SUPPORTED", "#,0.0",
     line_aware([f"CALCULATE ( AVERAGE ( 'Delivery'[delivery_days] ), {ELIG} )"]),
     "Average days purchase -> customer delivery over is_otd_eligible orders only (same filter as OTD)."),
    ("Reviews", "Avg Review Score", "KPI_REVIEW_SCORE", "SUPPORTED", "0.00",
     line_aware(["AVERAGE ( 'Order'[Review Score] )"]),
     "Mean latest review score per order (fct_orders.latest_review_score), 1-5. CSAT proxy, not surveyed CSAT."),
    ("Reviews", "Low Review %", "KPI_LOW_REVIEW_RATE", "SUPPORTED", PCT,
     line_aware(["DIVIDE (", "    CALCULATE ( COUNTROWS ( 'Order' ), KEEPFILTERS ( NOT ISBLANK ( 'Order'[Review Score] ) && 'Order'[Review Score] <= 2 ) ),",
                 "    CALCULATE ( COUNTROWS ( 'Order' ), KEEPFILTERS ( NOT ISBLANK ( 'Order'[Review Score] ) ) )", ")"]),
     "Orders with latest score <= 2 / orders reviewed."),
    # ---- Data quality (core.dq_results, latest run unless a run is selected)
    ("Data Quality", "DQ Score %", "KPI_DQ_SCORE", "SUPPORTED", PCT,
     (["VAR _runSelected = ISFILTERED ( 'DQ Run Summary'[Run ID] ) || ISFILTERED ( 'DQ Run Summary'[Run At] )",
       "VAR _runAt =", "    IF (", "        _runSelected,", "        MAX ( 'DQ Run Summary'[Run At] ),",
       "        CALCULATE ( MAX ( 'DQ Run Summary'[Run At] ), REMOVEFILTERS ( 'DQ Run Summary' ), 'DQ Run Summary'[is_latest_run] = TRUE () )",
       "    )", "RETURN",
       "    CALCULATE ( MAX ( 'DQ Run Summary'[dq_score] ), REMOVEFILTERS ( 'DQ Run Summary' ), 'DQ Run Summary'[Run At] = _runAt )"]
      if USE_DQ_RUN_SUMMARY else
      latest_run(["DIVIDE (", "    CALCULATE ( SUM ( 'DQ Results'[weight] ), KEEPFILTERS ( 'DQ Results'[Status] = \"pass\" ) ),",
                  "    SUM ( 'DQ Results'[weight] )", ")"])),
     ("Strict weighted DQ score from core.dq_run_summary.dq_score (only pass earns weight; warn and fail earn 0). Latest run (is_latest_run = TRUE) unless a run is selected; if several runs are selected, the latest of them."
      if USE_DQ_RUN_SUMMARY else
      "Sum of weights of checks with status pass / sum of all weights (warn counts as not pass). Latest run_at unless a run is selected.")),
    ("Data Quality", "Reconciliation Variance", "KPI_RECON_VARIANCE", "SUPPORTED", "#,0.00",
     latest_run(["SUMX (", "    FILTER ( 'DQ Results', NOT ISBLANK ( 'DQ Results'[source_value] ) ),",
                 "    'DQ Results'[mart_value] - 'DQ Results'[source_value]", ")"]),
     "Sum of (mart_value - source_value) over checks with a source_value; slice by KPI ID. Latest run unless a run is selected."),
    ("Data Quality", "Checks Failed", "KPI_DQ_SCORE", "SUPPORTED", INT,
     latest_run(["CALCULATE ( COUNTROWS ( 'DQ Results' ), KEEPFILTERS ( 'DQ Results'[Status] = \"fail\" ) )"]),
     "Supporting measure: checks with status fail in the latest (or selected) run."),
    ("Data Quality", "Checks Warned", "KPI_DQ_SCORE", "SUPPORTED", INT,
     latest_run(["CALCULATE ( COUNTROWS ( 'DQ Results' ), KEEPFILTERS ( 'DQ Results'[Status] = \"warn\" ) )"]),
     "Supporting measure: checks with status warn in the latest (or selected) run."),
    ("Data Quality", "Blocking Failures", "KPI_DQ_SCORE", "SUPPORTED", INT,
     latest_run(["CALCULATE (", "    COUNTROWS ( 'DQ Results' ),", "    KEEPFILTERS ( 'DQ Results'[Status] = \"fail\" ),",
                 "    KEEPFILTERS ( 'DQ Results'[Severity] = \"block\" )", ")"]),
     "Supporting measure: failed checks with severity block in the latest (or selected) run."),
    ("Data Quality", "Failing Rows", "KPI_DQ_SCORE", "SUPPORTED", INT,
     latest_run(["SUM ( 'DQ Results'[failing_rows] )"]),
     "Supporting measure: sum of failing_rows in the latest (or selected) run."),
    ("Data Quality", "DQ Status Colour", "KPI_DQ_SCORE", "SUPPORTED", "",
     latest_run(["SWITCH (", "    SELECTEDVALUE ( 'DQ Results'[Status] ),", "    \"pass\", \"#10B981\",",
                 "    \"warn\", \"#F59E0B\",", "    \"fail\", \"#EF4444\",", "    \"#64748B\"", ")"]),
     "Formatting helper only (not a KPI): hex status colour for conditional formatting of the checks table. Hidden."),
    ("Data Quality", "Payment Mismatch Orders", "KPI_PAYMENT_VALUE", "SUPPORTED", INT,
     ["CALCULATE ( COUNTROWS ( 'Order' ), KEEPFILTERS ( ABS ( 'Order'[payment_vs_items_diff] ) > 0.01 ) )"],
     "Data-quality exclusion count (validation rule of KPI_PAYMENT_VALUE), not sales: orders where |sum(payment_value) - sum(item_price + freight_value)| > 0.01 BRL. fct_orders.payment_vs_items_diff = coalesce(payments,0) - coalesce(items+freight,0), so orders missing either side count. Baseline: 1,076 orders."),
    ("Data Quality", "Payment Without Items Orders", "KPI_PAYMENT_VALUE", "SUPPORTED", INT,
     [f"CALCULATE ( COUNTROWS ( 'Order' ), {MM}, KEEPFILTERS ( 'Order'[has_items] = FALSE () ) )"],
     "Data-quality exclusion count (KPI_PAYMENT_VALUE exception breakdown): mismatched orders with payments but no order items."),
    ("Data Quality", "Items Without Payment Orders", "KPI_PAYMENT_VALUE", "SUPPORTED", INT,
     [f"CALCULATE ( COUNTROWS ( 'Order' ), {MM}, KEEPFILTERS ( 'Order'[has_items] = TRUE () ), KEEPFILTERS ( 'Order'[has_payment] = FALSE () ) )"],
     "Data-quality exclusion count (KPI_PAYMENT_VALUE exception breakdown): mismatched orders with items but no payment record."),
    ("Data Quality", "Overpaid Orders", "KPI_PAYMENT_VALUE", "SUPPORTED", INT,
     [f"CALCULATE ( COUNTROWS ( 'Order' ), {MM}, KEEPFILTERS ( 'Order'[has_items] = TRUE () ), KEEPFILTERS ( 'Order'[has_payment] = TRUE () ), KEEPFILTERS ( 'Order'[payment_vs_items_diff] > 0 ) )"],
     "Data-quality exclusion count (KPI_PAYMENT_VALUE exception breakdown): both sides present, payments exceed items+freight by > 0.01 BRL (e.g. installment interest)."),
    ("Data Quality", "Underpaid Orders", "KPI_PAYMENT_VALUE", "SUPPORTED", INT,
     [f"CALCULATE ( COUNTROWS ( 'Order' ), {MM}, KEEPFILTERS ( 'Order'[has_items] = TRUE () ), KEEPFILTERS ( 'Order'[has_payment] = TRUE () ), KEEPFILTERS ( 'Order'[payment_vs_items_diff] < 0 ) )"],
     "Data-quality exclusion count (KPI_PAYMENT_VALUE exception breakdown): both sides present, payments below items+freight by > 0.01 BRL (e.g. vouchers/discounts)."),
    ("Data Quality", "Delivered Missing Timestamp", "KPI_OTD_RATE", "SUPPORTED", INT,
     ["CALCULATE ( COUNTROWS ( 'Delivery' ), KEEPFILTERS ( 'Delivery'[dq_missing_delivery_ts] = TRUE () ) )"],
     "Data-quality exclusion count, not an operational KPI: delivered orders without delivered_customer_at, excluded from OTD and delivery-days KPIs (fct_deliveries.dq_missing_delivery_ts)."),
    ("Data Quality", "Delivered Before Purchase", "KPI_DELIVERY_DAYS", "SUPPORTED", INT,
     ["CALCULATE ( COUNTROWS ( 'Delivery' ), KEEPFILTERS ( 'Delivery'[dq_delivered_before_purchase] = TRUE () ) )"],
     "Data-quality exclusion count, not an operational KPI: delivery timestamp before purchase, excluded from OTD and delivery-days KPIs (fct_deliveries.dq_delivered_before_purchase)."),
    ("Data Quality", "OTD Eligible Orders", "KPI_OTD_RATE", "SUPPORTED", INT,
     [f"CALCULATE ( COUNTROWS ( 'Delivery' ), {ELIG} )"],
     "Supporting measure: OTD denominator (is_otd_eligible = true)."),
    ("Data Quality", "Payment Records", "KPI_PAYMENT_VALUE", "SUPPORTED", INT, ["COUNTROWS ( 'Payment' )"],
     "Supporting DQ measure: row count of fct_payments in context."),
]

# ---- UCI measures (names / ids / statuses exactly as governance/kpi_dictionary/kpis.yaml v2.0.0, domain uci)
GBP, GBP2 = "£#,0", "£#,0.00"
UF = "UCI Retail (GBP)"
L_ = "'UCI Invoice Line'"
PROD_SALE = f"KEEPFILTERS ( {L_}[is_product_line] = TRUE () ), KEEPFILTERS ( {L_}[is_cancellation] = FALSE () )"
PROD_CANC = f"KEEPFILTERS ( {L_}[is_product_line] = TRUE () ), KEEPFILTERS ( {L_}[is_cancellation] = TRUE () )"
SALES_INV = "KEEPFILTERS ( 'UCI Invoice'[is_cancellation] = FALSE () )"
UCI_MEASURES = [
    (f"{UF}\\Sales", "UCI Gross Product Sales", "KPI_UCI_GROSS_SALES", "SUPPORTED", GBP,
     [f"CALCULATE ( SUM ( {L_}[line_value] ), {PROD_SALE} )"],
     "Invoiced value of product lines on non-cancellation invoices (GBP). Invoiced value, not recognized revenue. Full coverage = 19,643,861.637."),
    (f"{UF}\\Sales", "UCI Product Cancellations", "KPI_UCI_PRODUCT_CANCELLATIONS", "SUPPORTED", GBP,
     [f"CALCULATE ( SUM ( {L_}[line_value] ), {PROD_CANC} )"],
     "Signed (negative) value of product lines on C invoices. Cancellations, not confirmed returns."),
    (f"{UF}\\Sales", "UCI Discounts", "KPI_UCI_DISCOUNTS", "SUPPORTED", GBP,
     [f"CALCULATE ( SUM ( {L_}[line_value] ), KEEPFILTERS ( {L_}[Line Type] = \"discount\" ) )"],
     "Signed value of discount lines (StockCode D)."),
    (f"{UF}\\Sales", "UCI Net Sales (proxy)", "KPI_UCI_NET_SALES_PROXY", "SUPPORTED", GBP,
     ["[UCI Gross Product Sales] + [UCI Product Cancellations] + [UCI Discounts]"],
     "Net Sales (proxy) = gross product sales + product cancellations + discounts (signed); postage and fees excluded. Operational proxy, not recognized revenue. Full coverage = 18,914,519.437."),
    (f"{UF}\\Sales", "UCI Postage", "KPI_UCI_POSTAGE_FEES", "SUPPORTED", GBP,
     [f"CALCULATE ( SUM ( {L_}[line_value] ), KEEPFILTERS ( {L_}[Line Type] = \"postage\" ) )"],
     "Postage lines (POST, DOT, C2), reported separately; excluded from Net Sales (proxy)."),
    (f"{UF}\\Sales", "UCI Fees", "KPI_UCI_POSTAGE_FEES", "SUPPORTED", GBP,
     [f"CALCULATE ( SUM ( {L_}[line_value] ), KEEPFILTERS ( {L_}[Line Type] = \"fee\" ) )"],
     "Fee lines (BANK CHARGES, AMAZONFEE, CRUK), reported separately; excluded from Net Sales (proxy)."),
    (f"{UF}\\Invoices", "UCI Sales Invoices", "KPI_UCI_INVOICES", "SUPPORTED", "#,0",
     [f"CALCULATE ( COUNTROWS ( 'UCI Invoice' ), {SALES_INV} )"],
     "Distinct non-cancellation invoices (all line types). Full coverage = 45,336. Not filtered by UCI Product."),
    (f"{UF}\\Invoices", "UCI AOV", "KPI_UCI_AOV", "SUPPORTED", GBP2,
     ["DIVIDE ( [UCI Net Sales (proxy)], [UCI Sales Invoices] )"],
     "Average invoice value = SUM(net_sales_proxy_gbp) / SUM(sales_invoice_count) at any grain (ratio of sums; never an average of aov_gbp). Full coverage = 417.21. Not meaningful under a UCI Product filter (denominator is invoice-level)."),
    (f"{UF}\\Invoices", "UCI Units per Invoice", "KPI_UCI_UNITS_PER_INVOICE", "SUPPORTED", "#,0.0",
     ["DIVIDE (", f"    CALCULATE ( SUM ( 'UCI Invoice'[product_units] ), {SALES_INV} ),",
      f"    CALCULATE ( COUNTROWS ( 'UCI Invoice' ), {SALES_INV}, KEEPFILTERS ( 'UCI Invoice'[product_line_count] > 0 ) )", ")"],
     "Product units sold / sales invoices with products (ratio of sums)."),
    (f"{UF}\\Cancellations", "UCI Cancellation Rate % (Value)", "KPI_UCI_CANCEL_RATE_VALUE", "SUPPORTED", "0.0%",
     ["DIVIDE ( ABS ( [UCI Product Cancellations] ), [UCI Gross Product Sales] )"],
     "|Product cancellations| / gross product sales (ratio of sums). Period rate with no C->original invoice link; can exceed 100% at fine grain."),
    (f"{UF}\\Cancellations", "UCI Cancellation Rate % (Lines)", "KPI_UCI_CANCEL_RATE_LINES", "SUPPORTED", "0.0%",
     ["DIVIDE (", f"    CALCULATE ( COUNTROWS ( {L_} ), {PROD_CANC} ),",
      f"    CALCULATE ( COUNTROWS ( {L_} ), KEEPFILTERS ( {L_}[is_product_line] = TRUE () ) )", ")"],
     "Product lines on C invoices / all product lines."),
    (f"{UF}\\Cancellations", "UCI Cancellation Rate % (Invoices)", "KPI_UCI_CANCEL_RATE_INVOICES", "SUPPORTED", "0.0%",
     ["DIVIDE (", "    CALCULATE ( COUNTROWS ( 'UCI Invoice' ), KEEPFILTERS ( 'UCI Invoice'[is_cancellation] = TRUE () ) ),",
      "    COUNTROWS ( 'UCI Invoice' )", ")"],
     "Cancellation invoices / (sales invoices + cancellation invoices)."),
    (f"{UF}\\Customers", "UCI Active Customers", "KPI_UCI_ACTIVE_CUSTOMERS", "SUPPORTED", "#,0",
     ["CALCULATE (", "    DISTINCTCOUNT ( 'UCI Invoice'[uci_customer_sk] ),", f"    {SALES_INV},",
      "    KEEPFILTERS ( 'UCI Invoice'[has_customer] = TRUE () )", ")"],
     "Distinct identified customers with >=1 sales invoice in period (identified only; never sum daily counts)."),
    (f"{UF}\\Customers", "UCI New Customers", "KPI_UCI_NEW_CUSTOMERS", "SUPPORTED", "#,0",
     ["VAR _start = MIN ( 'UCI Date'[Date] )", "VAR _end = MAX ( 'UCI Date'[Date] )", "RETURN",
      "    CALCULATE (", "        COUNTROWS ( 'UCI Customer' ),", "        KEEPFILTERS ( 'UCI Customer'[is_identified] = TRUE () ),",
      "        KEEPFILTERS ( 'UCI Customer'[First Purchase Month] >= DATE ( YEAR ( _start ), MONTH ( _start ), 1 ) && 'UCI Customer'[First Purchase Month] <= _end )",
      "    )"],
     "Identified customers whose first purchase month falls in the period. 2009-12 overstated (dataset start, no prior history)."),
    (f"{UF}\\Customers", "UCI Repeat Rate %", "KPI_UCI_REPEAT_RATE", "SUPPORTED", "0.0%",
     ["DIVIDE (", "    CALCULATE ( COUNTROWS ( 'UCI Customer' ), KEEPFILTERS ( 'UCI Customer'[is_identified] = TRUE () ), KEEPFILTERS ( 'UCI Customer'[is_repeat_customer] = TRUE () ) ),",
      "    CALCULATE ( COUNTROWS ( 'UCI Customer' ), KEEPFILTERS ( 'UCI Customer'[is_identified] = TRUE () ) )", ")"],
     "Identified customers with >=2 sales invoices over full coverage (2009-12-01 to 2011-12-09) / identified customers. Not period-sensitive."),
    (f"{UF}\\Customers", "UCI Cohort Retention %", "KPI_UCI_RETENTION", "PARTIAL", "0.0%",
     ["VAR _completeMonths =", "    CALCULATETABLE (", "        VALUES ( 'UCI Date'[Month Start] ),", "        REMOVEFILTERS ( 'UCI Date' ),",
      "        'UCI Date'[is_complete_month] = TRUE ()", "    )", "RETURN", "    CALCULATE (",
      "        DIVIDE ( SUM ( 'UCI Cohort'[active_customers] ), SUM ( 'UCI Cohort'[cohort_customers] ) ),",
      "        TREATAS ( _completeMonths, 'UCI Cohort'[Active Month] )", "    )"],
     "Share of a monthly first-purchase cohort active n months later (read per cohort x months since first purchase). Partial active months (2011-12) are blank. PARTIAL: 2009-12 cohort mixes pre-existing customers; 22.8% of lines without Customer ID excluded."),
    (f"{UF}\\Customers", "UCI Customers by RFM Segment", "KPI_UCI_RFM_SEGMENT", "PARTIAL", "#,0",
     ["COUNTROWS ( 'UCI RFM' )"],
     "Identified customers per R/F/M score combination (NTILE(5), snapshot 2011-12-10). Descriptive, not a prediction. PARTIAL: segment-label rules to be documented by owner."),
    (f"{UF}\\Mix", "UCI Product Contribution %", "KPI_UCI_PRODUCT_CONTRIBUTION", "SUPPORTED", "0.00%",
     ["DIVIDE ( [UCI Gross Product Sales], CALCULATE ( [UCI Gross Product Sales], REMOVEFILTERS ( 'UCI Product' ) ) )"],
     "Product share of gross product sales."),
    (f"{UF}\\Mix", "UCI Country Contribution %", "KPI_UCI_COUNTRY_CONTRIBUTION", "SUPPORTED", "0.0%",
     ["DIVIDE ( [UCI Gross Product Sales], CALCULATE ( [UCI Gross Product Sales], REMOVEFILTERS ( 'UCI Country' ) ) )"],
     "Invoice-country share of gross product sales (UK about 85.5%; non-UK view shown separately)."),
]

CALC_ITEMS = [
    ("Current", ["SELECTEDMEASURE ()"], None),
    ("MTD", ["CALCULATE ( SELECTEDMEASURE (), DATESMTD ( 'Date'[Date] ) )"], None),
    ("QTD", ["CALCULATE ( SELECTEDMEASURE (), DATESQTD ( 'Date'[Date] ) )"], None),
    ("YTD", ["CALCULATE ( SELECTEDMEASURE (), DATESYTD ( 'Date'[Date] ) )"], None),
    ("PY", ["CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( 'Date'[Date] ) )"], None),
    ("YoY", ["VAR _current = SELECTEDMEASURE ()",
             "VAR _py = CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( 'Date'[Date] ) )",
             "RETURN", "    IF ( NOT ISBLANK ( _current ) && NOT ISBLANK ( _py ), _current - _py )"], None),
    ("YoY %", ["VAR _current = SELECTEDMEASURE ()",
               "VAR _py = CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( 'Date'[Date] ) )",
               "RETURN", "    IF ( NOT ISBLANK ( _current ) && NOT ISBLANK ( _py ), DIVIDE ( _current - _py, _py ) )"], '"0.0%"'),
    ("Rolling 12M", ["CALCULATE (", "    SELECTEDMEASURE (),",
                     "    DATESINPERIOD ( 'Date'[Date], MAX ( 'Date'[Date] ), -12, MONTH )", ")"], None),
]


def tmdl_expr(lines: list[str], indent: int) -> str:
    pad = "\t" * indent
    return "\n".join(pad + ln.replace("    ", "\t") if ln.startswith("    ") else pad + ln for ln in lines)


def build_table(t: dict) -> str:
    name = t["name"]
    out = [f"/// {t['desc']}", f"table {q(name)}", f"\tlineageTag: {gid('table', name)}"]
    if t.get("date_table"):
        out.append("\tdataCategory: Time")
    out.append("")
    for cname, src, dtype, o in t["cols"]:
        out.append(f"\tcolumn {q(cname)}")
        out.append(f"\t\tdataType: {dtype}")
        if o.get("key"):
            out.append("\t\tisKey")
        if o.get("hidden"):
            out.append("\t\tisHidden")
        if o.get("fmt"):
            out.append(f"\t\tformatString: {o['fmt']}")
        out.append(f"\t\tlineageTag: {gid('col', name, cname)}")
        out.append(f"\t\tsummarizeBy: {o.get('summarize', 'none')}")
        out.append(f"\t\tsourceColumn: {src}")
        if o.get("sortby"):
            out.append(f"\t\tsortByColumn: {q(o['sortby'])}")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = User")
        out.append("")
    for cname, dtype, expr, cdesc in t.get("calc_cols", []):
        out.append(f"\t/// {cdesc}")
        out.append(f"\tcolumn {q(cname)} =")
        out.append(tmdl_expr(expr, 3))
        out.append(f"\t\tdataType: {dtype}")
        out.append("\t\tisHidden")
        out.append(f"\t\tlineageTag: {gid('col', name, cname)}")
        out.append("\t\tsummarizeBy: none")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = Automatic")
        out.append("")
    select = t.get("select") or [src for _, src, _, _ in t["cols"]]
    m = pg_source(t["dbt"], select, t.get("steps"), optional=t.get("optional", False), schema=t.get("schema", "PgSchema"))
    out.append(f"\tpartition {q(name)} = m")
    out.append("\t\tmode: import")
    out.append("\t\tsource =")
    out.append(tmdl_expr(m, 4))
    out.append("")
    out.append("\tannotation PBI_ResultType = Table")
    out.append("")
    return "\n".join(out)


def build_measures_table(tname: str = "_Measures", measures: list | None = None,
                         tdesc: str = "Home table for all explicit Olist measures (BRL). Names follow docs/kpi-catalog.md; descriptions carry KPI ids.") -> str:
    measures = MEASURES if measures is None else measures
    out = [f"/// {tdesc}", f"table {q(tname)}", f"\tlineageTag: {gid('table', tname)}", ""]
    for folder, name, kid, status, fmt, expr, desc in measures:
        out.append(f"\t/// {kid} ({status}): {desc}")
        if len(expr) == 1:
            out.append(f"\tmeasure {q(name)} = {expr[0]}")
        else:
            out.append(f"\tmeasure {q(name)} =")
            out.append(tmdl_expr(expr, 3))
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        if name in HIDDEN_MEASURES:
            out.append("\t\tisHidden")
        out.append(f"\t\tdisplayFolder: {folder}")
        out.append(f"\t\tlineageTag: {gid('measure', name)}")
        out.append("")
        out.append(f"\t\tannotation KPI_Id = {kid}")
        out.append("")
        out.append(f"\t\tannotation KPI_Status = {status}")
        out.append("")
    out += ["\tcolumn Value", "\t\tdataType: string", "\t\tisHidden", f"\t\tlineageTag: {gid('col', tname, 'Value')}",
            "\t\tsummarizeBy: none", "\t\tsourceColumn: Value", "", "\t\tannotation SummarizationSetBy = Automatic", "",
            f"\tpartition {q(tname)} = m", "\t\tmode: import", "\t\tsource =",
            tmdl_expr(["let", "    Source = #table(type table [Value = text], {})", "in", "    Source"], 4), "",
            "\tannotation PBI_ResultType = Table", ""]
    return "\n".join(out)


def build_calc_group() -> str:
    out = ["/// Time intelligence calculation group. Requires the marked Date table. YoY on GMV is PARTIAL (coverage).",
           "table 'Time Intelligence'", f"\tlineageTag: {gid('table', 'Time Intelligence')}", "",
           "\tcalculationGroup", "\t\tprecedence: 10", ""]
    for i, (name, expr, fse) in enumerate(CALC_ITEMS):
        if len(expr) == 1:
            out.append(f"\t\tcalculationItem {q(name)} = {expr[0]}")
        else:
            out.append(f"\t\tcalculationItem {q(name)} =")
            out.append(tmdl_expr(expr, 4))
        out.append(f"\t\t\tordinal: {i}")
        out.append("\t\t\tformatStringDefinition = " + (fse or "SELECTEDMEASUREFORMATSTRING ()"))
        out.append("")
    out += ["\tcolumn 'Time Calculation'", "\t\tdataType: string", f"\t\tlineageTag: {gid('col', 'TI', 'name')}",
            "\t\tsummarizeBy: none", "\t\tsourceColumn: Name", "\t\tsortByColumn: Ordinal", "",
            "\t\tannotation SummarizationSetBy = Automatic", "",
            "\tcolumn Ordinal", "\t\tdataType: int64", "\t\tisHidden", "\t\tformatString: 0",
            f"\t\tlineageTag: {gid('col', 'TI', 'ordinal')}", "\t\tsummarizeBy: none", "\t\tsourceColumn: Ordinal", "",
            "\t\tannotation SummarizationSetBy = Automatic", "",
            "\tpartition 'Time Intelligence' = calculationGroup", "\t\tmode: import", ""]
    return "\n".join(out)


def build_model() -> None:
    if SM.exists():
        shutil.rmtree(SM)
    d = SM / "definition"
    wjson(SM / "definition.pbism", {"$schema": f"{MS}/item/semanticModel/definitionProperties/1.0.0/schema.json",
                                    "version": "4.2", "settings": {}})
    write(d / "database.tmdl", "database\n\tcompatibilityLevel: 1567\n\n")
    all_tables = [t["name"] for t in TABLES] + ["_Measures", UCI_MEASURES_TABLE, "Time Intelligence"]
    model = ["model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
             "\tdiscourageImplicitMeasures", "\tsourceQueryCulture: en-US", "\tdataAccessOptions",
             "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
             'annotation PBI_QueryOrder = ["PgServer","PgDatabase","PgSchema","PgSchemaUci","PgSchemaUciMarts"]', "",
             "annotation __PBI_TimeIntelligenceEnabled = 0", "",
             "annotation PBI_ProTooling = [\"DevMode\"]", ""]
    model += [f"ref table {q(n)}" for n in all_tables] + [""] + [f"ref role {q(r[0])}" for r in ROLES] + ["", "ref cultureInfo en-US", ""]
    for rname, rdesc, perms in ROLES:
        rl = [f"/// {rdesc}", f"role {q(rname)}", "\tmodelPermission: read", ""]
        for tname, flt in perms:
            rl += [f"\ttablePermission {q(tname)} = {flt}", ""]
        rl += [f"\tannotation PBI_Id = {gid('role', rname).replace('-', '')}", ""]
        write(d / "roles" / f"{rname}.tmdl", "\n".join(rl))
    write(d / "model.tmdl", "\n".join(model))
    params = [("PgServer", "localhost:5432", "PostgreSQL server as host:port (laptop: localhost:5432)."),
              ("PgDatabase", "enterprise360", "PostgreSQL database."),
              ("PgSchema", "core", "Schema holding the dbt core facts/dimensions (dbt +schema: core)."),
              ("PgSchemaUci", "uci_core", "UCI Online Retail II core facts/dimensions (dbt +schema: uci_core)."),
              ("PgSchemaUciMarts", "uci_marts", "UCI Online Retail II marts (cohorts, RFM; dbt +schema: uci_marts).")]
    ex = []
    for n, v, desc in params:
        ex += [f"/// {desc}",
               f'expression {n} = "{v}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]',
               f"\tlineageTag: {gid('expr', n)}", "", "\tannotation PBI_ResultType = Text", ""]
    write(d / "expressions.tmdl", "\n".join(ex))
    rel = []
    for ft, fc, tt, tc, active in RELS:
        rel.append(f"relationship {gid('rel', ft, fc, tt, tc)}")
        if not active:
            rel.append("\tisActive: false")
        rel.append(f"\tfromColumn: {q(ft)}.{q(fc)}")
        rel.append(f"\ttoColumn: {q(tt)}.{q(tc)}")
        rel.append("")
    write(d / "relationships.tmdl", "\n".join(rel))
    write(d / "cultures" / "en-US.tmdl", "\n".join([
        "cultureInfo en-US", "", "\tlinguisticMetadata =", "\t\t\t{", '\t\t\t  "Version": "1.0.0",',
        '\t\t\t  "Language": "en-US"', "\t\t\t}", "\t\tcontentType: json", ""]))
    for t in TABLES:
        write(d / "tables" / f"{t['name']}.tmdl", build_table(t))
    write(d / "tables" / "_Measures.tmdl", build_measures_table())
    write(d / "tables" / f"{UCI_MEASURES_TABLE}.tmdl", build_measures_table(
        UCI_MEASURES_TABLE, UCI_MEASURES,
        "UCI Online Retail II measures (GBP). Separate UK dataset; never combined with Olist (BRL). Names/ids follow kpis.yaml domain uci."))
    write(d / "tables" / "Time Intelligence.tmdl", build_calc_group())


# --------------------------------------------------------------------------------------
# Report (PBIR)
# --------------------------------------------------------------------------------------
def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}


def color(hexv: str):
    return {"solid": {"color": lit(hexv)}}


def fld(kind: str, entity: str, prop: str):
    key = "Measure" if kind == "m" else "Column"
    return {key: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def proj(kind: str, entity: str, prop: str, display: str | None = None):
    p_ = {"field": fld(kind, entity, prop), "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}
    if display:
        p_["displayName"] = display
    return p_


M = "_Measures"
PARTIAL_GROWTH = "Partial: 2016 and late-2018 coverage incomplete"
PARTIAL_RETENTION = "Partial: low repeat base; 2016/late-2018 incomplete"
PARTIAL_HANDOVER = "Partial: carrier handover is recorded per order, so sellers in multi-seller orders share one handover time."
AMBER = "#F59E0B"


def page_name(pid: str) -> str:
    return hid("page", pid)


class Page:
    def __init__(self, pid: str, display: str, width: int = 1280, height: int = 720, ptype: str | None = None,
                 hidden: bool = False, drill: tuple | None = None):
        self.pid, self.display, self.width, self.height = pid, display, width, height
        self.ptype, self.hidden, self.drill = ptype, hidden, drill
        self.name = page_name(pid)
        self.visuals: list[dict] = []
        self.z = 0

    def add(self, vname: str, vtype: str, pos: tuple, roles: dict | None = None, title: str | None = None,
            subtitle: str | None = None, sort: tuple | None = None, objects: dict | None = None,
            tooltip_page: str | None = None, link: dict | None = None, hidden: bool = False, card: bool = True,
            filters: list | None = None) -> str:
        x, y, w, h = pos
        self.z += 1
        v: dict = {"visualType": vtype}
        if roles:
            v["query"] = {"queryState": {r: {"projections": [proj(*p_) for p_ in ps]} for r, ps in roles.items()}}
            if sort:
                kind, ent, prop, direction = sort
                v["query"]["sortDefinition"] = {"sort": [{"field": fld(kind, ent, prop), "direction": direction}],
                                                "isDefaultSort": False}
        if objects:
            v["objects"] = objects
        vco: dict = {}
        if card:
            vco["background"] = [{"properties": {"show": lit(True), "color": color("#111A2E"), "transparency": lit(0)}}]
            vco["border"] = [{"properties": {"show": lit(True), "color": color("#1F2A44"), "radius": lit(8)}}]
            vco["dropShadow"] = [{"properties": {"show": lit(False)}}]
        if title:
            vco["title"] = [{"properties": {"show": lit(True), "text": lit(title), "fontColor": color("#E5E7EB")}}]
        else:
            vco["title"] = [{"properties": {"show": lit(False)}}]
        if subtitle:
            vco["subTitle"] = [{"properties": {"show": lit(True), "text": lit(subtitle), "fontColor": color(AMBER)}}]
        if tooltip_page:
            vco["visualTooltip"] = [{"properties": {"show": lit(True), "type": lit("ReportPage"),
                                                    "section": lit(page_name(tooltip_page))}}]
        if link:
            vco["visualLink"] = [{"properties": {k: lit(val) for k, val in link.items()}}]
        v["visualContainerObjects"] = vco
        v["drillFilterOtherVisuals"] = True
        name = hid(self.pid, vname)
        container = {"$schema": f"{MS}/item/report/definition/visualContainer/{V_VISUAL}/schema.json",
                     "name": name,
                     "position": {"x": x, "y": y, "z": self.z * 100, "height": h, "width": w, "tabOrder": self.z * 100},
                     "visual": v}
        if hidden:
            container["isHidden"] = True
        if filters:
            container["filterConfig"] = {"filters": [{
                "name": hid(self.pid, vname, "filter", ent, prop), "field": fld("c", ent, prop), "type": "Categorical",
                "filter": {"Version": 2, "From": [{"Name": "f", "Entity": ent, "Type": 0}],
                           "Where": [{"Condition": {"In": {
                               "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": prop}}],
                               "Values": [[{"Literal": {"Value": "true" if val else "false"}}]]}}}]}}
                for ent, prop, val in filters]}
        self.visuals.append(container)
        return name


CARD_OBJ = {"labels": [{"properties": {"color": color("#22D3EE"), "fontSize": lit(22)}}],
            "categoryLabels": [{"properties": {"show": lit(False)}}]}
SMALL_CARD_OBJ = {"labels": [{"properties": {"color": color("#22D3EE"), "fontSize": lit(16)}}],
                  "categoryLabels": [{"properties": {"show": lit(False)}}]}
SLICER_OBJ = {"data": [{"properties": {"mode": lit("Between")}}]}
TOOLTIP_CATEGORY, TOOLTIP_STATE = "tooltip-category", "tooltip-state"
NO_TOTALS = {"total": [{"properties": {"totals": lit(False)}}]}
SUB_CATEGORY = "Order-level KPIs = orders containing the category; categories do not sum to the company figure"
SUB_PRODUCT = "Order-level KPIs = orders containing the product; rows do not sum to the company figure"
SUB_SELLER = "Order-level KPIs = orders containing the seller's items; sellers do not sum to the company figure"
SUB_SELLER_STATE = "Orders containing items from sellers in each state"
SUB_THIS_SELLER = "Orders containing this seller's items"
CONTENT_Y = 212


def header(pg: Page, date_slicer: bool = True) -> None:
    pg.add("nav", "pageNavigator", (24, 8, 1232, 36), card=False)
    if date_slicer:
        pg.add("slicer-date", "slicer", (24, 52, 320, 48), {"Values": [("c", "Date", "Date")]}, "Purchase date",
               objects=SLICER_OBJ)


def cards(pg: Page, specs: list[tuple], y: int = 108, h: int = 92) -> None:
    n, gap, x0, w_total = len(specs), 12, 24, 1232
    w = (w_total - gap * (n - 1)) // n
    for i, spec in enumerate(specs):
        meas, title = spec[0], spec[1]
        sub = spec[2] if len(spec) > 2 else None
        pg.add(f"card-{meas}", "card", (x0 + i * (w + gap), y, w, h), {"Values": [("m", M, meas)]}, title,
               subtitle=sub, objects=CARD_OBJ)


def back_button(pg: Page) -> None:
    pg.add("back", "actionButton", (1160, 56, 96, 40), None, None,
           objects={"icon": [{"properties": {"shapeType": lit("back")}}],
                    "text": [{"properties": {"show": lit(True), "text": lit("Back")}}]},
           link={"show": True, "type": "Back"}, card=False)


PAGES: list[Page] = []
BOOKMARKS: list[dict] = []

# ---- Executive Command Center (with Executive / Detail bookmarks)
ex = Page("executive-command-center", "Executive Command Center")
header(ex)
cards(ex, [("GMV", "GMV (BRL)"), ("Orders", "Orders"), ("AOV", "AOV (BRL)"),
           ("Avg Review Score", "Avg Review Score (1-5)"), ("On-Time Delivery %", "On-Time Delivery %")])
exec_view = [
    ex.add("trend", "lineChart", (24, CONTENT_Y, 776, 240),
           {"Category": [("c", "Date", "Year Month")], "Y": [("m", M, "GMV"), ("m", M, "Net GMV")]},
           "Monthly GMV vs Net GMV (BRL)", sort=("c", "Date", "Year Month", "Ascending")),
    ex.add("state", "clusteredBarChart", (812, CONTENT_Y, 444, 496),
           {"Category": [("c", "Geography", "State")], "Y": [("m", M, "GMV")]},
           "GMV by customer state", sort=("m", M, "GMV", "Descending"), tooltip_page=TOOLTIP_STATE),
    ex.add("category", "clusteredBarChart", (24, 464, 380, 244),
           {"Category": [("c", "Product", "Category")], "Y": [("m", M, "GMV")]},
           "Top categories by GMV", sort=("m", M, "GMV", "Descending"), tooltip_page=TOOLTIP_CATEGORY),
    ex.add("growth", "clusteredColumnChart", (416, 464, 384, 244),
           {"Category": [("c", "Date", "Year Month")], "Y": [("m", M, "GMV Growth %")]},
           "GMV Growth % (MoM)", subtitle=PARTIAL_GROWTH, sort=("c", "Date", "Year Month", "Ascending")),
]
detail_view = [
    ex.add("detail-table", "tableEx", (24, CONTENT_Y, 1232, 496),
           {"Values": [("c", "Date", "Year Month"), ("m", M, "GMV"), ("m", M, "Net GMV"), ("m", M, "Orders"),
                       ("m", M, "AOV"), ("m", M, "Cancellation Rate %"), ("m", M, "On-Time Delivery %"),
                       ("m", M, "Avg Delivery Days"), ("m", M, "Avg Review Score"), ("m", M, "GMV Growth %")]},
           "Monthly scorecard (GMV Growth %: partial coverage)", subtitle=PARTIAL_GROWTH,
           sort=("c", "Date", "Year Month", "Ascending"), hidden=True),
]
BM_EXEC, BM_DETAIL = "bm-executive-view", "bm-detail-view"
for bname, label, x in ((BM_EXEC, "Executive view", 760), (BM_DETAIL, "Detail view", 900)):
    ex.add(f"btn-{bname}", "actionButton", (x, 56, 128, 40), None, None,
           objects={"text": [{"properties": {"show": lit(True), "text": lit(label)}}]},
           link={"show": True, "type": "Bookmark", "bookmark": hid("bookmark", bname)}, card=False)
for bname, label, show, hide in ((BM_EXEC, "Executive view", exec_view, detail_view),
                                 (BM_DETAIL, "Detail view", detail_view, exec_view)):
    vtypes = {v["name"]: v["visual"]["visualType"] for v in ex.visuals}
    state = {n: {"singleVisual": {"visualType": vtypes[n]}} for n in show}
    state.update({n: {"singleVisual": {"visualType": vtypes[n], "display": {"mode": "hidden"}}} for n in hide})
    BOOKMARKS.append({
        "$schema": f"{MS}/item/report/definition/bookmark/{V_BOOKMARK}/schema.json",
        "displayName": label, "name": hid("bookmark", bname),
        "options": {"targetVisualNames": show + hide, "applyOnlyToTargetVisuals": True, "suppressData": True},
        "explorationState": {"version": "1.3", "activeSection": ex.name,
                             "sections": {ex.name: {"visualContainers": state}}},
    })
PAGES.append(ex)

# ---- Sales Performance
sp = Page("sales-performance", "Sales Performance")
header(sp)
cards(sp, [("GMV", "GMV (BRL)"), ("Net GMV", "Net GMV (BRL)"), ("Items per Order", "Items per Order"),
           ("Freight Share %", "Freight Share % (customer freight)"), ("Cancellation Rate %", "Cancellation Rate %"),
           ("Repeat Purchase Rate %", "Repeat Purchase Rate % (within selected period)", PARTIAL_RETENTION)])
sp.add("trend", "lineChart", (24, CONTENT_Y, 616, 236), {"Category": [("c", "Date", "Year Month")], "Y": [("m", M, "GMV")]},
       "GMV trend (BRL)", sort=("c", "Date", "Year Month", "Ascending"))
sp.add("category", "clusteredBarChart", (652, CONTENT_Y, 300, 236),
       {"Category": [("c", "Product", "Category")], "Y": [("m", M, "GMV")]}, "GMV by category",
       sort=("m", M, "GMV", "Descending"), tooltip_page=TOOLTIP_CATEGORY)
sp.add("state", "clusteredBarChart", (964, CONTENT_Y, 292, 236),
       {"Category": [("c", "Geography", "State")], "Y": [("m", M, "GMV")]}, "GMV by customer state",
       sort=("m", M, "GMV", "Descending"), tooltip_page=TOOLTIP_STATE)
sp.add("paymix", "donutChart", (24, 460, 400, 248),
       {"Category": [("c", "Payment", "Payment Type")], "Y": [("m", M, "Payment Value")]},
       "Payment mix by type (payment value, not sales)")
sp.add("sellers", "tableEx", (436, 460, 820, 248),
       {"Values": [("c", "Seller", "Seller ID"), ("c", "Seller", "Seller State"), ("m", M, "GMV"), ("m", M, "Orders"),
                   ("m", M, "AOV"), ("m", M, "On-Time Delivery %"),
                   ("m", M, "Avg Review Score", "Avg Review Score of orders containing seller")]},
       "Top sellers by GMV (right-click a seller > Drill through > Seller Detail)", subtitle=SUB_SELLER,
       sort=("m", M, "GMV", "Descending"), objects=NO_TOTALS)
PAGES.append(sp)

# ---- Customer Intelligence
ci = Page("customer-intelligence", "Customer Intelligence")
header(ci)
cards(ci, [("Active Customers", "Active Customers"), ("New Customers", "New Customers"),
           ("Repeat Purchase Rate %", "Repeat Purchase Rate % (within selected period)", PARTIAL_RETENTION),
           ("Customer Retention %", "Customer Retention % (prior month)", PARTIAL_RETENTION),
           ("Retention Cohort Size", "Retention Cohort Size (prior-month active)", PARTIAL_RETENTION)])
ci.add("trend", "lineChart", (24, CONTENT_Y, 616, 236),
       {"Category": [("c", "Date", "Year Month")], "Y": [("m", M, "Active Customers"), ("m", M, "New Customers")]},
       "Active vs new customers by month (new = first-order cohort size)", sort=("c", "Date", "Year Month", "Ascending"))
ci.add("region", "clusteredBarChart", (652, CONTENT_Y, 300, 236),
       {"Category": [("c", "Geography", "Region")], "Y": [("m", M, "Active Customers")]}, "Active customers by region",
       sort=("m", M, "Active Customers", "Descending"))
ci.add("state", "clusteredBarChart", (964, CONTENT_Y, 292, 496),
       {"Category": [("c", "Geography", "State")], "Y": [("m", M, "Active Customers")]}, "Active customers by state",
       sort=("m", M, "Active Customers", "Descending"), tooltip_page=TOOLTIP_STATE)
ci.add("retention", "tableEx", (24, 460, 928, 248),
       {"Values": [("c", "Date", "Year Month"), ("m", M, "Active Customers"), ("m", M, "New Customers"),
                   ("m", M, "Repeat Purchase Rate %"), ("m", M, "Customer Retention %"), ("m", M, "Retention Cohort Size")]},
       "Monthly retention with cohort size (repeat rate within each month)", subtitle=PARTIAL_RETENTION,
       sort=("c", "Date", "Year Month", "Ascending"))
PAGES.append(ci)

# ---- Product Performance
pp = Page("product-performance", "Product Performance")
header(pp)
cards(pp, [("GMV", "GMV (BRL)"), ("Items Sold", "Items Sold"), ("AOV", "AOV (BRL)"),
           ("Items per Order", "Items per Order"), ("Freight Share %", "Freight Share %")])
pp.add("category", "clusteredBarChart", (24, CONTENT_Y, 400, 496),
       {"Category": [("c", "Product", "Category")], "Y": [("m", M, "GMV")]}, "GMV by category",
       sort=("m", M, "GMV", "Descending"), tooltip_page=TOOLTIP_CATEGORY)
pp.add("category-table", "tableEx", (436, CONTENT_Y, 820, 244),
       {"Values": [("c", "Product", "Category"), ("m", M, "GMV"), ("m", M, "Items Sold"), ("m", M, "AOV"),
                   ("m", M, "Items per Order"),
                   ("m", M, "Avg Review Score", "Avg Review Score of orders containing category"),
                   ("m", M, "Freight Share %")]},
       "Category scorecard", subtitle=SUB_CATEGORY, sort=("m", M, "GMV", "Descending"), objects=NO_TOTALS)
pp.add("products", "tableEx", (436, 468, 820, 240),
       {"Values": [("c", "Product", "Product ID"), ("c", "Product", "Category"), ("m", M, "GMV"), ("m", M, "Items Sold"),
                   ("m", M, "Avg Review Score", "Avg Review Score of orders containing product"),
                   ("m", M, "Freight Share %")]},
       "Top products by GMV", subtitle=SUB_PRODUCT, sort=("m", M, "GMV", "Descending"), objects=NO_TOTALS)
PAGES.append(pp)

# ---- Operations / Delivery
op = Page("operations-delivery", "Operations & Delivery")
header(op)
cards(op, [("On-Time Delivery %", "On-Time Delivery %"), ("Avg Delivery Days", "Avg Delivery Days"),
           ("Late Orders", "Late Orders"), ("Cancellation Rate %", "Cancellation Rate %"),
           ("Avg Approval Hours", "Avg Approval Hours"),
           ("Seller Handover On-Time %", "Seller handover on-time % (vs Olist shipping deadline)", PARTIAL_HANDOVER)])
op.add("otd-trend", "lineChart", (24, CONTENT_Y, 616, 236),
       {"Category": [("c", "Date", "Year Month")], "Y": [("m", M, "On-Time Delivery % (by Delivery Date)")]},
       "On-time delivery % by delivery month (estimate is Olist's, not a contractual SLA)",
       sort=("c", "Date", "Year Month", "Ascending"))
op.add("otd-state", "clusteredBarChart", (652, CONTENT_Y, 300, 236),
       {"Category": [("c", "Geography", "State")], "Y": [("m", M, "On-Time Delivery %")]},
       "On-time % by customer state", sort=("m", M, "On-Time Delivery %", "Ascending"), tooltip_page=TOOLTIP_STATE)
op.add("otd-seller-state", "clusteredBarChart", (964, CONTENT_Y, 292, 236),
       {"Category": [("c", "Seller", "Seller State")], "Y": [("m", M, "On-Time Delivery %"), ("m", M, "Seller Handover On-Time %")]},
       "On-time delivery % and seller handover on-time % (vs Olist shipping deadline) by seller state",
       subtitle=SUB_SELLER_STATE + ". " + PARTIAL_HANDOVER, sort=("m", M, "On-Time Delivery %", "Ascending"))
op.add("status-funnel", "funnel", (24, 460, 400, 248),
       {"Category": [("c", "Order Status", "Order Status")], "Y": [("m", M, "Orders")]}, "Orders by status",
       sort=("m", M, "Orders", "Descending"))
op.add("late-orders", "tableEx", (436, 460, 820, 248),
       {"Values": [("c", "Order", "Order ID"), ("c", "Order", "Purchased At"), ("c", "Delivery", "Estimated Delivery At"),
                   ("c", "Delivery", "Delivered At"), ("m", M, "Late Orders"), ("m", M, "Avg Delivery Days")]},
       "Late orders (right-click > Drill through > Order Detail)", sort=("m", M, "Avg Delivery Days", "Descending"))
PAGES.append(op)

# ---- Data Quality
dq = Page("data-quality", "Data Quality")
header(dq, date_slicer=False)
dq.add("slicer-run", "slicer", (24, 52, 320, 48), {"Values": [("c", "DQ Run Summary" if USE_DQ_RUN_SUMMARY else "DQ Results", "Run At")]},
       "dbt run (default: latest)", objects={"data": [{"properties": {"mode": lit("Dropdown")}}]})
cards(dq, [("DQ Score %", "DQ Score % (latest run)"), ("Blocking Failures", "Blocking failures"),
           ("Checks Failed", "Checks failed"), ("Checks Warned", "Checks warned"), ("Failing Rows", "Failing rows")])
dq.add("checks", "tableEx", (24, CONTENT_Y, 800, 300),
       {"Values": [("c", "DQ Results", "Check"), ("c", "DQ Results", "Layer"), ("c", "DQ Results", "Model"),
                   ("c", "DQ Results", "KPI ID"), ("c", "DQ Results", "Severity"), ("c", "DQ Results", "Status"),
                   ("m", M, "Failing Rows"), ("m", M, "Reconciliation Variance")]},
       "Checks (latest run unless a run is selected)", sort=("m", M, "Failing Rows", "Descending"),
       objects={"values": [{"properties": {"backColor": {"solid": {"color": {"expr": fld("m", M, "DQ Status Colour")}}}},
                            "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                                         "metadata": "DQ Results.Status"}}]})
dq.add("recon", "clusteredBarChart", (836, CONTENT_Y, 420, 300),
       {"Category": [("c", "DQ Results", "KPI ID")], "Y": [("m", M, "Reconciliation Variance")]},
       "Reconciliation variance by KPI (mart - source)", sort=("m", M, "Reconciliation Variance", "Descending"))
dq.add("score-trend", "lineChart", (24, 524, 800, 184),
       {"Category": [("c", "DQ Run Summary" if USE_DQ_RUN_SUMMARY else "DQ Results", "Run At")], "Y": [("m", M, "DQ Score %")]},
       "DQ Score % by run (strict: warn earns 0)",
       sort=("c", "DQ Run Summary" if USE_DQ_RUN_SUMMARY else "DQ Results", "Run At", "Ascending"))
dq.add("payment-exceptions", "multiRowCard", (836, 524, 204, 184),
       {"Values": [("m", M, "Payment Mismatch Orders"), ("m", M, "Payment Without Items Orders"), ("m", M, "Overpaid Orders"),
                   ("m", M, "Underpaid Orders"), ("m", M, "Items Without Payment Orders")]},
       "Payment vs items+freight exceptions (orders)",
       subtitle="Payment-without-items orders don't appear under product or seller filters, so the four breakdowns won't sum to the mismatch total when filtered")
dq.add("warehouse-checks", "multiRowCard", (1052, 524, 204, 184),
       {"Values": [("m", M, "Delivered Missing Timestamp"),
                   ("m", M, "Delivered Before Purchase"), ("m", M, "Handover Missing Timestamp"), ("m", M, "OTD Eligible Orders"), ("m", M, "Orders"),
                   ("m", M, "Items Sold"), ("m", M, "Payment Records")]},
       "Warehouse checks from fct tables (purchase-date slicers do not apply here)")
PAGES.append(dq)

# ---- Drill-through: Order Detail
od = Page("order-detail", "Order Detail", ptype="Drillthrough", hidden=True, drill=("Order", "Order ID"))
od.add("nav", "pageNavigator", (24, 8, 1232, 36), card=False)
back_button(od)
od.add("order", "tableEx", (24, 108, 1232, 120),
       {"Values": [("c", "Order", "Order ID"), ("c", "Order Status", "Order Status"), ("c", "Order", "Purchased At"),
                   ("c", "Order", "Approved At"), ("c", "Delivery", "Estimated Delivery At"), ("c", "Delivery", "Delivered At"),
                   ("c", "Order", "Review Score")]},
       "Order status, delivery timestamps and latest review")
od.add("lines", "tableEx", (24, 240, 808, 468),
       {"Values": [("c", "Product", "Product ID"), ("c", "Product", "Category"), ("c", "Seller", "Seller ID"),
                   ("m", M, "Items Sold"), ("m", M, "GMV"), ("m", M, "Freight Value")]},
       "Order lines (GMV = item price, freight separate)")
od.add("payments", "tableEx", (844, 240, 412, 468),
       {"Values": [("c", "Payment", "Payment Type"), ("c", "Payment", "Payment Installments"), ("m", M, "Payment Value")]},
       "Payments (transaction value, not sales)")
PAGES.append(od)

# ---- Drill-through: Seller Detail
sd = Page("seller-detail", "Seller Detail", ptype="Drillthrough", hidden=True, drill=("Seller", "Seller ID"))
sd.add("nav", "pageNavigator", (24, 8, 1232, 36), card=False)
sd.add("seller", "multiRowCard", (24, 52, 600, 48), {"Values": [("c", "Seller", "Seller ID"), ("c", "Seller", "Seller State")]},
       None)
back_button(sd)
cards(sd, [("GMV", "GMV (BRL)"), ("Orders", "Orders", SUB_THIS_SELLER), ("AOV", "AOV (BRL)", SUB_THIS_SELLER),
           ("On-Time Delivery %", "On-Time Delivery %", SUB_THIS_SELLER),
           ("Avg Review Score", "Avg Review Score of orders containing seller")])
sd.add("trend", "lineChart", (24, CONTENT_Y, 616, 236), {"Category": [("c", "Date", "Year Month")], "Y": [("m", M, "GMV")]},
       "Seller GMV trend", sort=("c", "Date", "Year Month", "Ascending"))
sd.add("categories", "clusteredBarChart", (652, CONTENT_Y, 604, 236),
       {"Category": [("c", "Product", "Category")], "Y": [("m", M, "GMV")]}, "Top categories for this seller",
       sort=("m", M, "GMV", "Descending"))
sd.add("orders", "tableEx", (24, 460, 1232, 248),
       {"Values": [("c", "Order", "Order ID"), ("c", "Order", "Purchased At"), ("m", M, "Items Sold"), ("m", M, "GMV"),
                   ("m", M, "Freight Value")]},
       "Seller's orders (right-click > Drill through > Order Detail)", subtitle="GMV and freight = this seller's lines only",
       sort=("c", "Order", "Purchased At", "Descending"), objects=NO_TOTALS)
PAGES.append(sd)

# ---- UCI Online Retail II (GBP) pages -- UCI fields only, never mixed with Olist fields
MU = UCI_MEASURES_TABLE
UCI_GROUP = "UCI Online Retail II (GBP)"
SUB_UCI = "UCI Online Retail II (GBP): separate UK dataset, not comparable with Olist (BRL)"
TREND_NOTE = "Trend excludes 2011-12 (partial month, data ends 2011-12-09)"
REPORTING_ONLY = [("UCI Date", "is_reporting_month", True)]
SUB_UCI_PRODUCT = "Invoice-level KPIs are not shown by product; product rows are line values and do sum"
PARTIAL_UCI_RETENTION = ("Partial: 2009-12 cohort mixes pre-existing customers (dataset start); 2011-12 active month is partial and blank; "
                         "22.8% of lines have no Customer ID and are excluded")
PARTIAL_UCI_RFM = "Partial: descriptive NTILE(5) scores at snapshot 2011-12-10, not a prediction; segment labels to be set by owner"
NEW_CUST_NOTE = "Identified customers only; 2009-12 overstated (dataset start, no prior history)"


def uci_header(pg: Page) -> None:
    pg.add("nav", "pageNavigator", (24, 8, 1232, 36), card=False)
    pg.add("slicer-date", "slicer", (24, 52, 420, 48), {"Values": [("c", "UCI Date", "Date")]}, "Invoice date (UCI)",
           subtitle=SUB_UCI, objects=SLICER_OBJ)
    pg.add("slicer-country", "slicer", (456, 52, 300, 48), {"Values": [("c", "UCI Country", "Country")]}, "Invoice country (UCI)",
           objects={"data": [{"properties": {"mode": lit("Dropdown")}}]})


def uci_cards(pg: Page, specs: list[tuple], y: int = 108, h: int = 92) -> None:
    n, gap, x0, w_total = len(specs), 12, 24, 1232
    w = (w_total - gap * (n - 1)) // n
    for i, spec in enumerate(specs):
        meas, title = spec[0], spec[1]
        sub = spec[2] if len(spec) > 2 else None
        pg.add(f"card-{meas}", "card", (x0 + i * (w + gap), y, w, h), {"Values": [("m", MU, meas)]}, title,
               subtitle=sub, objects=CARD_OBJ)


uo = Page("uci-retail-overview", "UCI Retail Overview")
uci_header(uo)
uci_cards(uo, [("UCI Net Sales (proxy)", "Net Sales (proxy) (GBP)"),
               ("UCI Gross Product Sales", "Invoiced Value (gross product sales, GBP)"),
               ("UCI Sales Invoices", "Sales invoices"), ("UCI AOV", "AOV (GBP)"),
               ("UCI Active Customers", "Active customers", "Identified customers only"),
               ("UCI Units per Invoice", "Units per invoice")])
uo.add("trend", "lineChart", (24, CONTENT_Y, 760, 240),
       {"Category": [("c", "UCI Date", "Year Month")], "Y": [("m", MU, "UCI Net Sales (proxy)"), ("m", MU, "UCI Gross Product Sales", "Invoiced Value (gross product sales)")]},
       "Net Sales (proxy) and Invoiced Value by month (GBP)", subtitle=TREND_NOTE,
       sort=("c", "UCI Date", "Year Month", "Ascending"), filters=REPORTING_ONLY)
uo.add("country", "clusteredBarChart", (796, CONTENT_Y, 460, 240),
       {"Category": [("c", "UCI Country", "Country")], "Y": [("m", MU, "UCI Net Sales (proxy)")]},
       "Net Sales (proxy) by invoice country (GBP)", sort=("m", MU, "UCI Net Sales (proxy)", "Descending"))
uo.add("country-nonuk", "clusteredBarChart", (24, 464, 400, 244),
       {"Category": [("c", "UCI Country", "Country")], "Y": [("m", MU, "UCI Country Contribution %")]},
       "Country contribution % - non-UK countries", subtitle="United Kingdom (about 85.5%) excluded from this view",
       sort=("m", MU, "UCI Country Contribution %", "Descending"), filters=[("UCI Country", "is_domestic", False)])
uo.add("top-products", "tableEx", (436, 464, 820, 244),
       {"Values": [("c", "UCI Product", "Stock Code"), ("c", "UCI Product", "Description"),
                   ("m", MU, "UCI Gross Product Sales", "Invoiced Value (gross product sales)"),
                   ("m", MU, "UCI Product Cancellations"), ("m", MU, "UCI Product Contribution %")]},
       "Top products by Invoiced Value (GBP)", subtitle=SUB_UCI_PRODUCT,
       sort=("m", MU, "UCI Gross Product Sales", "Descending"), objects=NO_TOTALS)
PAGES.append(uo)

uc = Page("uci-customers-retention", "UCI Customers & Retention")
uci_header(uc)
uci_cards(uc, [("UCI Active Customers", "Active customers", "Identified customers only (22.8% of lines have no Customer ID)"),
               ("UCI New Customers", "New customers", NEW_CUST_NOTE),
               ("UCI Repeat Rate %", "Repeat rate % (full coverage)", "Full window 2009-12-01..2011-12-09; not period-sensitive"),
               ("UCI Customers by RFM Segment", "Customers with RFM scores", PARTIAL_UCI_RFM)])
uc.add("cust-trend", "lineChart", (24, CONTENT_Y, 616, 236),
       {"Category": [("c", "UCI Date", "Year Month")], "Y": [("m", MU, "UCI Active Customers"), ("m", MU, "UCI New Customers")]},
       "Active and new customers by month", subtitle=TREND_NOTE + ". " + NEW_CUST_NOTE,
       sort=("c", "UCI Date", "Year Month", "Ascending"), filters=REPORTING_ONLY)
uc.add("rfm", "pivotTable", (652, CONTENT_Y, 604, 236),
       {"Rows": [("c", "UCI RFM", "R Score")], "Columns": [("c", "UCI RFM", "F Score")],
        "Values": [("m", MU, "UCI Customers by RFM Segment")]},
       "Customers by RFM score (R rows x F columns)", subtitle=PARTIAL_UCI_RFM)
uc.add("retention", "pivotTable", (24, 460, 1232, 248),
       {"Rows": [("c", "UCI Cohort", "Cohort Month")], "Columns": [("c", "UCI Cohort", "Months Since First Purchase")],
        "Values": [("m", MU, "UCI Cohort Retention %")]},
       "Cohort retention % (first-purchase month x months since first purchase)", subtitle=PARTIAL_UCI_RETENTION,
       objects=NO_TOTALS)
PAGES.append(uc)

ur = Page("uci-cancellations", "UCI Cancellations & Discounts")
uci_header(ur)
uci_cards(ur, [("UCI Product Cancellations", "Product cancellations (GBP)", "Cancellations (C invoices), not confirmed returns"),
               ("UCI Cancellation Rate % (Value)", "Cancellation rate % (value)"),
               ("UCI Cancellation Rate % (Lines)", "Cancellation rate % (lines)"),
               ("UCI Cancellation Rate % (Invoices)", "Cancellation rate % (invoices)"),
               ("UCI Discounts", "Discounts (GBP)"), ("UCI Postage", "Postage (GBP)"), ("UCI Fees", "Fees (GBP)")])
ur.add("cancel-trend", "lineChart", (24, CONTENT_Y, 760, 240),
       {"Category": [("c", "UCI Date", "Year Month")], "Y": [("m", MU, "UCI Cancellation Rate % (Value)"), ("m", MU, "UCI Cancellation Rate % (Invoices)")]},
       "Cancellation rate % by month", subtitle=TREND_NOTE + ". Period rate: cancellations are not linked to their original invoice",
       sort=("c", "UCI Date", "Year Month", "Ascending"), filters=REPORTING_ONLY)
ur.add("cancel-country", "clusteredBarChart", (796, CONTENT_Y, 460, 240),
       {"Category": [("c", "UCI Country", "Country")], "Y": [("m", MU, "UCI Cancellation Rate % (Value)")]},
       "Cancellation rate % (value) by invoice country", sort=("m", MU, "UCI Cancellation Rate % (Value)", "Descending"))
ur.add("cancel-products", "tableEx", (24, 464, 1232, 244),
       {"Values": [("c", "UCI Product", "Stock Code"), ("c", "UCI Product", "Description"),
                   ("m", MU, "UCI Product Cancellations"), ("m", MU, "UCI Gross Product Sales", "Invoiced Value (gross product sales)"),
                   ("m", MU, "UCI Cancellation Rate % (Value)"), ("m", MU, "UCI Cancellation Rate % (Lines)")]},
       "Most cancelled products (GBP)", subtitle="Product-line values; rates can exceed 100% at product grain (no C-to-original link)",
       sort=("m", MU, "UCI Product Cancellations", "Ascending"), objects=NO_TOTALS)
PAGES.append(ur)

# ---- Tooltip pages
for tid, display, field in ((TOOLTIP_CATEGORY, "Tooltip - Category", ("Product", "Category")),
                            (TOOLTIP_STATE, "Tooltip - State", ("Geography", "State"))):
    tp = Page(tid, display, width=320, height=240, ptype="Tooltip", hidden=True)
    tp.add("title", "multiRowCard", (8, 8, 304, 40), {"Values": [("c", field[0], field[1])]}, None, card=False)
    specs = ([("GMV", "GMV (BRL)"), ("AOV", "AOV of orders containing category"),
              ("Avg Review Score", "Avg Review Score of orders containing category"),
              ("On-Time Delivery %", "On-time % of orders containing category")] if tid == TOOLTIP_CATEGORY else
             [("GMV", "GMV (BRL)"), ("AOV", "AOV (BRL)"), ("Avg Review Score", "Avg Review Score"),
              ("On-Time Delivery %", "On-time %")])
    for i, (meas, title) in enumerate(specs):
        tp.add(f"card-{meas}", "card", (8 + (i % 2) * 156, 56 + (i // 2) * 90, 148, 82),
               {"Values": [("m", M, meas)]}, title, objects=SMALL_CARD_OBJ)
    PAGES.append(tp)

THEME_NAME = "Enterprise360Dark"
THEME = {
    "$schema": "https://raw.githubusercontent.com/microsoft/powerbi-desktop-samples/main/Report%20Theme%20JSON%20Schema/reportThemeSchema-2.159.json",
    "name": THEME_NAME,
    "dataColors": ["#22D3EE", "#3B82F6", "#818CF8", "#2DD4BF", "#60A5FA", "#A78BFA", "#94A3B8", "#F59E0B"],
    "foreground": "#E5E7EB", "foregroundNeutralSecondary": "#94A3B8", "foregroundNeutralTertiary": "#64748B",
    "background": "#0B1220", "secondaryBackground": "#111A2E", "backgroundLight": "#1F2A44",
    "backgroundNeutral": "#1F2A44", "tableAccent": "#22D3EE", "accent": "#22D3EE",
    "good": "#10B981", "neutral": "#F59E0B", "bad": "#EF4444",
    "maximum": "#22D3EE", "center": "#3B82F6", "minimum": "#1E3A8A", "null": "#64748B",
    "hyperlink": "#22D3EE", "visitedHyperlink": "#60A5FA",
    "textClasses": {
        "callout": {"fontSize": 22, "fontFace": "Segoe UI Semibold", "color": "#22D3EE"},
        "title": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#E5E7EB"},
        "header": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#E5E7EB"},
        "label": {"fontSize": 10, "fontFace": "Segoe UI", "color": "#94A3B8"},
    },
    "visualStyles": {
        "page": {"*": {"background": [{"color": {"solid": {"color": "#0B1220"}}, "transparency": 0}],
                       "outspace": [{"color": {"solid": {"color": "#0B1220"}}}]}},
        "*": {"*": {"title": [{"fontColor": {"solid": {"color": "#E5E7EB"}}, "fontSize": 11}],
                    "visualHeader": [{"background": {"solid": {"color": "#111A2E"}},
                                      "foreground": {"solid": {"color": "#94A3B8"}}}]}},
        "actionButton": {"*": {"fill": [{"show": True, "fillColor": {"solid": {"color": "#1F2A44"}}}],
                               "text": [{"fontColor": {"solid": {"color": "#E5E7EB"}}}]}},
        "pageNavigator": {"*": {"fill": [{"show": True, "fillColor": {"solid": {"color": "#111A2E"}}}],
                                "text": [{"fontColor": {"solid": {"color": "#94A3B8"}}}]}},
    },
}


def build_report() -> None:
    if RP.exists():
        shutil.rmtree(RP)
    wjson(RP / "definition.pbir", {"$schema": f"{MS}/item/report/definitionProperties/2.0.0/schema.json",
                                   "version": "4.0",
                                   "datasetReference": {"byPath": {"path": "../Enterprise360.SemanticModel"}}})
    d = RP / "definition"
    wjson(d / "version.json", {"$schema": f"{MS}/item/report/definition/versionMetadata/1.0.0/schema.json",
                               "version": "2.0.0"})
    theme_file = f"{THEME_NAME}.json"
    wjson(d / "report.json", {
        "$schema": f"{MS}/item/report/definition/report/{V_REPORT}/schema.json",
        "themeCollection": {"customTheme": {"name": theme_file,
                                            "reportVersionAtImport": {"visual": V_VISUAL, "report": V_REPORT, "page": V_PAGE},
                                            "type": "RegisteredResources"}},
        "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                              "items": [{"name": theme_file, "path": theme_file, "type": "CustomTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True,
                     "exportDataMode": "AllowSummarized"},
    })
    wjson(RP / "StaticResources" / "RegisteredResources" / theme_file, THEME)
    wjson(d / "pages" / "pages.json", {"$schema": f"{MS}/item/report/definition/pagesMetadata/1.0.0/schema.json",
                                       "pageOrder": [p.name for p in PAGES], "activePageName": PAGES[0].name})
    for pg in PAGES:
        page: dict = {"$schema": f"{MS}/item/report/definition/page/{V_PAGE}/schema.json",
                      "name": pg.name, "displayName": pg.display,
                      "displayOption": "ActualSize" if pg.ptype == "Tooltip" else "FitToPage",
                      "height": pg.height, "width": pg.width}
        if pg.drill:
            ent, prop = pg.drill
            fname = hid("drillfilter", pg.pid)
            page["filterConfig"] = {"filters": [{"name": fname, "field": fld("c", ent, prop), "type": "Categorical",
                                                 "howCreated": "Drillthrough"}]}
            page["pageBinding"] = {"name": hid("binding", pg.pid), "type": "Drillthrough",
                                   "parameters": [{"name": hid("param", pg.pid), "boundFilter": fname,
                                                   "fieldExpr": fld("c", ent, prop)}]}
        elif pg.ptype == "Tooltip":
            page["pageBinding"] = {"name": hid("binding", pg.pid), "type": "Tooltip"}
        page["objects"] = {"background": [{"properties": {"color": color("#0B1220"), "transparency": lit(0)}}],
                           "outspace": [{"properties": {"color": color("#0B1220")}}]}
        if pg.ptype:
            page["type"] = pg.ptype
        if pg.hidden:
            page["visibility"] = "HiddenInViewMode"
        wjson(d / "pages" / pg.name / "page.json", page)
        for v in pg.visuals:
            wjson(d / "pages" / pg.name / "visuals" / v["name"] / "visual.json", v)
    bdir = d / "bookmarks"
    wjson(bdir / "bookmarks.json", {"$schema": f"{MS}/item/report/definition/bookmarksMetadata/1.0.0/schema.json",
                                    "items": [{"name": b["name"]} for b in BOOKMARKS]})
    for b in BOOKMARKS:
        wjson(bdir / f"{b['name']}.bookmark.json", b)
    wjson(ROOT / "Enterprise360.pbip", {"$schema": f"{MS}/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
                                        "artifacts": [{"report": {"path": "Enterprise360.Report"}}],
                                        "settings": {"enableAutoRecovery": True}})


if __name__ == "__main__":
    build_model()
    build_report()
    print("generated", SM, RP)
