
import streamlit as st
import pandas as pd
from datetime import datetime
try:
    from utils import db as _db
except Exception:
    _db = None

# Apple-style icon grid for dashboard header
def _app_icon_grid():
    pass

# Apple Style Dashboard - Always visible structure


def _apply_dashboard_theme():
    # Use the app's global theme and styles — avoid page-specific heavy overrides
    # This keeps dashboard styling consistent with other pages.
    return
def _metric(title, value, subtitle=None):
    # Use the shared hero-card style from the global theme for consistent appearance
    st.markdown(
        f"""
        <div class="hero-card" style="text-align:center; padding:18px 20px;">
            <div style="font-size:28px;font-weight:700;color:var(--text-main);">{value}</div>
            <div style="font-size:18px;font-weight:500;color:var(--text-main);">{title}</div>
            <div style="font-size:15px;color:var(--accent);">{subtitle if subtitle else ""}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def dashboard_new_app():
    _apply_dashboard_theme()
    _app_icon_grid()
    # بيانات الداشبورد من Supabase فقط (بدون Excel)
    @st.cache_data(ttl=10, show_spinner=False)
    def _load_from_db(kind: str, columns):
        df = None
        if _db is None:
            return pd.DataFrame(columns=columns)
        try:
            if kind == "records":
                rows = _db.db_query(
                    "SELECT base_id, date, type, number, amount, client_name, phone, location, note FROM records ORDER BY date"
                )
                df = pd.DataFrame(rows)
                if not df.empty:
                    df.columns = [c.strip().lower() for c in df.columns]
                    if "date" in df.columns:
                        df["date"] = pd.to_datetime(df["date"], errors="coerce")
                    if "type" in df.columns:
                        df["type"] = (
                            df["type"]
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            .replace({"quotation": "q", "invoice": "i", "receipt": "r"})
                        )
                    if "amount" in df.columns:
                        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
            elif kind == "customers":
                rows = _db.db_query(
                    "SELECT name, phone, email, address FROM customers ORDER BY id"
                )
                df = pd.DataFrame(rows)
                if not df.empty:
                    df = df.rename(columns={"name": "client_name", "address": "location"})
                    df.columns = [c.strip().lower() for c in df.columns]
        except Exception:
            df = None

        if df is None:
            df = pd.DataFrame(columns=columns)
        for col in columns:
            if col not in df.columns:
                df[col] = None
        return df[columns]

    records = _load_from_db(
        "records",
        ["base_id", "date", "type", "number", "amount", "client_name", "phone", "location", "note"],
    )
    customers = _load_from_db(
        "customers",
        ["client_name", "phone", "location", "last_activity", "status"],
    )

    def _phone_flat10(raw):
        if raw is None:
            return ""
        s = str(raw).strip()
        if not s:
            return ""
        # Handle Excel float-like values such as 502992932.0000
        if "." in s:
            try:
                s = str(int(float(s)))
            except Exception:
                pass
        digits = "".join(ch for ch in s if ch.isdigit())
        if not digits:
            return ""
        if digits.startswith("971") and len(digits) >= 12 and digits[3] == "5":
            return "0" + digits[3:12]
        if len(digits) == 9 and digits.startswith("5"):
            return "0" + digits
        if len(digits) >= 10 and digits[-10:].startswith("05"):
            return digits[-10:]
        return digits[-10:] if len(digits) > 10 else digits

    def _phone_pretty(raw):
        flat = _phone_flat10(raw)
        if len(flat) == 10 and flat.startswith("05"):
            return f"+971 {flat[1:3]} {flat[3:6]} {flat[6:]}"
        return flat or ""

    rec = records.copy()
    if not rec.empty and "date" in rec.columns:
        rec["date"] = pd.to_datetime(rec["date"], errors="coerce")
    if "type" in rec.columns:
        rec["type"] = (
            rec["type"]
            .astype(str)
            .str.strip()
            .str.lower()
            .replace({"quotation": "q", "invoice": "i", "receipt": "r"})
        )

    # Clean Customer Signals for production display
    if not customers.empty:
        c = customers.copy()
        c["client_name"] = c["client_name"].astype(str).str.strip()
        c["location"] = c["location"].astype(str).str.strip()
        c["status"] = c["status"].astype(str).str.strip().replace({"": "New", "nan": "New", "None": "New"})
        c["last_activity_dt"] = pd.to_datetime(c["last_activity"], errors="coerce")
        c["last_activity"] = c["last_activity_dt"].dt.strftime("%Y-%m-%d").fillna("")
        c["phone_norm"] = c["phone"].apply(_phone_flat10)
        c["phone"] = c["phone"].apply(_phone_pretty)

        # De-duplicate exact customer duplicates, keep latest activity
        c = c.sort_values("last_activity_dt", ascending=False, na_position="last")
        c = c.drop_duplicates(subset=["client_name", "phone_norm", "location"], keep="first")
        c = c.drop(columns=["last_activity_dt"], errors="ignore")
        customers = c.reset_index(drop=True)

    total_q = int((rec["type"] == "q").sum()) if "type" in rec.columns else 0
    total_i = int((rec["type"] == "i").sum()) if "type" in rec.columns else 0
    total_r = int((rec["type"] == "r").sum()) if "type" in rec.columns else 0
    total_invoice_amount = float(rec.loc[rec.get("type","") == "i", "amount"].sum()) if "amount" in rec.columns else 0.0
    total_received = float(rec.loc[rec.get("type","") == "r", "amount"].sum()) if "amount" in rec.columns else 0.0
    remaining_balance = total_invoice_amount - total_received

    c1, c2, c3 = st.columns(3)
    with c1: _metric("Quotations", total_q, "Active proposals")
    with c2: _metric("Invoices", total_i, "Issued bills")
    with c3: _metric("Receipts", total_r, "Recorded payments")

    c4, c5, c6 = st.columns(3)
    with c4: _metric("Invoice Volume", f"AED {total_invoice_amount:,.0f}")
    with c5: _metric("Received", f"AED {total_received:,.0f}")
    with c6: _metric("Outstanding", f"AED {remaining_balance:,.0f}")

    st.markdown('<div class="section-title">Project Lifecycle Tracking</div>', unsafe_allow_html=True)
    st.markdown('<div class="table-wrap">', unsafe_allow_html=True)
    if rec.empty or "base_id" not in rec.columns:
        st.write("No lifecycle records yet.")
    else:
        rec_l = rec.copy()
        rec_l["base_id"] = rec_l["base_id"].astype(str)
        rec_l["amount"] = pd.to_numeric(rec_l.get("amount", 0), errors="coerce").fillna(0.0)
        if "date" in rec_l.columns:
            rec_l["date"] = pd.to_datetime(rec_l["date"], errors="coerce")

        lifecycle_rows = []
        for base_id, g in rec_l.groupby("base_id", dropna=False):
            q = g[g["type"] == "q"]
            i = g[g["type"] == "i"]
            r = g[g["type"] == "r"]
            invoiced = float(i["amount"].sum()) if not i.empty else 0.0
            received = float(r["amount"].sum()) if not r.empty else 0.0
            sample = g.sort_values("date", ascending=False).iloc[0]
            last_dt = sample.get("date")
            lifecycle_rows.append(
                {
                    "Base ID": base_id,
                    "Client": sample.get("client_name", ""),
                    "Phone": sample.get("phone", ""),
                    "Location": sample.get("location", ""),
                    "Quotation": not q.empty,
                    "Invoice": not i.empty,
                    "Receipt": not r.empty,
                    "Amount": invoiced,
                    "Balance": max(invoiced - received, 0.0),
                    "Last Update": last_dt.strftime("%Y-%m-%d") if pd.notna(last_dt) else "",
                }
            )

        lifecycle_data = pd.DataFrame(lifecycle_rows).sort_values("Last Update", ascending=False)
        for col in ["Quotation", "Invoice", "Receipt"]:
            lifecycle_data[col] = lifecycle_data[col].apply(
                lambda x: "<span style='font-size:22px;'>✅</span>" if x else "<span style='font-size:22px;'>❌</span>"
            )
        lifecycle_data["Amount"] = lifecycle_data["Amount"].apply(lambda x: f"{x:,.2f}")
        lifecycle_data["Balance"] = lifecycle_data["Balance"].apply(lambda x: f"{x:,.2f}")
        st.markdown(
            f"<div style='overflow-x:auto;'><table class='project-table'>{lifecycle_data.to_html(escape=False, index=False, classes='stTable')}</table></div>",
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    two1, two2 = st.columns(2)
    with two1:
        st.markdown('<div class="section-title">Latest Invoices</div>', unsafe_allow_html=True)
        st.markdown('<div class="table-wrap">', unsafe_allow_html=True)
        if not rec.empty and "type" in rec.columns:
            last_10_invoices = (
                rec[rec["type"] == "i"]
                .sort_values("date", ascending=False, na_position="last")
                .head(10)[["date", "number", "client_name", "amount"]]
            )
            if not last_10_invoices.empty:
                d = last_10_invoices.copy()
                if "date" in d.columns:
                    d["date"] = pd.to_datetime(d["date"], errors="coerce").dt.strftime("%Y-%m-%d")
                st.table(d.rename(columns={"date": "Date", "number": "Invoice", "client_name": "Client", "amount": "Amount (AED)"}))
            else:
                st.write("No invoices yet.")
        else:
            st.write("No invoices yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    with two2:
        st.markdown('<div class="section-title">Latest Receipts</div>', unsafe_allow_html=True)
        st.markdown('<div class="table-wrap">', unsafe_allow_html=True)
        if not rec.empty and "type" in rec.columns:
            last_10_receipts = (
                rec[rec["type"] == "r"]
                .sort_values("date", ascending=False, na_position="last")
                .head(10)[["date", "number", "client_name", "amount"]]
            )
            if not last_10_receipts.empty:
                d = last_10_receipts.copy()
                if "date" in d.columns:
                    d["date"] = pd.to_datetime(d["date"], errors="coerce").dt.strftime("%Y-%m-%d")
                st.table(d.rename(columns={"date": "Date", "number": "Receipt", "client_name": "Client", "amount": "Amount (AED)"}))
            else:
                st.write("No receipts yet.")
        else:
            st.write("No receipts yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Customer Signals</div>', unsafe_allow_html=True)
    st.markdown('<div class="table-wrap">', unsafe_allow_html=True)
    if not customers.empty:
        signals = customers.rename(
                columns={
                    "client_name": "Client",
                    "phone": "Phone",
                    "location": "Location",
                    "last_activity": "Last Activity",
                    "status": "Stage",
                }
            )
        for col in ["Client", "Phone", "Location", "Last Activity", "Stage"]:
            if col not in signals.columns:
                signals[col] = ""
        signals = signals[["Client", "Phone", "Location", "Last Activity", "Stage"]]
        st.table(signals)
    else:
        st.write("No customer records yet.")
    st.markdown('</div>', unsafe_allow_html=True)
