"""
Run Supabase migration (Newton Smart Home schema) against DB_CONNECTION_STRING.
Reads connection from: env DB_CONNECTION_STRING, or data/supabase_db_url.txt, or .env.
Usage: python scripts/run_supabase_migration.py
"""
from pathlib import Path
import os
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]


def get_connection_string() -> str:
    s = os.environ.get("DB_CONNECTION_STRING") or os.environ.get("SUPABASE_DB_URL")
    if s:
        return s.strip()
    # data/supabase_db_url.txt (one line: connection string)
    p = REPO_ROOT / "data" / "supabase_db_url.txt"
    if p.exists():
        s = p.read_text(encoding="utf-8").strip()
        if s and not s.startswith("#"):
            return s.split("\n")[0].strip()
    # .env
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DB_CONNECTION_STRING="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
            if line.startswith("SUPABASE_DB_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(
        "Set DB_CONNECTION_STRING or SUPABASE_DB_URL in env, or create data/supabase_db_url.txt or .env with one line: DB_CONNECTION_STRING=postgresql://..."
    )


def main():
    import psycopg2

    conn_str = get_connection_string()
    migration_path = REPO_ROOT / "supabase" / "migrations" / "20250207120000_newton_smart_home_full_schema.sql"
    if not migration_path.exists():
        raise SystemExit(f"Migration file not found: {migration_path}")

    sql = migration_path.read_text(encoding="utf-8")
    conn = psycopg2.connect(conn_str)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        conn.rollback()
        print("Migration failed:", e, file=sys.stderr)
        raise SystemExit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
