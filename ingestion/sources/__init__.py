from ingestion.sources.contracts import ReplaceScope, SourceContract
from ingestion.sources.funnel import FUNNEL_CLOSED_DEALS, FUNNEL_CONTRACTS, FUNNEL_MQL
from ingestion.sources.olist import OLIST_CONTRACTS, get_contract
from ingestion.sources.uci import UCI_CONTRACTS, UCI_ONLINE_RETAIL_II

__all__ = [
    "FUNNEL_CLOSED_DEALS",
    "FUNNEL_CONTRACTS",
    "FUNNEL_MQL",
    "OLIST_CONTRACTS",
    "UCI_CONTRACTS",
    "UCI_ONLINE_RETAIL_II",
    "ReplaceScope",
    "SourceContract",
    "get_contract",
]
