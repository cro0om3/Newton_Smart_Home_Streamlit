import streamlit as st
import pandas as pd
from datetime import datetime
import os
try:
    from utils import db as _db
except Exception:
    _db = None


# ===== Excel Auto-Creation (as specified) =====
def ensure_excel_files():
    import pandas as pd
    import os

    if not os.path.exists("data"):
        os.makedirs("data")

    customers_path = "data/customers.xlsx"
    if not os.path.exists(customers_path):
        df = pd.DataFrame(columns=[
            "client_name",
            "phone",
            "location",
            "email",
            "status",
            "notes",
            "tags",
            "next_follow_up",
            "assigned_to",
            "last_activity"
        ])
        df.to_excel(customers_path, index=False)

    records_path = "data/records.xlsx"
    if not os.path.exists(records_path):
        df = pd.DataFrame(columns=[
            "base_id",
            "date",
            "type",
            "number",
            "amount",
            "client_name",
            "phone",
            "location",
            "note"
        ])
        df.to_excel(records_path, index=False)


# ===== Utilities =====
def proper_case(text):
    if not text:
        return ""
    try:
        return str(text).title().strip()
    except Exception:
        return str(text)


def format_phone_input(raw_input):
    if not raw_input:
        return None
    digits = ''.join(filter(str.isdigit, str(raw_input)))
    if digits.startswith("0"):
        digits = digits[1:]
    if digits.startswith("5") and len(digits) == 9:
        return f"+971 {digits[:2]} {digits[2:5]} {digits[5:]}"
    return None


def phone_flat10(raw_input):
    if raw_input is None:
        return ""
    digits = ''.join(filter(str.isdigit, str(raw_input)))
    if not digits:
        return ""
    if digits.startswith('971') and len(digits) >= 12 and digits[3] == '5':
        return '0' + digits[3:12]
    if len(digits) == 9 and digits.startswith('5'):
        return '0' + digits
    if len(digits) == 10 and digits.startswith('05'):
        return digits
    return digits[-10:]


def phone_label_mask(raw_input):
    flat = phone_flat10(raw_input)
    return f"{flat} xxxxxxxxxx" if flat else "xxxxxxxxxx"


# ===== Data IO =====
CUSTOMERS_XLSX = "data/customers.xlsx"
RECORDS_XLSX = "data/records.xlsx"


def load_customers():
    # Try loading from Postgres (non-intrusive). If DB unavailable or mismatch, fall back to Excel.
    if _db is not None:
        try:
            rows = _db.db_query('SELECT id, name, phone, email, address FROM customers ORDER BY id')
            if rows:
                df = pd.DataFrame(rows)
                # map DB columns to expected app columns
                df = df.rename(columns={'name': 'client_name', 'address': 'location'})
                # Ensure all expected columns exist
                for col in [
                    "client_name", "phone", "location", "email", "status",
                    "notes", "tags", "next_follow_up", "assigned_to", "last_activity"
                ]:
                    if col not in df.columns:
                        df[col] = None
                # Keep column order expected by app
                return df[[
                    "client_name", "phone", "location", "email", "status",
                    "notes", "tags", "next_follow_up", "assigned_to", "last_activity"
                ]]
        except Exception:
            # Any DB error -> fall back to Excel
            pass

    try:
        df = pd.read_excel(CUSTOMERS_XLSX)
    except Exception:
        df = pd.DataFrame(columns=[
            "client_name", "phone", "location", "email", "status",
            "notes", "tags", "next_follow_up", "assigned_to", "last_activity"
        ])
    df.columns = [c.strip().lower() for c in df.columns]
    for col in [
        "client_name", "phone", "location", "email", "status",
        "notes", "tags", "next_follow_up", "assigned_to", "last_activity"
    ]:
        if col not in df.columns:
            df[col] = None
    return df[[
        "client_name", "phone", "location", "email", "status",
        "notes", "tags", "next_follow_up", "assigned_to", "last_activity"
    ]]


def save_customers(df: pd.DataFrame):
    os.makedirs("data", exist_ok=True)
    # Try to persist to DB (non-intrusive). If DB ops fail, fall back to writing Excel only.
    if _db is not None:
        try:
            # For each row, attempt to upsert by matching name and phone
            for _, row in df.iterrows():
                name = str(row.get('client_name') or '')
                phone = row.get('phone')
                email = row.get('email')
                address = row.get('location')

                # Try find existing
                try:
                    existing = _db.db_query('SELECT id FROM customers WHERE name = %s AND phone = %s', (name, phone))
                except Exception:
                    existing = []

                if existing:
                    # update
                    try:
                        _db.db_execute('UPDATE customers SET email = %s, address = %s WHERE id = %s', (email, address, existing[0].get('id')))
                    except Exception:
                        # ignore per-row failure and continue
                        pass
                else:
                    try:
                        _db.db_execute('INSERT INTO customers(name, phone, email, address) VALUES (%s, %s, %s, %s)', (name, phone, email, address))
                    except Exception:
                        pass
            
            # After attempting DB sync, still write Excel to preserve full app fields
            df.to_excel(CUSTOMERS_XLSX, index=False)
            return
        except Exception:
            # Any DB-level error -> fall back to Excel-only
            pass

    # Default: write Excel file
    df.to_excel(CUSTOMERS_XLSX, index=False)


