"""Configuration management using Pydantic Settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="local", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="fleet_warehouse", alias="POSTGRES_DB")
    postgres_user: str = Field(default="fleet_app", alias="POSTGRES_USER")
    postgres_password: str = Field(default="change_me", alias="POSTGRES_PASSWORD")

    source_type: str = Field(default="file", alias="SOURCE_TYPE")
    source_file: str = Field(default="data/sample/vehicles.json", alias="SOURCE_FILE")
    rejected_dir: str = Field(default="data/rejected", alias="REJECTED_DIR")

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL for SQLAlchemy."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def resolved_source_path(self) -> Path:
        """Return the resolved Path object of the source file."""
        return Path(self.source_file)

    @property
    def resolved_rejected_dir(self) -> Path:
        """Return the resolved Path object of the rejection output directory."""
        return Path(self.rejected_dir)


def get_settings() -> Settings:
    """Factory function to instantiate or retrieve settings."""
    return Settings()
