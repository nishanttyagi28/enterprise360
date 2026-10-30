"""``python -m orchestration.flow [--source-dir DIR] [--force] [--full-refresh]``"""

from __future__ import annotations

import argparse
from pathlib import Path

from orchestration.flows.olist_pipeline import olist_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Olist ingest -> dbt build flow")
    parser.add_argument("--source-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true", help="reload files even if unchanged")
    parser.add_argument("--full-refresh", action="store_true", help="rebuild incremental models")
    a = parser.parse_args()
    olist_pipeline(source_dir=a.source_dir, force=a.force, full_refresh=a.full_refresh)


if __name__ == "__main__":
    main()