def load_records():
    # Try DB first
    if _db is not None:
        try:
            rows = _db.db_query('SELECT base_id, date, type, number, amount, client_name, phone, location, note FROM records ORDER BY date')
            if rows:
                df = pd.DataFrame(rows)
                df.columns = [c.strip().lower() for c in df.columns]
                return df
        except Exception:
            pass

    try:
        df = pd.read_excel(RECORDS_XLSX)
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame(columns=[
            "base_id", "date", "type", "number", "amount",
            "client_name", "phone", "location", "note"
        ])


def calculate_customer_finances(customer_name: str, customer_phone: str | None):
    rec = load_records()
    if rec.empty:
        return 0.0, 0.0, 0.0, 0.0
    # Normalize for matching
    cname = str(customer_name).strip().lower()
    cphone = phone_flat10(customer_phone) if customer_phone else ""
    # Build mask: prefer phone if available, else fallback to name
    name_mask = rec["client_name"].astype(str).str.strip().str.lower() == cname
    if "phone" in rec.columns:
        rec_phone_norm = rec["phone"].apply(phone_flat10)
        phone_mask = rec_phone_norm == cphone if cphone else False
    else:
        phone_mask = False
    mask = phone_mask | name_mask
    sub = rec[mask]
    total_q = sub[sub["type"] == "q"]["amount"].sum() if not sub.empty else 0.0
    total_i = sub[sub["type"] == "i"]["amount"].sum() if not sub.empty else 0.0
    total_r = sub[sub["type"] == "r"]["amount"].sum() if not sub.empty else 0.0
    outstanding = total_i - total_r
    return float(total_q or 0.0), float(total_i or 0.0), float(total_r or 0.0), float(outstanding or 0.0)


