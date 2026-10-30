from ingestion.sources.contracts import ReplaceScope, SourceContract
from ingestion.sources.olist import OLIST_CONTRACTS, get_contract
from ingestion.sources.uci import UCI_CONTRACTS, UCI_ONLINE_RETAIL_II

__all__ = [
    "OLIST_CONTRACTS",
    "UCI_CONTRACTS",
    "UCI_ONLINE_RETAIL_II",
    "ReplaceScope",
    "SourceContract",
    "get_contract",
]
