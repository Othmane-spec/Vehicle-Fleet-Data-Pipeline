"""Database connectivity, session management and schema execution."""

from collections.abc import Generator
from contextlib import contextmanager
import logging
from pathlib import Path
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from fleet_pipeline.config import get_settings

logger = logging.getLogger("fleet_pipeline.database")


def get_engine(db_url: str | None = None) -> Engine:
    """Create a SQLAlchemy Engine with connection pooling.

    Args:
        db_url: Optional database connection string. If omitted, loaded from settings.

    Returns:
        SQLAlchemy Engine instance.
    """
    settings = get_settings()
    url = db_url or settings.database_url

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    return engine


def check_connection(engine: Engine) -> bool:
    """Check if the database engine can successfully connect and execute a ping query.

    Args:
        engine: SQLAlchemy Engine to test.

    Returns:
        True if connection succeeded, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Database connection check failed: %s", exc)
        return False


def init_db(engine: Engine, schema_file: Path | str | None = None) -> None:
    """Execute DDL statements to ensure all tables and indexes exist.

    Args:
        engine: Target SQLAlchemy Engine.
        schema_file: Optional path to schema.sql file. Defaults to sql/schema.sql.
    """
    if schema_file:
        path = Path(schema_file)
        if not path.exists():
            raise FileNotFoundError(f"Specified schema file does not exist: {path}")
    else:
        path = Path("sql/schema.sql")
        if not path.exists():
            alt_path = Path(__file__).resolve().parent.parent.parent / "sql" / "schema.sql"
            if alt_path.exists():
                path = alt_path
            else:
                raise FileNotFoundError(f"Default schema file not found at {path} or {alt_path}")

    sql_script = path.read_text(encoding="utf-8")

    with engine.begin() as conn:
        # SQLite vs PostgreSQL compatibility for tests
        if engine.dialect.name == "sqlite":
            # Strip PostgreSQL-specific TIMESTAMPTZ/BIGSERIAL for SQLite test runs
            compat_script = (
                sql_script.replace("BIGSERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                .replace("TIMESTAMPTZ", "TIMESTAMP")
                .replace("NOW()", "CURRENT_TIMESTAMP")
            )
            # SQLite doesn't support multiple statements in a single execute(text())
            for statement in compat_script.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))
        else:
            conn.execute(text(sql_script))

    logger.info("Database schema initialized successfully from %s", path)


@contextmanager
def get_session(engine: Engine) -> Generator[Session, None, None]:
    """Provide a transactional session scope around a series of operations."""
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_connection(engine: Engine) -> Generator[Connection, None, None]:
    """Provide a transactional connection scope with auto-commit/rollback."""
    with engine.begin() as conn:
        yield conn

