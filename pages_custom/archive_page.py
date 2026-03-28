from pathlib import Path
import pandas as pd
import streamlit as st

try:
    from utils import db as _db
except Exception:
    _db = None


@st.cache_data(ttl=10, show_spinner=False)
def _load_records() -> pd.DataFrame:
    cols = ["base_id", "date", "type", "number", "amount", "client_name", "phone", "location", "note"]
    if _db is not None:
        try:
            rows = _db.db_query(
                "SELECT base_id, date, type, number, amount, client_name, phone, location, note FROM records ORDER BY date DESC"
            )
            if rows:
                df = pd.DataFrame(rows)
                for c in cols:
                    if c not in df.columns:
                        df[c] = ""
                return df[cols]
        except Exception:
            pass
    try:
        df = pd.read_excel("data/records.xlsx")
        df.columns = [str(c).strip().lower() for c in df.columns]
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        return df[cols]
    except Exception:
        return pd.DataFrame(columns=cols)


@st.cache_data(ttl=10, show_spinner=False)
def _find_export_html(doc_type: str, number: str) -> Path | None:
    export_dir = Path("data") / "exports"
    if not export_dir.exists():
        return None

    number_str = str(number or "").strip()
    if not number_str:
        return None

    prefix_map = {"q": "Quotation", "i": "Invoice", "r": "Receipt"}
    prefix = prefix_map.get(str(doc_type).lower(), "")
    if not prefix:
        return None

    patterns = [
        f"{prefix}_*_{number_str}.html",
        f"{prefix}_{number_str}.html",
        f"{prefix}*{number_str}*.html",
    ]
    for pat in patterns:
        matches = sorted(export_dir.glob(pat), key=lambda p: p.stat().st_mtime, reverse=True)
        if matches:
            return matches[0]
    return None


def archive_app():
    st.markdown("## Archive")
    st.caption("Search and retrieve saved quotations, invoices, and receipts.")

    df = _load_records()
    if df.empty:
        st.info("No records found yet.")
        return

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["number"] = df["number"].astype(str)
    df["type"] = (
        df["type"]
        .astype(str)
        .str.strip()
        .str.lower()
        .replace({"quotation": "q", "invoice": "i", "receipt": "r"})
    )
    df["client_name"] = df["client_name"].astype(str)

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        type_opt = st.selectbox("Type", ["All", "Quotation", "Invoice", "Receipt"], index=0)
    with c2:
        date_from = st.date_input("From", value=None)
    with c3:
        q = st.text_input("Search", placeholder="Number, client name, phone...")

    type_map = {"Quotation": "q", "Invoice": "i", "Receipt": "r"}
    filtered = df.copy()
    if type_opt in type_map:
        filtered = filtered[filtered["type"] == type_map[type_opt]]
    if date_from is not None:
        filtered = filtered[filtered["date"].dt.date >= date_from]
    if q:
        qs = q.strip().lower()
        mask = (
            filtered["number"].str.lower().str.contains(qs, na=False)
            | filtered["client_name"].str.lower().str.contains(qs, na=False)
            | filtered["phone"].astype(str).str.lower().str.contains(qs, na=False)
        )
        filtered = filtered[mask]

    filtered = filtered.sort_values("date", ascending=False)
    st.write(f"Results: **{len(filtered)}**")
    if filtered.empty:
        st.warning("No matching records.")
        return

    label_map = {"q": "Quotation", "i": "Invoice", "r": "Receipt"}
    for i, row in filtered.iterrows():
        doc_type = str(row.get("type", "")).lower()
        number = str(row.get("number", ""))
        client = str(row.get("client_name", ""))
        amount = float(row.get("amount") or 0)
        d = row.get("date")
        d_text = d.strftime("%Y-%m-%d") if pd.notna(d) else "-"

        st.markdown("---")
        st.markdown(
            f"**{label_map.get(doc_type, doc_type.upper())}** `{number}` - {client}  \n"
            f"Date: `{d_text}` | Amount: `AED {amount:,.2f}` | Base ID: `{row.get('base_id', '')}`"
        )

        html_path = _find_export_html(doc_type, number)
        if html_path and html_path.exists():
            html_bytes = html_path.read_bytes()
            st.download_button(
                "Download HTML",
                data=html_bytes,
                file_name=html_path.name,
                mime="text/html",
                key=f"arch_html_{i}",
                use_container_width=True,
            )
        else:
            st.caption("HTML export file not found.")