# ===== Main Page =====
def customers_app():
    ensure_excel_files()

    # UAE location list (same as quotation)
    uae_locations = [
        "Abu Dhabi - Al Shamkha","Abu Dhabi - Al Shawamekh","Abu Dhabi - Khalifa City",
        "Abu Dhabi - Al Bateen","Abu Dhabi - Al Reem Island","Abu Dhabi - Yas Island",
        "Abu Dhabi - Al Mushrif","Abu Dhabi - Al Rawdah","Abu Dhabi - Al Muroor",
        "Abu Dhabi - Baniyas","Abu Dhabi - Mussafah","Abu Dhabi - Al Mafraq",
        "Abu Dhabi - Al Falah","Abu Dhabi - MBZ City","Abu Dhabi - Al Raha",
        "Abu Dhabi - Al Maqtaa","Abu Dhabi - Zayed Port","Abu Dhabi - Saadiyat Island",
        "Al Ain - Al Jimi","Al Ain - Falaj Hazza","Al Ain - Al Maqam",
        "Al Ain - Zakher","Al Ain - Hili","Al Ain - Al Foah","Al Ain - Al Mutaredh",
        "Al Ain - Al Towayya","Al Ain - Al Sarooj","Al Ain - Al Nyadat",
        "Dubai - Marina","Dubai - Downtown","Dubai - Business Bay",
        "Dubai - Jumeirah","Dubai - JBR","Dubai - Al Barsha","Dubai - Mirdif",
        "Dubai - Deira","Dubai - Bur Dubai","Dubai - Silicon Oasis",
        "Dubai - Academic City","Dubai - Arabian Ranches","Dubai - International City",
        "Dubai - Dubai Hills","Dubai - The Springs","Dubai - The Meadows",
        "Dubai - The Greens","Dubai - Palm Jumeirah","Dubai - Al Qusais",
        "Dubai - Al Nahda","Dubai - JVC","Dubai - Damac Hills",
        "Dubai - Discovery Gardens","Dubai - IMPZ","Dubai - Al Warqa",
        "Dubai - Nad Al Sheba",
        "Sharjah - Al Majaz","Sharjah - Al Nahda","Sharjah - Al Taawun",
        "Sharjah - Muwaileh","Sharjah - Al Khan","Sharjah - Al Yarmook",
        "Sharjah - Al Qasimia","Sharjah - Al Fisht","Sharjah - Al Nasserya",
        "Sharjah - Al Goaz","Sharjah - Al Jubail","Sharjah - Maysaloon",
        "Ajman - Al Rashidiya","Ajman - Al Nuaimiya","Ajman - Al Mowaihat",
        "Ajman - Al Rawda","Ajman - Al Jurf","Ajman - Al Hamidiya",
        "Ajman - Al Rumailah","Ajman - Al Bustan","Ajman - City Center",
        "RAK - Al Nakheel","RAK - Al Dhait","RAK - Julph",
        "RAK - Khuzam","RAK - Al Qusaidat","RAK - Seih Al Uraibi",
        "RAK - Al Rams","RAK - Al Mairid","RAK - Mina Al Arab",
        "RAK - Al Hamra Village","RAK - Marjan Island",
    ]

    st.markdown("<div class='section-title'>Customers</div>", unsafe_allow_html=True)

    # Load Data
    customers = load_customers()
    records = load_records()

    # ---- Filters ----
    f1, f2, f3, f4, f5 = st.columns([2,1.2,1.2,1,1.2])
    with f1:
        q = st.text_input("Search name or phone")
    with f2:
        status_filter = st.selectbox("Status", options=["All","New","Follow-up","Active","Done","Lost"], index=0)
    with f3:
        location_filter = st.selectbox("Location", options=["All"] + sorted(list({x for x in customers["location"].dropna().astype(str)})))
    with f4:
        unpaid_only = st.checkbox("Unpaid only")
    with f5:
        emp_filter = st.selectbox("Assigned To", options=["All"] + sorted(list({x for x in customers["assigned_to"].dropna().astype(str)})))

    tbl = customers.copy()
    tbl["Client Name"] = tbl["client_name"].apply(proper_case)
    tbl["Phone"] = tbl["phone"].apply(lambda p: format_phone_input(p) or p)
    tbl["Location"] = tbl["location"].apply(proper_case)
    tbl["Status"] = tbl["status"].fillna("")
    tbl["Assigned To"] = tbl["assigned_to"].fillna("")
    tbl["Next Follow-up"] = tbl["next_follow_up"].fillna("")
    tbl["Last Activity"] = tbl["last_activity"].fillna("")

    # Pre-aggregate finance once per rerun (instead of per-row DB/file read).
    rec = records.copy()
    if rec.empty:
        tbl["Total Quotations (AED)"] = 0.0
        tbl["Total Invoices (AED)"] = 0.0
        tbl["Total Paid (AED)"] = 0.0
        tbl["Remaining (AED)"] = 0.0
    else:
        rec["type"] = rec["type"].astype(str).str.strip().str.lower().replace(
            {"quotation": "q", "invoice": "i", "receipt": "r"}
        )
        rec["amount"] = pd.to_numeric(rec.get("amount"), errors="coerce").fillna(0.0)
        rec["name_key"] = rec["client_name"].astype(str).str.strip().str.lower()
        rec["phone_key"] = rec["phone"].apply(phone_flat10) if "phone" in rec.columns else ""
        by_phone = rec[rec["phone_key"].astype(str) != ""].groupby(["phone_key", "type"], dropna=False)["amount"].sum().unstack(fill_value=0.0)
        by_name = rec.groupby(["name_key", "type"], dropna=False)["amount"].sum().unstack(fill_value=0.0)

        def compute_fin(row):
            p_key = phone_flat10(row.get("phone", ""))
            n_key = str(row.get("client_name", "")).strip().lower()
            src = by_phone.loc[p_key] if p_key and p_key in by_phone.index else (by_name.loc[n_key] if n_key in by_name.index else pd.Series(dtype="float64"))
            total_q = float(src.get("q", 0.0))
            total_i = float(src.get("i", 0.0))
            total_r = float(src.get("r", 0.0))
            return pd.Series({
                "Total Quotations (AED)": total_q,
                "Total Invoices (AED)": total_i,
                "Total Paid (AED)": total_r,
                "Remaining (AED)": total_i - total_r,
            })

        fin_cols = tbl.apply(compute_fin, axis=1)
        for c in ["Total Quotations (AED)", "Total Invoices (AED)", "Total Paid (AED)", "Remaining (AED)"]:
            tbl[c] = fin_cols[c]

    # Apply filters
    if q:
        ql = q.strip().lower()
        tbl = tbl[tbl.apply(lambda r: ql in str(r["Client Name"]).lower() or ql in str(r["Phone"]).lower(), axis=1)]
    if status_filter != "All":
        tbl = tbl[tbl["Status"].astype(str) == status_filter]
    if location_filter != "All":
        tbl = tbl[tbl["Location"].astype(str) == location_filter]
    if emp_filter != "All":
        tbl = tbl[tbl["Assigned To"].astype(str) == emp_filter]
    if unpaid_only:
        tbl = tbl[tbl["Remaining (AED)"] > 0]

    display_cols = [
        "Client Name","Phone","Location","Status","Last Activity",
        "Total Quotations (AED)","Total Invoices (AED)","Total Paid (AED)","Remaining (AED)",
        "Assigned To","Next Follow-up"
    ]
    st.dataframe(tbl[display_cols], use_container_width=True, hide_index=True)

    # ---- Add New Customer ----
    st.markdown("---")
    st.markdown("<div class='section-title'>Add New Customer</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        new_name = st.text_input("Client Name", key="new_c_name")
        new_phone = st.text_input("Phone", key="new_c_phone")
        new_location = st.selectbox("Location", options=[""] + uae_locations, key="new_c_loc")
        new_email = st.text_input("Email", key="new_c_email")
        new_status = st.selectbox("Status", ["New","Follow-up","Active","Done","Lost"], key="new_c_status")
    with c2:
        new_notes = st.text_area("Notes", key="new_c_notes", height=90)
        new_tags = st.text_input("Tags", key="new_c_tags", placeholder="vip, smart-home, ...")
        new_assigned = st.text_input("Assigned To", key="new_c_assigned")
        _new_next_has = st.checkbox("Set Next Follow-up date", value=False, key="new_c_next_has")
        new_next = st.date_input("Next Follow-up", value=datetime.today(), key="new_c_next") if _new_next_has else None

    if st.button("Add Customer"):
        cust = load_customers()
        row = {
            "client_name": proper_case(new_name),
            "phone": new_phone,
            "location": new_location,
            "email": new_email,
            "status": new_status,
            "notes": new_notes,
            "tags": new_tags,
            "next_follow_up": new_next.strftime('%Y-%m-%d') if new_next else "",
            "assigned_to": new_assigned,
            "last_activity": datetime.today().strftime('%Y-%m-%d'),
        }
        cust = pd.concat([cust, pd.DataFrame([row])], ignore_index=True)
        save_customers(cust)
        st.success(f"Saved {proper_case(new_name)}")
        st.rerun()

    # ---- Profile Panel ----
    st.markdown("---")
    st.markdown("<div class='section-title'>Customer Profile</div>", unsafe_allow_html=True)
    names = customers["client_name"].dropna().astype(str).tolist()
    labels = {n: f"{proper_case(n)}  |  {phone_label_mask(customers[customers['client_name']==n]['phone'].iloc[0])}" for n in names}
    selected_name = st.selectbox("Open Profile", options=[""] + names, format_func=lambda v: labels.get(v, v))

    if selected_name:
        row = customers[customers["client_name"].astype(str) == selected_name].iloc[0]
        total_q, total_i, total_r, outstanding = calculate_customer_finances(selected_name, row.get("phone"))

        cA, cB = st.columns([1,1])
        with cA:
            st.markdown("<div class='section-title'>Details</div>", unsafe_allow_html=True)
            st.write(f"Name: {proper_case(row['client_name'])}")
            st.write(f"Phone: {format_phone_input(row['phone']) or row['phone']}")
            st.write(f"Location: {proper_case(row['location'])}")
            st.write(f"Email: {row.get('email','')}")
            st.write(f"Status: {row.get('status','')}")
            st.write(f"Tags: {row.get('tags','')}")
            st.write(f"Assigned To: {row.get('assigned_to','')}")
            st.write(f"Next Follow-up: {row.get('next_follow_up','')}")
            st.write(f"Notes: {row.get('notes','')}")

            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("Edit Customer"):
                    st.session_state["_cust_editing"] = True
            with b2:
                if st.button("Delete Customer"):
                    cust = load_customers()
                    cust = cust[cust["client_name"].astype(str) != selected_name]
                    save_customers(cust)
                    st.success("Customer deleted")
                    st.rerun()
            with b3:
                pass

            cQ, cI, cR = st.columns(3)
            with cQ:
                if st.button("Create Quotation"):
                    st.session_state["active_page"] = "quotation"
                    st.session_state["client_name"] = proper_case(row['client_name'])
                    st.session_state["client_phone"] = phone_flat10(row['phone'])
                    st.session_state["client_location"] = row['location']
                    st.rerun()
            with cI:
                if st.button("Create Invoice"):
                    st.session_state["active_page"] = "invoice"
                    st.session_state["inv_mode"] = "New Invoice"
                    st.session_state["inv_client"] = proper_case(row['client_name'])
                    st.session_state["inv_phone"] = row['phone']
                    st.session_state["inv_loc"] = row['location']
                    st.rerun()
            with cR:
                if st.button("Create Receipt"):
                    st.session_state["active_page"] = "receipt"
                    st.rerun()

        with cB:
            st.markdown("<div class='section-title'>Financial Summary</div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style='background:#fff;border:1px solid rgba(0,0,0,.08);border-radius:12px;padding:16px;box-shadow:0 2px 6px rgba(0,0,0,.04);'>
                    <div style='display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,0,0,.06);'>
                        <span style='font-weight:600;color:#6e6e73;'>Total Quotations</span>
                        <span style='font-weight:700;color:#1d1d1f;'>{total_q:,.2f} AED</span>
                    </div>
                    <div style='display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,0,0,.06);'>
                        <span style='font-weight:600;color:#6e6e73;'>Total Invoices</span>
                        <span style='font-weight:700;color:#1d1d1f;'>{total_i:,.2f} AED</span>
                    </div>
                    <div style='display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,0,0,.06);'>
                        <span style='font-weight:600;color:#6e6e73;'>Total Received</span>
                        <span style='font-weight:700;color:#1d1d1f;'>{total_r:,.2f} AED</span>
                    </div>
                    <div style='display:flex;justify-content:space-between;padding:12px 0;background:rgba(0,0,0,.02);margin-top:8px;border-radius:8px;padding-left:12px;padding-right:12px;'>
                        <span style='font-weight:700;font-size:15px;color:#1d1d1f;'>Outstanding</span>
                        <span style='font-weight:700;font-size:17px;color:#1d1d1f;'>{outstanding:,.2f} AED</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Activity timeline
            st.markdown("<div class='section-title' style='margin-top:14px'>Activity Timeline</div>", unsafe_allow_html=True)
            client_rows = records[records["client_name"].astype(str).str.lower() == selected_name.lower()]
            if client_rows.empty:
                st.info("No activity recorded yet.")
            else:
                for _, r in client_rows.sort_values("date", ascending=False).iterrows():
                    t = r.get("type","?")
                    tname = "Quotation" if t=='q' else "Invoice" if t=='i' else "Receipt" if t=='r' else t
                    st.markdown(
                        f"{r.get('date','')} • {tname} • {r.get('number','')} • {float(r.get('amount',0)) :,.0f} AED"
                    )

        # Edit panel
        if st.session_state.get("_cust_editing"):
            st.markdown("---")
            st.markdown("<div class='section-title'>Edit Customer</div>", unsafe_allow_html=True)
            e1, e2 = st.columns(2)
            with e1:
                st.text_input("Client Name", value=row['client_name'], disabled=True)
                e_phone = st.text_input("Phone", value=row['phone'])
                e_location = st.selectbox("Location", options=[row['location']] + [l for l in uae_locations if l != row['location']])
                e_email = st.text_input("Email", value=row.get('email',''))
            with e2:
                e_status = st.selectbox("Status", ["New","Follow-up","Active","Done","Lost"], index=["New","Follow-up","Active","Done","Lost"].index(row.get('status','New')) if row.get('status','New') in ["New","Follow-up","Active","Done","Lost"] else 0)
                e_tags = st.text_input("Tags", value=row.get('tags',''))
                e_assigned = st.text_input("Assigned To", value=row.get('assigned_to',''))
                _has_next = st.checkbox("Has Next Follow-up", value=bool(str(row.get('next_follow_up','')).strip()))
                e_next = st.date_input("Next Follow-up", value=(pd.to_datetime(row.get('next_follow_up')).date() if str(row.get('next_follow_up','')).strip() else datetime.today()), disabled=not _has_next)
            e_notes = st.text_area("Notes", value=row.get('notes',''), height=80)

            if st.button("Save Changes"):
                cust = load_customers()
                idx = cust.index[cust["client_name"].astype(str) == selected_name][0]
                cust.loc[idx, [
                    "phone","location","email","status","notes","tags","next_follow_up","assigned_to","last_activity"
                ]] = [
                    e_phone, e_location, e_email, e_status, e_notes, e_tags,
                    e_next.strftime('%Y-%m-%d') if _has_next and e_next is not None else "",
                    e_assigned, datetime.today().strftime('%Y-%m-%d')
                ]
                save_customers(cust)
                st.session_state["_cust_editing"] = False
                st.success("Customer updated")
                st.rerun()
            if st.button("Cancel"):
                st.session_state["_cust_editing"] = False
                st.rerun()
