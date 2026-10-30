"""Allows ``python -m ingestion ...`` (OS-agnostic entry point; no shell scripts required)."""

from ingestion.cli import app

app()
