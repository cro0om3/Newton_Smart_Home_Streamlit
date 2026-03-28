"""
Re-read PDFs in ../qutaion and UPDATE existing records imported with note 'imported_pdf:filename'.
Fills client_name, phone, location, amount from PDF text (same logic as import_qutaion_folder).

Usage (from 1NEWTON):
  python scripts/refresh_imported_records_from_pdf.py
  python scripts/refresh_imported_records_from_pdf.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent
DEFAULT_QUTAION_DIR = WORKSPACE_ROOT / "qutaion"

sys.path.insert(0, str(REPO_ROOT))
from utils.pdf_invoice_extract import merge_pdf_into_row  # noqa: E402


def _doc_type_from_filename(fname: str) -> str:
    sl = Path(fname).stem.lower()
    if sl.startswith("quotation") or "quo-" in sl:
        return "q"
    return "i"


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
    raise SystemExit("Set DB_CONNECTION_STRING or .streamlit/secrets.toml")


def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", type=Path, default=DEFAULT_QUTAION_DIR)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    folder: Path = args.folder.resolve()
    if not folder.is_dir():
        raise SystemExit(f"Folder not found: {folder}")

    os.environ["DB_CONNECTION_STRING"] = _load_conn_string()
    import psycopg2

    conn = psycopg2.connect(os.environ["DB_CONNECTION_STRING"], connect_timeout=30)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT base_id, note, client_name, amount
                FROM records
                WHERE note LIKE 'imported_pdf:%%'
                ORDER BY base_id
                """
            )
            rows = cur.fetchall()
        if not rows:
            print("No imported_pdf records found.")
            return

        updated = 0
        for base_id, note, old_client, old_amt in rows:
            fname = note.split(":", 1)[1].strip() if ":" in note else ""
            pdf = folder / fname
            if not pdf.is_file():
                print(f"SKIP missing file: {fname} (base_id={base_id})")
                continue

            patch = {
                "client_name": old_client or "-",
                "phone": "",
                "location": "",
                "amount": float(old_amt or 0),
            }
            merge_pdf_into_row(pdf, patch)
            new_type = _doc_type_from_filename(fname)

            if args.dry_run:
                print(
                    f"DRY {fname}: type->{new_type} client {old_client!r} -> {patch['client_name']!r} "
                    f"amt {old_amt} -> {patch['amount']}"
                )
                updated += 1
                continue

            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE records
                    SET type = %s, client_name = %s, phone = %s, location = %s, amount = %s
                    WHERE base_id = %s
                    """,
                    (
                        new_type,
                        patch["client_name"],
                        patch["phone"],
                        patch["location"],
                        patch["amount"],
                        base_id,
                    ),
                )
            updated += 1
            print(
                f"OK {fname}: type={new_type} client={patch['client_name']!r} amount={patch['amount']}"
            )

        if not args.dry_run:
            conn.commit()
        print(f"Done. Rows processed: {updated}.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
