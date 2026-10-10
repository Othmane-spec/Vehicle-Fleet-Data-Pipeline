"""Unit tests for database module helpers."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text

from fleet_pipeline.database import (
    check_connection,
    get_connection,
    get_engine,
    get_session,
    init_db,
)


def test_get_engine_sqlite():
    """Verify get_engine creates an active Engine instance with sqlite."""
    engine = get_engine("sqlite:///:memory:")
    assert engine is not None
    assert check_connection(engine) is True


def test_check_connection_failure():
    """Verify check_connection returns False on broken connection."""
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("Connection refused")
    assert check_connection(mock_engine) is False


def test_get_connection_context_manager(tmp_path: Path):
    """Verify get_connection provides auto-committing connection."""
    db_file = tmp_path / "conn_test.db"
    engine = create_engine(f"sqlite:///{db_file}")

    with get_connection(engine) as conn:
        conn.execute(text("CREATE TABLE test_tab (id INT);"))
        conn.execute(text("INSERT INTO test_tab VALUES (42);"))

    with engine.connect() as conn:
        val = conn.execute(text("SELECT id FROM test_tab;")).scalar()
        assert val == 42


def test_get_session_commit_and_rollback(tmp_path: Path):
    """Verify get_session commits on success and rolls back on exception."""
    db_file = tmp_path / "session_test.db"
    engine = create_engine(f"sqlite:///{db_file}")

    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE items (val INT);"))

    # Test commit
    with get_session(engine) as session:
        session.execute(text("INSERT INTO items VALUES (10);"))

    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM items;")).scalar() == 1

    # Test rollback on exception
    with pytest.raises(ValueError, match="intentional"):
        with get_session(engine) as session:
            session.execute(text("INSERT INTO items VALUES (20);"))
            raise ValueError("intentional")

    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM items;")).scalar() == 1


def test_init_db_file_not_found(tmp_path: Path):
    """Verify init_db raises FileNotFoundError if schema file does not exist."""
    engine = create_engine("sqlite:///:memory:")
    with pytest.raises(FileNotFoundError):
        init_db(engine, schema_file=tmp_path / "non_existent_schema.sql")
