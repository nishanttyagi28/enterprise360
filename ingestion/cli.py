"""CLI: ``python -m ingestion init-db | olist [--source-dir DIR] [--only NAME] [--force]``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ingestion.config import get_settings
from ingestion.log_config import configure_logging
from ingestion.pipeline import apply_ddl, connect, run_olist

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def _main() -> None:
    configure_logging(get_settings().log_level)


@app.command("init-db")
def init_db() -> None:
    """Create schemas, raw tables and the audit table (idempotent)."""
    settings = get_settings()
    with connect(settings) as conn:
        apply_ddl(conn, settings.resolve(settings.ddl_dir))


@app.command("olist")
def olist(
    source_dir: Annotated[Path | None, typer.Option(help="Folder with the 9 Olist CSVs")] = None,
    only: Annotated[list[str] | None, typer.Option(help="Load only these sources")] = None,
    force: Annotated[bool, typer.Option(help="Reload even if file hash unchanged")] = False,
) -> None:
    """Load the Olist CSVs into raw.*; unchanged files are skipped."""
    run_olist(get_settings(), source_dir=source_dir, only=only, force=force)


if __name__ == "__main__":
    app()
