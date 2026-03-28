"""
1) Truncate Newton app tables in Supabase (records, customers, products, users, logs).
2) Re-seed default users (Admin/Staff/Viewer) so login still works.
3) Insert one quotation row (type=q) per PDF in sibling folder ../qutaion (all files, no skip).

Usage (from repo root 1NEWTON):
  set DB_CONNECTION_STRING=...   OR rely on .streamlit/secrets.toml
  python scripts/import_qutaion_folder.py

Optional:
  python scripts/import_qutaion_folder.py --folder "C:\\path\\to\\qutaion"
  python scripts/import_qutaion_folder.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent
DEFAULT_QUTAION_DIR = WORKSPACE_ROOT / "qutaion"

DEFAULT_USERS = [
    (
        "Admin",
        "1234",
        "admin",
        "dashboard,quotation,invoice,receipt,customers,products,reports,archive,settings",
    ),
    (
        "Staff",
        "5678",
        "staff",
        "dashboard,quotation,invoice,receipt,customers,archive",
    ),
    ("Viewer", "9999", "viewer", "dashboard,reports"),
]

APP_TABLES = ("logs", "records", "customers", "products", "users")


def _load_conn_string() -> str:
    s = os.environ.get("DB_CONNECTION_STRING") or os.environ.get("SUPABASE_DB_URL")
    if s:
        return s.strip()
    p = REPO_ROOT / ".streamlit" / "secrets.toml"
    if p.is_file() and sys.version_info >= (3, 11):
        import tomllib

        data = tomllib.loads(p.read_text(encoding="utf-8"))
        c = data.get("DB_CONNECTION_STRING")
        if c:
            return str(c).strip()
        db = data.get("db")
        if isinstance(db, dict) and db.get("connection_string"):
            return str(db["connection_string"]).strip()
    raise SystemExit(
        "Set DB_CONNECTION_STRING or add it to .streamlit/secrets.toml"
    )


def _existing_public_tables(cur) -> set[str]:
    cur.execute(
        """
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public' AND tablename = ANY(%s)
        """,
        (list(APP_TABLES),),
    )
    return {r[0] for r in cur.fetchall()}


def _truncate_app_tables(conn) -> None:
    with conn.cursor() as cur:
        exist = _existing_public_tables(cur)
        to_truncate = [t for t in APP_TABLES if t in exist]
        if not to_truncate:
            print("No app tables found to truncate:", APP_TABLES)
            return
        # FK-safe order: children first if any FKs exist
        order = [t for t in APP_TABLES if t in to_truncate]
        ids = ", ".join(f'"{t}"' for t in order)
        cur.execute(f"TRUNCATE TABLE {ids} RESTART IDENTITY CASCADE")
    conn.commit()
    print("Truncated:", ", ".join(order))


def _seed_users(conn) -> None:
    with conn.cursor() as cur:
        exist = _existing_public_tables(cur)
        if "users" not in exist:
            print("Table users missing; skip seed.")
            return
        for name, pin, role, pages in DEFAULT_USERS:
            cur.execute(
                "INSERT INTO users(name, pin, role, allowed_pages) VALUES (%s,%s,%s,%s)",
                (name, pin, role, pages),
            )
    conn.commit()
    print("Seeded default users: Admin (1234), Staff (5678), Viewer (9999)")


def _parse_quotation_row(path: Path, idx: int) -> dict:
    """Build one records row (type q) from a PDF filename."""
    stem = path.stem
    name = path.name
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    date_str = mtime.strftime("%Y-%m-%d")
    client = ""
    number: str | None = None

    m = re.search(
        r"Quotation_(.+?)_QUO-(\d{4})(\d{2})(\d{2})-(\d+)",
        stem,
        re.I,
    )
    if m:
        client = m.group(1).replace("_", " ").strip()
        y, mo, d, seq = m.group(2), m.group(3), m.group(4), m.group(5)
        date_str = f"{y}-{mo}-{d}"
        number = f"QUO-{y}{mo}{d}-{seq}"
        suffix = stem[m.end() :].strip()
        if suffix:
            number = f"{number}-{re.sub(r'[^A-Za-z0-9]+', '', suffix)[:20]}"

    if not number:
        m = re.search(r"INV-(\d{4})(\d{2})(\d{2})-(\d+)", stem, re.I)
        if m:
            y, mo, d, seq = m.group(1), m.group(2), m.group(3), m.group(4)
            date_str = f"{y}-{mo}-{d}"
            number = f"INV-{y}{mo}{d}-{seq}"
            extra = re.sub(r"^.*INV-\d{8}-\d+\s*", "", stem).strip()
            if extra:
                number = f"{number}-{_slug(extra)}"

    if not number:
        m = re.search(r"_I(20\d{6,})(.*)$", stem, re.I)
        if m:
            inv_core = f"I{m.group(1).upper()}"
            rest = m.group(2).strip()
            number = f"{inv_core}-{_slug(rest)}" if rest else inv_core

    if not number:
        number = f"FILE-{idx:04d}-{_slug(stem)}"

    if re.search(r"Khalid\s+Al\s+Dhahani", stem, re.I):
        client = client or "Khalid Al Dhahani"

    if not client and stem.startswith("Invoice"):
        tail = re.sub(r"^Invoice_?", "", stem, flags=re.I).strip()
        if not re.search(r"^I?20\d{6}", tail, re.I) and not tail.upper().startswith("INV-"):
            if tail and not tail.lower().startswith("newton"):
                client = re.sub(r"\s+", " ", tail)[:120]

    base_id = f"IMP-{datetime.now().strftime('%Y%m%d')}-{idx:04d}"

    return {
        "base_id": base_id,
        "date": date_str,
        "type": "q",
        "number": number[:200],
        "amount": 0.0,
        "client_name": (client or "-")[:200],
        "phone": "",
        "location": "",
        "note": f"imported_pdf:{name}"[:500],
    }


def _slug(s: str) -> str:
    s = re.sub(r"[^\w\-]+", "-", s.strip())
    s = re.sub(r"-+", "-", s).strip("-")
    return (s[:40] or "x").lower()


def _dedupe_numbers(rows: list[dict]) -> None:
    seen: dict[str, int] = {}
    for r in rows:
        n = r["number"]
        if n not in seen:
            seen[n] = 0
        seen[n] += 1
        if seen[n] > 1:
            r["number"] = f"{n}__{seen[n]}"


def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--folder",
        type=Path,
        default=DEFAULT_QUTAION_DIR,
        help="Folder containing PDFs (default: ../qutaion next to 1NEWTON)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions only; no DB writes",
    )
    args = parser.parse_args()

    folder: Path = args.folder.resolve()
    if not folder.is_dir():
        raise SystemExit(f"Folder not found: {folder}")

    pdfs = sorted(folder.glob("*.pdf"), key=lambda p: p.name.lower())
    if not pdfs:
        raise SystemExit(f"No PDF files in {folder}")

    rows = [_parse_quotation_row(p, i + 1) for i, p in enumerate(pdfs)]
    _dedupe_numbers(rows)

    print(f"Found {len(pdfs)} PDF(s) in {folder}")
    for p, r in zip(pdfs, rows):
        print(f"  - {p.name} -> number={r['number']} client={r['client_name']} date={r['date']}")

    if args.dry_run:
        print("Dry run; no database changes.")
        return

    os.environ["DB_CONNECTION_STRING"] = _load_conn_string()
    sys.path.insert(0, str(REPO_ROOT))
    import psycopg2

    conn = psycopg2.connect(os.environ["DB_CONNECTION_STRING"], connect_timeout=30)
    try:
        _truncate_app_tables(conn)
        _seed_users(conn)

        with conn.cursor() as cur:
            exist = _existing_public_tables(cur)
            if "records" not in exist:
                raise SystemExit("Table records does not exist in this database.")

            for r in rows:
                cur.execute(
                    """
                    INSERT INTO records(base_id, date, type, number, amount, client_name, phone, location, note)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        r["base_id"],
                        r["date"],
                        r["type"],
                        r["number"],
                        r["amount"],
                        r["client_name"],
                        r["phone"],
                        r["location"],
                        r["note"],
                    ),
                )
        conn.commit()
        print(f"Inserted {len(rows)} quotation record(s) into records.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
