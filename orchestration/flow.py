"""``python -m orchestration.flow [--domain olist|uci|all] [--source-dir DIR] [--uci-source-dir DIR]
[--force] [--full-refresh]``"""

from __future__ import annotations

import argparse
from pathlib import Path

from orchestration.flows.olist_pipeline import olist_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ingest (Olist + UCI) -> dbt build flow")
    parser.add_argument("--domain", choices=["olist", "uci", "all"], default="all")
    parser.add_argument("--source-dir", type=Path, default=None, help="Olist CSV folder override")
    parser.add_argument("--uci-source-dir", type=Path, default=None, help="UCI CSV folder override")
    parser.add_argument("--force", action="store_true", help="reload files even if unchanged")
    parser.add_argument("--full-refresh", action="store_true", help="rebuild incremental models")
    a = parser.parse_args()
    olist_pipeline(
        source_dir=a.source_dir,
        force=a.force,
        full_refresh=a.full_refresh,
        domain=a.domain,
        uci_source_dir=a.uci_source_dir,
    )


if __name__ == "__main__":
    main()
