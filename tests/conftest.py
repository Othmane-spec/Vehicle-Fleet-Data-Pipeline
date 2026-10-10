"""Pytest global configuration and fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to tests fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_json_path(fixtures_dir: Path) -> Path:
    """Return path to fixture sample vehicles json file."""
    return fixtures_dir / "sample_vehicles.json"
