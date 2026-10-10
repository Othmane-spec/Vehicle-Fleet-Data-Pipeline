"""Unit tests for configuration management."""

import os
from unittest.mock import patch

from fleet_pipeline.config import Settings, get_settings


def test_settings_default_values():
    """Verify default configuration parameters."""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert settings.app_env == "local"
        assert settings.log_level == "INFO"
        assert settings.postgres_host == "localhost"
        assert settings.postgres_port == 5432
        assert settings.postgres_db == "fleet_warehouse"
        assert "postgresql+psycopg://" in settings.database_url


def test_settings_environment_override():
    """Verify environment variables take precedence."""
    env_vars = {
        "APP_ENV": "production",
        "LOG_LEVEL": "DEBUG",
        "POSTGRES_HOST": "db.prod.internal",
        "POSTGRES_PORT": "5433",
        "POSTGRES_DB": "prod_fleet",
        "POSTGRES_USER": "prod_user",
        "POSTGRES_PASSWORD": "secret_password",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        settings = get_settings()
        assert settings.app_env == "production"
        assert settings.log_level == "DEBUG"
        assert settings.postgres_host == "db.prod.internal"
        assert settings.postgres_port == 5433
        assert (
            settings.database_url
            == "postgresql+psycopg://prod_user:secret_password@db.prod.internal:5433/prod_fleet"
        )
