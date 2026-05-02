"""Database connection management — SQLAlchemy 2.0 session.

Provides both the SQLAlchemy session interface (get_db, SessionLocal)
and a legacy-compatible DatabaseManager for incremental migration.
"""
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.core.models import Base

DB_PATH = Path(__file__).parent.parent.parent / "competitor_watch.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """Create all tables (dev convenience; production uses Alembic)."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """FastAPI dependency injection: yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _convert_positional(query: str, params):
    """Convert ? placeholders and tuple/list params to SQLAlchemy named params.

    SQLAlchemy 2.0 requires list[dict] for named params or list[tuple] for
    positional params. Mixed-type tuples (int + str) cause sorting errors.
    This converts ? to :p0, :p1, ... and tuples to dicts automatically.
    """
    if params is None:
        return query, None

    if isinstance(params, dict):
        return query, [params]

    if isinstance(params, (list, tuple)):
        # Already a list of dicts/tuples (batch mode)
        if len(params) > 0 and isinstance(params[0], (dict, tuple, list)):
            return query, params

        # Single tuple/list of values — convert ? to :pN and values to dict
        named_query = query
        for i in range(len(params)):
            named_query = named_query.replace("?", f":p{i}", 1)

        named_params = {f"p{i}": v for i, v in enumerate(params)}
        return named_query, [named_params]

    return query, params


class DatabaseManager:
    """Legacy-compatible wrapper over SQLAlchemy engine.

    Provides the same execute_query/execute_update/execute_insert
    interface that existing services use, but backed by SQLAlchemy.
    """

    def __init__(self, _engine=None):
        self._engine = _engine or engine

    def execute_query(self, query: str, params=None) -> List[Dict]:
        query, params = _convert_positional(query, params)
        with self._engine.connect() as conn:
            if params is not None:
                result = conn.execute(text(query), params)
            else:
                result = conn.execute(text(query))
            return [dict(row._mapping) for row in result]

    def execute_update(self, query: str, params=None) -> int:
        query, params = _convert_positional(query, params)
        with self._engine.connect() as conn:
            if params is not None:
                result = conn.execute(text(query), params)
            else:
                result = conn.execute(text(query))
            conn.commit()
            return result.rowcount

    def execute_insert(self, query: str, params=None) -> int:
        query, params = _convert_positional(query, params)
        with self._engine.connect() as conn:
            if params is not None:
                result = conn.execute(text(query), params)
            else:
                result = conn.execute(text(query))
            conn.commit()
            return result.lastrowid


db_manager = DatabaseManager()