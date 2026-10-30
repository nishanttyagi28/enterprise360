"""Contracts for Kaggle ``olistbr/marketing-funnel-olist`` (CC BY-NC-SA 4.0; headers verified on file).

Two independent full-snapshot files (ReplaceScope.TABLE): ~8,000 marketing-qualified leads and ~842
closed deals. ``closed_deals.mql_id`` references a lead; ``seller_id`` may reference an Olist seller
(match rate measured in dbt, never assumed).
"""

from __future__ import annotations

from ingestion.sources.contracts import SourceContract

FUNNEL_MQL = SourceContract(
    name="olist_marketing_qualified_leads",
    file_name="olist_marketing_qualified_leads_dataset.csv",
    table="olist_marketing_qualified_leads",
    columns=("mql_id", "first_contact_date", "landing_page_id", "origin"),
    natural_key=("mql_id",),
)

FUNNEL_CLOSED_DEALS = SourceContract(
    name="olist_closed_deals",
    file_name="olist_closed_deals_dataset.csv",
    table="olist_closed_deals",
    columns=(
        "mql_id",
        "seller_id",
        "sdr_id",
        "sr_id",
        "won_date",
        "business_segment",
        "lead_type",
        "lead_behaviour_profile",
        "has_company",
        "has_gtin",
        "average_stock",
        "business_type",
        "declared_product_catalog_size",
        "declared_monthly_revenue",
    ),
    natural_key=("mql_id",),
)

FUNNEL_CONTRACTS: tuple[SourceContract, ...] = (FUNNEL_MQL, FUNNEL_CLOSED_DEALS)
