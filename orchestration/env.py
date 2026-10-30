"""Load the repo ``.env`` into the process environment so dbt's ``env_var()`` sees the same
credentials as ingestion (dbt itself never reads .env). Existing env vars win (CI overrides)."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
DBT_PROJECT_DIR = REPO_ROOT / "dbt_enterprise360"


def load_env() -> None:
    load_dotenv(REPO_ROOT / ".env", override=False, encoding="utf-8")
