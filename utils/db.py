from pathlib import Path
from typing import Any, List, Optional, Tuple
import os
import sys
import re
from urllib.parse import quote, urlparse, unquote

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

# First DSN that successfully connected (pooler vs direct)
_working_conn_str: Optional[str] = None


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


def _secret_get(key: str) -> Optional[str]:
    if st is not None and hasattr(st, "secrets"):
        try:
            v = st.secrets[key]
            if v:
                return str(v).strip()
        except Exception:
            pass
    v = os.environ.get(key)
    return v.strip() if v else None


def get_connection_string() -> Optional[str]:
    """Primary configured DSN (for display / single-string APIs)."""
    pool = _secret_get("DB_CONNECTION_STRING_POOLER")
    if pool:
        return pool
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


def _supabase_direct_to_pooler_candidates(direct_url: str) -> List[str]:
    """
    If URL looks like Supabase direct (db.<ref>.supabase.co:5432), build Session pooler URLs.
    See: https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler
    """
    u = direct_url.strip()
    try:
        p = urlparse(u)
    except Exception:
        return []
    host = (p.hostname or "").lower()
    if not host.startswith("db.") or not host.endswith(".supabase.co"):
        return []
    if p.port not in (None, 5432):
        return []
    ref = host[3 : -len(".supabase.co")]
    if not re.match(r"^[a-z0-9]{15,25}$", ref):
        return []
    password = unquote(p.password or "")
    if not password:
        return []
    dbn = (p.path or "/postgres").strip("/") or "postgres"
    if p.query:
        q = f"?{p.query}"
        if "sslmode" not in p.query.lower():
            q += "&sslmode=require"
    else:
        q = "?sslmode=require"

    pool_user = f"postgres.{ref}"
    pwq = quote(password, safe="")
    regions = []
    reg = _secret_get("SUPABASE_POOLER_REGION")
    if reg:
        regions.append(reg.strip())
    for r in (
        "me-central-1",
        "eu-central-1",
        "eu-west-1",
        "us-east-1",
        "us-west-1",
        "ap-south-1",
        "ap-southeast-1",
    ):
        if r not in regions:
            regions.append(r)
    out: List[str] = []
    for region in regions:
        phost = f"aws-0-{region}.pooler.supabase.com"
        out.append(f"postgresql://{quote(pool_user, safe='.@')}:{pwq}@{phost}:6543/{dbn}{q}")
    return out


def _connection_candidates() -> List[str]:
    seen = set()
    out: List[str] = []

    def add(s: Optional[str]) -> None:
        if not s:
            return
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    add(_secret_get("DB_CONNECTION_STRING_POOLER"))
    primary = get_connection_string()
    add(primary)
    if primary:
        for d in _supabase_direct_to_pooler_candidates(primary):
            add(d)
    return out


def _connect_first_available(candidates: List[str]) -> Tuple[Any, str]:
    global _working_conn_str
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is required but not installed")
    last_err: Optional[Exception] = None
    for i, cs in enumerate(candidates):
        # First tries (configured DSNs): longer timeout; auto pooler guesses: shorter
        timeout = 16 if i < 2 else 9
        try:
            conn = psycopg2.connect(cs, connect_timeout=timeout)
            _working_conn_str = cs
            return conn, cs
        except Exception as e:
            last_err = e
            continue
    _working_conn_str = None
    if last_err:
        raise last_err
    raise RuntimeError("No database connection string configured")


def get_connection():
    global _working_conn_str
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is required but not installed. Please install psycopg2-binary")

    if _working_conn_str:
        try:
            return psycopg2.connect(_working_conn_str, connect_timeout=20)
        except Exception:
            _working_conn_str = None

    cands = _connection_candidates()
    if not cands:
        raise RuntimeError(
            'Database connection string not set. Set st.secrets["DB_CONNECTION_STRING"] '
            'or optional DB_CONNECTION_STRING_POOLER (Session pooler, port 6543)'
        )
    conn, _ = _connect_first_available(cands)
    return conn


def check_db_connection():
    """
    Returns (ok: bool, message: str). Message is safe for UI (Arabic hints, no password).
    """
    if psycopg2 is None:
        return False, "مكتبة psycopg2 غير متوفرة."
    cands = _connection_candidates()
    if not cands:
        return False, (
            "لم يُعثر على DB_CONNECTION_STRING. في Streamlit Cloud: App settings → Secrets "
            "وأضف سطر: DB_CONNECTION_STRING = \"postgresql://...\""
        )
    global _working_conn_str
    prev = _working_conn_str
    _working_conn_str = None
    try:
        conn, used = _connect_first_available(cands)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            pool = ":6543" in used or "pooler" in used.lower()
            return True, (
                "قاعدة البيانات (Supabase) متصلة"
                + (" عبر Session pooler." if pool else ".")
            )
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        _working_conn_str = prev
        raw = (str(e) or "").lower()
        hint = ""
        if "timeout" in raw or "timed out" in raw or "could not connect" in raw:
            hint = (
                " غالباً Streamlit Cloud لا يصل للمنفذ 5432 المباشر. من Supabase: "
                "Settings → Database → استخدم **Connection pooling** / **Session mode** "
                "والمنفذ **6543** (مثال: …pooler.supabase.com:6543…)."
            )
        elif "password authentication failed" in raw or "invalid password" in raw:
            hint = " تحقق من كلمة مرور مستخدم postgres في Secrets (وليس مفتاح anon)."
        elif "could not translate host name" in raw or "name or service not known" in raw:
            hint = " تحقق من اسم المضيف (host) في سلسلة الاتصال."
        elif "ssl" in raw or "certificate" in raw:
            hint = " أضف في نهاية الرابط: ?sslmode=require"
        elif "no pg_hba.conf entry" in raw or "no encryption" in raw:
            hint = " استخدم sslmode=require في سلسلة الاتصال."
        first = str(e).strip().split("\n")[0][:180]
        return False, first + hint


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
