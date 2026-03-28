from pathlib import Path
from typing import Any, List, Optional
import os
import sys

try:
    import streamlit as st
except Exception:
    st = None

try:
    import psycopg2
    import psycopg2.extras
except Exception:
    psycopg2 = None
    psycopg2_extras = None


def _connection_string_from_secrets_file() -> Optional[str]:
    """CLI / scripts: read DB_CONNECTION_STRING from repo .streamlit/secrets.toml."""
    if sys.version_info < (3, 11):
        return None
    try:
        import tomllib
        p = Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"
        if not p.is_file():
            return None
        data = tomllib.loads(p.read_text(encoding="utf-8"))
        c = data.get("DB_CONNECTION_STRING")
        if c:
            return str(c).strip()
        db = data.get("db")
        if isinstance(db, dict) and db.get("connection_string"):
            return str(db["connection_string"]).strip()
    except Exception:
        pass
    return None


def get_connection_string() -> Optional[str]:
    # Streamlit runtime (secrets is a mapping, not always dict)
    if st is not None and hasattr(st, "secrets"):
        try:
            c = st.secrets["DB_CONNECTION_STRING"]
            if c:
                return str(c).strip()
        except Exception:
            pass
        try:
            db = st.secrets["db"]
            if isinstance(db, dict) and db.get("connection_string"):
                return str(db["connection_string"]).strip()
        except Exception:
            pass
    env = os.environ.get("DB_CONNECTION_STRING")
    if env:
        return env.strip()
    return _connection_string_from_secrets_file()


def get_connection():
    conn_str = get_connection_string()
    if not conn_str:
        raise RuntimeError('Database connection string not set. Set st.secrets["DB_CONNECTION_STRING"] or env DB_CONNECTION_STRING')
    if psycopg2 is None:
        raise RuntimeError('psycopg2 is required but not installed. Please install psycopg2-binary')
    return psycopg2.connect(conn_str)


def db_query(query: str, params: Optional[tuple] = None) -> List[dict]:
    """Execute a SELECT query and return list of dict rows."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        try:
            conn.close()
        except Exception:
            pass


def db_execute(query: str, params: Optional[tuple] = None, returning: bool = False) -> Any:
    """Execute INSERT/UPDATE/DELETE. If returning=True, fetch one row from RETURNING clause."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params or ())
            if returning:
                try:
                    row = cur.fetchone()
                except Exception:
                    row = None
            else:
                row = None
        conn.commit()
        return row
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass
