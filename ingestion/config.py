"""Typed configuration. Values come from environment variables or a local ``.env`` (never code)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Connection vars use the team-wide fixed names POSTGRES_*; pipeline knobs keep E360_*.
        populate_by_name=True,
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    pg_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    pg_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    pg_db: str = Field(default="enterprise360", validation_alias="POSTGRES_DB")
    pg_user: str = Field(default="e360_app", validation_alias="POSTGRES_USER")
    pg_password: SecretStr = Field(default=SecretStr(""), validation_alias="POSTGRES_PASSWORD")
    olist_dir: Path = Field(default=Path("data/raw/olist"), validation_alias=AliasChoices("E360_OLIST_DIR"))
    uci_dir: Path = Field(default=Path("data/raw/uci_online_retail_ii"), validation_alias="E360_UCI_DIR")
    ddl_dir: Path = Field(default=Path("database/ddl"), validation_alias="E360_DDL_DIR")
    log_level: str = Field(default="INFO", validation_alias="E360_LOG_LEVEL")
    # COPY streams the file in chunks; 1 MiB keeps memory flat even for the 60 MB geolocation file.
    copy_chunk_bytes: int = Field(default=1 << 20, validation_alias="E360_COPY_CHUNK_BYTES")
    connect_retries: int = Field(default=5, validation_alias="E360_CONNECT_RETRIES")

    def resolve(self, path: Path) -> Path:
        """Relative paths are relative to the repo root, so CWD does not matter (Windows/Linux)."""
        return path if path.is_absolute() else (REPO_ROOT / path).resolve()

    @property
    def conninfo(self) -> str:
        from psycopg.conninfo import make_conninfo

        return make_conninfo(
            host=self.pg_host,
            port=self.pg_port,
            dbname=self.pg_db,
            user=self.pg_user,
            password=self.pg_password.get_secret_value(),
            application_name="e360-ingestion",
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
