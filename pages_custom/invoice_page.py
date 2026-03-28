import streamlit as st
import pandas as pd
from datetime import datetime
import os
from pathlib import Path
from utils.quotation_utils import render_quotation_html
from utils.settings import load_settings
try:
    from utils import db as _db
except Exception:
    _db = None
from utils.image_utils import ensure_data_url


def proper_case(text):
    if not text:
        return ""
    try:
        return text.title().strip()
    except:
        return text


def invoice_app():
    # Phone formatter (same logic as quotation)
    def format_phone_input(raw_input):
        if not raw_input:
            return None
        digits = ''.join(filter(str.isdigit, str(raw_input)))
        if digits.startswith("0"):
            digits = digits[1:]
        if digits.startswith("5") and len(digits) == 9:
            return f"+971 {digits[:2]} {digits[2:5]} {digits[5:]}"
        return None
    # Phone as 10-digit local (0502992932) for labels

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

    # Page CSS (colors handled globally; keep geometry only)
    st.markdown("""
    <style>
    .hero{ border-radius:24px; padding:32px; backdrop-filter:blur(20px); margin-bottom:18px; }
    .hero h2{ margin:0 0 8px; font-size:32px; font-weight:700; }
    .hero p{ margin:0; font-size:15px; }
    .section-title{ font-size:20px; font-weight:700; margin:18px 0 10px; }

    .product-header{ display:flex; gap:1rem; padding:8px 0 12px; background:transparent; font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; margin-bottom:10px; align-items:center; }
    .product-header span{text-align:center;}
    .product-header span:nth-child(1){flex:4.5; text-align:left;}
    .product-header span:nth-child(2){flex:0.7;}
    .product-header span:nth-child(3){flex:1;}
    .product-header span:nth-child(4){flex:1;}
    .product-header span:nth-child(5){flex:0.7;}
    .product-header span:nth-child(6){flex:0.7;}

    .added-product-row{ padding:10px 14px; border-radius:12px; margin-bottom:6px; box-shadow:0 2px 6px rgba(0,0,0,.05); }
    .product-value{ font-weight:600; }
    </style>
    """, unsafe_allow_html=True)

    # (Header hero removed by request)

    # ---------------- LOAD DATA ----------------
    # Load product catalog (DB-first; fallback to Excel only when DB is unavailable)
    catalog = None
    db_checked = False
    if _db is not None:
        try:
            db_checked = True
            rows = _db.db_query(
                'SELECT device as "Device", description as "Description", unit_price as "UnitPrice", warranty as "Warranty", image_base64 as "ImageBase64", image_path as "ImagePath" FROM products ORDER BY id')
            catalog = pd.DataFrame(rows)
        except Exception:
            catalog = None
    if catalog is None and not db_checked:
        try:
            catalog = pd.read_excel("data/products.xlsx")
        except Exception:
            st.error("❌ Cannot load products.xlsx")
            return
    elif catalog is None:
        catalog = pd.DataFrame(columns=["Device", "Description", "UnitPrice", "Warranty", "ImageBase64", "ImagePath"])

    for col in ["Device", "Description", "UnitPrice", "Warranty", "ImageBase64", "ImagePath"]:
        if col not in catalog.columns:
            catalog[col] = None
    catalog["Device"] = catalog["Device"].astype(str).str.strip()
    catalog = catalog[catalog["Device"] != ""].copy()
    catalog = catalog.drop_duplicates(subset=["Device"], keep="first").reset_index(drop=True)

    # simple records list for quotations to pick from
    def load_records():
        # Try DB first then Excel
        if _db is not None:
            try:
                rows = _db.db_query(
                    'SELECT base_id, date, type, number, amount, client_name, phone, location, note FROM records ORDER BY date')
                if rows:
                    df = pd.DataFrame(rows)
                    df.columns = [c.strip().lower() for c in df.columns]
                    if "type" in df.columns:
                        df["type"] = (
                            df["type"]
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            .replace({"quotation": "q", "invoice": "i", "receipt": "r"})
                        )
                    return df
            except Exception:
                pass
        try:
            df = pd.read_excel("data/records.xlsx")
            df.columns = [c.strip().lower() for c in df.columns]
            if "type" in df.columns:
                df["type"] = (
                    df["type"]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .replace({"quotation": "q", "invoice": "i", "receipt": "r"})
                )
            return df
        except:
            return pd.DataFrame(columns=[
                "base_id", "date", "type", "number", "amount", "client_name", "phone", "location", "note"
            ])

            for r in raw_items:
                # Safely parse quantity from common keys
                qty = 0.0
                for k in ('Qty', 'qty', 'Quantity'):
                    try:
                        if k in r and r.get(k) is not None and str(r.get(k)).strip() != '':
                            qty = float(r.get(k))
                            break
                    except Exception:
                        continue
        if {"type", "number"}.issubset(df.columns):
            df = df.drop_duplicates(subset=["type", "number"], keep="last")

        df.to_excel("data/records.xlsx", index=False)

    # ---- Customers helpers (auto add/update) ----
    def ensure_customers_file():
        os.makedirs("data", exist_ok=True)
        path = "data/customers.xlsx"
        if not os.path.exists(path):
            cols = [
                "client_name", "phone", "location", "email", "status",
                "notes", "tags", "next_follow_up", "assigned_to", "last_activity"
            ]
            pd.DataFrame(columns=cols).to_excel(path, index=False)

    def load_customers():
        # Try DB then Excel
        if _db is not None:
            try:
                rows = _db.db_query(
                    'SELECT id, name, phone, email, address FROM customers ORDER BY id')
                if rows:
                    df = pd.DataFrame(rows)
                    df = df.rename(
                        columns={'name': 'client_name', 'address': 'location'})
                    df.columns = [c.strip().lower() for c in df.columns]
                    return df
            except Exception:
                pass
        ensure_customers_file()
        try:
            df = pd.read_excel("data/customers.xlsx")
            df.columns = [c.strip().lower() for c in df.columns]
            return df
        except Exception:
            return pd.DataFrame(columns=[
                "client_name", "phone", "location", "email", "status",
                "notes", "tags", "next_follow_up", "assigned_to", "last_activity"
            ])

    def save_customers(df: pd.DataFrame):
        os.makedirs("data", exist_ok=True)
        if _db is not None:
            try:
                for _, row in df.iterrows():
                    name = str(row.get('client_name') or '')
                    phone = row.get('phone')
                    email = row.get('email')
                    address = row.get('location')
                    try:
                        existing = _db.db_query(
                            'SELECT id FROM customers WHERE name = %s AND phone = %s', (name, phone))
                    except Exception:
                        existing = []
                    if existing:
                        try:
                            _db.db_execute('UPDATE customers SET email = %s, address = %s WHERE id = %s', (
                                email, address, existing[0].get('id')))
                        except Exception:
                            pass
                    else:
                        try:
                            _db.db_execute(
                                'INSERT INTO customers(name, phone, email, address) VALUES (%s,%s,%s,%s)', (name, phone, email, address))
                        except Exception:
                            pass
                df.to_excel("data/customers.xlsx", index=False)
                return
            except Exception:
                pass
        df.to_excel("data/customers.xlsx", index=False)

    def _norm_phone(x: str):
        digits = ''.join(filter(str.isdigit, str(x)))
        if digits.startswith('971') and len(digits) >= 12 and digits[3] == '5':
            return '0' + digits[3:12]
        if len(digits) == 9 and digits.startswith('5'):
            return '0' + digits
        if len(digits) == 10 and digits.startswith('05'):
            return digits
        return digits[-10:]

    def upsert_customer_from_invoice(name: str, phone: str, location: str):
        if not str(name).strip():
            return
        # Try DB upsert first, fallback to Excel
        if _db is not None:
            try:
                existing = []
                try:
                    existing = _db.db_query(
                        'SELECT id FROM customers WHERE name = %s OR phone = %s', (proper_case(name), phone))
                except Exception:
                    existing = []
                if existing:
                    try:
                        _db.db_execute('UPDATE customers SET phone = %s, address = %s WHERE id = %s', (
                            phone, proper_case(location), existing[0].get('id')))
                    except Exception:
                        pass
                else:
                    try:
                        _db.db_execute('INSERT INTO customers(name, phone, email, address) VALUES (%s,%s,%s,%s)', (proper_case(
                            name), phone, '', proper_case(location)))
                    except Exception:
                        pass
                return
            except Exception:
                pass

        cdf = load_customers()
        key = str(name).strip().lower()
        idx = None
        if not cdf.empty and "client_name" in cdf.columns:
            m = cdf["client_name"].astype(str).str.strip().str.lower() == key
            if m.any():
                idx = m[m].index[0]
            elif phone:
                cdf_phone = cdf.get("phone", pd.Series(
                    [], dtype=str)).apply(_norm_phone)
                target = _norm_phone(phone)
                pm = cdf_phone == target
                if pm.any():
                    idx = pm[pm].index[0]
        if idx is None:
            new_row = {
                "client_name": proper_case(name),
                "phone": phone,
                "location": proper_case(location),
                "email": "",
                "status": "Active",
                "notes": "",
                "tags": "",
                "next_follow_up": "",
                "assigned_to": "",
                "last_activity": datetime.today().strftime('%Y-%m-%d'),
            }
            cdf = pd.concat([cdf, pd.DataFrame([new_row])], ignore_index=True)
        else:
            cdf.loc[idx, "client_name"] = proper_case(name)
            if phone:
                cdf.loc[idx, "phone"] = phone
            if location:
                cdf.loc[idx, "location"] = proper_case(location)
            if not str(cdf.loc[idx, "status"]).strip():
                cdf.loc[idx, "status"] = "Active"
            cdf.loc[idx, "last_activity"] = datetime.today().strftime('%Y-%m-%d')
        save_customers(cdf)
    records = load_records()
    quotes_df = records[records["type"] == "q"].copy()

    # ---------------- LAYOUT: SAME ROWS ----------------
    st.markdown("<div class='section-title'>Invoice Summary</div>",
                unsafe_allow_html=True)

    mode = st.radio("Invoice Creation Method", [
                    "From Quotation", "New Invoice"], horizontal=True, key="inv_mode")

    # New numbering system: IYYYY#### (e.g., I20260001)
    current_year = datetime.today().year
    year_invoices = records[(records['type']=='i') & (records['number'].astype(str).str.startswith(f'I{current_year}'))]
    next_seq = len(year_invoices) + 1
    auto_no = f"I{current_year}{str(next_seq).zfill(4)}"

    # Prefill defaults from previously selected quotation (before rendering widgets)
    sel_default_name = ""
    sel_default_loc = ""
    sel_default_phone = ""
    if mode == "From Quotation":
        selected_q = st.session_state.get("q_select_inline", None)
        if selected_q:
            try:
                q_prefill = records[records["number"] == selected_q].iloc[0]
                sel_default_name = str(q_prefill.get("client_name", "") or "")
                sel_default_loc = str(q_prefill.get("location", "") or "")
                sel_default_phone = str(q_prefill.get("phone", "") or "")
            except Exception:
                pass
    else:
        selected_q = None

    # If a quotation was just selected, prefill and rerun so inputs show values
    if mode == "From Quotation":
        current_q = st.session_state.get("q_select_inline")
        last_q = st.session_state.get("_last_q_selected")
        if current_q and current_q != last_q:
            try:
                q_prefill = records[records["number"] == current_q].iloc[0]
                st.session_state["inv_client"] = str(q_prefill.get("client_name", "") or "")
                st.session_state["inv_loc"] = str(q_prefill.get("location", "") or "")
                st.session_state["inv_phone"] = str(q_prefill.get("phone", "") or "")
            except Exception:
                pass
            st.session_state["_last_q_selected"] = current_q
            st.rerun()

    # Row 1: Name | Invoice Number
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        client_name = st.text_input(
            "Client Name", value=sel_default_name, key="inv_client")
    with r1c2:
        invoice_no = st.text_input(
            "Invoice Number", auto_no, disabled=True, key="inv_no")

    # UAE Locations (same as quotation)
    uae_locations = [
        "Abu Dhabi - Al Shamkha", "Abu Dhabi - Al Shawamekh", "Abu Dhabi - Khalifa City",
        "Abu Dhabi - Al Bateen", "Abu Dhabi - Al Reem Island", "Abu Dhabi - Yas Island",
        "Abu Dhabi - Al Mushrif", "Abu Dhabi - Al Rawdah", "Abu Dhabi - Al Muroor",
        "Abu Dhabi - Baniyas", "Abu Dhabi - Mussafah", "Abu Dhabi - Al Mafraq",
        "Abu Dhabi - Al Falah", "Abu Dhabi - MBZ City", "Abu Dhabi - Al Raha",
        "Abu Dhabi - Al Maqtaa", "Abu Dhabi - Zayed Port", "Abu Dhabi - Saadiyat Island",
        "Al Ain - Al Jimi", "Al Ain - Falaj Hazza", "Al Ain - Al Maqam",
        "Al Ain - Zakher", "Al Ain - Hili", "Al Ain - Al Foah", "Al Ain - Al Mutaredh",
        "Al Ain - Al Towayya", "Al Ain - Al Sarooj", "Al Ain - Al Nyadat",
        "Dubai - Marina", "Dubai - Downtown", "Dubai - Business Bay",
        "Dubai - Jumeirah", "Dubai - JBR", "Dubai - Al Barsha", "Dubai - Mirdif",
        "Dubai - Deira", "Dubai - Bur Dubai", "Dubai - Silicon Oasis",
        "Dubai - Academic City", "Dubai - Arabian Ranches", "Dubai - International City",
        "Dubai - Dubai Hills", "Dubai - The Springs", "Dubai - The Meadows",
        "Dubai - The Greens", "Dubai - Palm Jumeirah", "Dubai - Al Qusais",
        "Dubai - Al Nahda", "Dubai - JVC", "Dubai - Damac Hills",
        "Dubai - Discovery Gardens", "Dubai - IMPZ", "Dubai - Al Warqa",
        "Dubai - Nad Al Sheba",
        "Sharjah - Al Majaz", "Sharjah - Al Nahda", "Sharjah - Al Taawun",
        "Sharjah - Muwaileh", "Sharjah - Al Khan", "Sharjah - Al Yarmook",
        "Sharjah - Al Qasimia", "Sharjah - Al Fisht", "Sharjah - Al Nasserya",
        "Sharjah - Al Goaz", "Sharjah - Al Jubail", "Sharjah - Maysaloon",
        "Ajman - Al Rashidiya", "Ajman - Al Nuaimiya", "Ajman - Al Mowaihat",
        "Ajman - Al Rawda", "Ajman - Al Jurf", "Ajman - Al Hamidiya",
        "Ajman - Al Rumailah", "Ajman - Al Bustan", "Ajman - City Center",
        "RAK - Al Nakheel", "RAK - Al Dhait", "RAK - Julph",
        "RAK - Khuzam", "RAK - Al Qusaidat", "RAK - Seih Al Uraibi",
        "RAK - Al Rams", "RAK - Al Mairid", "RAK - Mina Al Arab",
        "RAK - Al Hamra Village", "RAK - Marjan Island",
        "Fujairah - Al Faseel", "Fujairah - Madhab", "Fujairah - Dibba",
        "Fujairah - Sakamkam", "Fujairah - Mirbah", "Fujairah - Al Taween",
        "Fujairah - Kalba", "Fujairah - Qidfa", "Fujairah - Al Aqah",
        "UAQ - Al Salama", "UAQ - Al Haditha", "UAQ - Al Raas",
        "UAQ - Al Dar Al Baida", "UAQ - Al Khor", "UAQ - Al Ramlah",
        "UAQ - Al Maidan", "UAQ - Emirates City",
    ]

    # Row 2: Location | Select Quotation
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        default_loc_index = uae_locations.index(
            sel_default_loc) if sel_default_loc in uae_locations else 0
        selected_loc = st.selectbox(
            "Project Location (UAE)", uae_locations, index=default_loc_index, key="inv_loc")
        client_location = proper_case(selected_loc)
    with r2c2:
        if mode == "From Quotation":
            if not quotes_df.empty:
                df = quotes_df.fillna("")
                numbers = df["number"].astype(str).tolist()
                labels = {}
                for _, row in df.iterrows():
                    client = str(row.get('client_name', 'N/A'))
                    phone_raw = row.get('phone', '')
                    # Format phone: +971 50 299 2932 or 050-299-2932
                    if phone_raw and str(phone_raw) != 'nan':
                        # Handle float values from Excel (502992932.0 → 502992932)
                        if isinstance(phone_raw, float):
                            digits = str(int(phone_raw))
                        else:
                            digits = ''.join(filter(str.isdigit, str(phone_raw)))
                        
                        if digits.startswith('971') and len(digits) >= 12:
                            # International format: +971 50 299 2932
                            phone = f"+971 {digits[3:5]} {digits[5:8]} {digits[8:12]}"
                        elif digits.startswith('05') and len(digits) == 10:
                            # Local format: 050-299-2932
                            phone = f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
                        elif digits.startswith('5') and len(digits) == 9:
                            # Add leading 0: 050-299-2932
                            phone = f"0{digits[0:2]}-{digits[2:5]}-{digits[5:9]}"
                        else:
                            phone = digits if digits else 'N/A'
                    else:
                        phone = 'N/A'
                    quo_num = str(row['number'])
                    labels[quo_num] = f"{client} | {phone} | {quo_num}"

                selected_q = st.selectbox(
                    "Select Quotation",
                    options=numbers if numbers else ["No quotations"],
                    key="q_select_inline",
                    format_func=lambda n: labels.get(n, n),
                )
            else:
                st.info("No quotations found in records")

    # Row 3: Phone | spacer
    r3c1, r3c2 = st.columns(2)
    with r3c1:
        phone_raw = st.text_input(
            "Mobile Number", placeholder="050xxxxxxx", key="quo_phone")
        client_phone = format_phone_input(phone_raw)
        if client_phone:
            st.success(f" {client_phone}")
    with r3c2:
        st.write("")  # keep grid aligned

    # ---------- ITEMS (same logic/visuals as Quotation) ----------
    if "invoice_table" not in st.session_state:
        st.session_state.invoice_table = pd.DataFrame(columns=[
            "Item No", "Product / Device", "Description", "Qty", "Unit Price (AED)", "Line Total (AED)", "Warranty (Years)"
        ])

    st.markdown("---")
    st.markdown("<div class='section-title'>Add Product</div>",
                unsafe_allow_html=True)

    st.markdown("""
    <div class="product-header">
      <span>Product / Device</span>
      <span>Qty</span>
      <span>Unit Price</span>
      <span>Line Total</span>
      <span>Warranty</span>
      <span>Action</span>
    </div>
    """, unsafe_allow_html=True)

    df = st.session_state.invoice_table.copy()
    if not df.empty:
        for i, row in df.iterrows():
            cols = st.columns([4.5, 0.7, 1, 1, 0.7, 0.7])
            with cols[0]:
                st.markdown(
                    f"<div class='added-product-row'><b>✓ {row['Product / Device']}</b></div>", unsafe_allow_html=True)
            with cols[1]:
                st.markdown(
                    f"<div class='added-product-row'><span class='product-value'>{int(row['Qty'])}</span></div>", unsafe_allow_html=True)
            with cols[2]:
                st.markdown(
                    f"<div class='added-product-row'><span class='product-value'>{row['Unit Price (AED)']:.2f}</span></div>", unsafe_allow_html=True)
            with cols[3]:
                st.markdown(
                    f"<div class='added-product-row'><span class='product-value'>AED {row['Line Total (AED)']:.2f}</span></div>",
                    unsafe_allow_html=True
                )
            with cols[4]:
                st.markdown(
                    f"<div class='added-product-row'><span class='product-value'>{int(row['Warranty (Years)'])} yr</span></div>", unsafe_allow_html=True)
            with cols[5]:
                if st.button("❌", key=f"delete_{i}"):
                    st.session_state.invoice_table = st.session_state.invoice_table.drop(
                        i).reset_index(drop=True)
                    st.session_state.invoice_table["Item No"] = range(
                        1, len(st.session_state.invoice_table)+1)
                    st.rerun()

    if catalog.empty:
        st.warning("No products found in database. Add products first from Products page.")
        st.stop()

    e = st.columns([4.5, 0.7, 1, 1, 0.7, 0.7])
    with e[0]:
        product = st.selectbox(
            "Product", options=catalog["Device"].tolist(), key="add_prod", label_visibility="collapsed")
        match = catalog[catalog["Device"].astype(str) == str(product).strip()]
        if match.empty:
            match = catalog.iloc[[0]]
        row = match.iloc[0]
        desc = row.get("Description", "")
    # Sync defaults when product changes
    if st.session_state.get("last_prod_inv") != product:
        if "price_inv" not in st.session_state:
            st.session_state["price_inv"] = float(row["UnitPrice"])
        else:
            st.session_state["price_inv"] = float(row["UnitPrice"])
        if "war_inv" not in st.session_state:
            st.session_state["war_inv"] = int(row["Warranty"])
        else:
            st.session_state["war_inv"] = int(row["Warranty"])
        if "qty_inv" not in st.session_state:
            st.session_state["qty_inv"] = 1
        else:
            st.session_state["qty_inv"] = 1
        st.session_state["last_prod_inv"] = product

    # Ensure keys exist (do not pass value= to widget)
    if "qty_inv" not in st.session_state:
        st.session_state["qty_inv"] = 1
    if "price_inv" not in st.session_state:
        st.session_state["price_inv"] = float(row["UnitPrice"])
    if "war_inv" not in st.session_state:
        st.session_state["war_inv"] = int(row["Warranty"])

    with e[1]:
        qty = st.number_input("Qty", min_value=1, step=1,
                              label_visibility="collapsed", key="qty_inv")
    with e[2]:
        price = st.number_input(
            "Unit Price (AED)", step=10.0, label_visibility="collapsed", key="price_inv")
    line_total = qty * price
    with e[3]:
        st.markdown(
            f"<div class='added-product-row'><span class='product-value'>AED {line_total:.2f}</span></div>",
            unsafe_allow_html=True
        )
    with e[4]:
        warranty = st.number_input("Warranty (Years)", min_value=0, value=st.session_state.get(
            "war_inv", int(row["Warranty"])), step=1, label_visibility="collapsed", key="war_inv")
    with e[5]:
        if st.button("✅", key="add_inv_btn"):
            # Attempt to attach image info from catalog (prefer Base64)
            image_val = None
            try:
                raw_b64 = row.get(
                    'ImageBase64') if 'ImageBase64' in row.index else None
                image_val = ensure_data_url(
                    raw_b64) if raw_b64 is not None else None
            except Exception:
                image_val = None

            new_item = {
                "Item No": len(st.session_state.invoice_table) + 1,
                "Product / Device": product,
                "Description": desc,
                "Qty": qty,
                "Unit Price (AED)": price,
                "Line Total (AED)": line_total,
                "Warranty (Years)": warranty,
                "ImagePath": row.get('ImagePath') if 'ImagePath' in row.index else None,
                "ImageBase64": row.get('ImageBase64') if 'ImageBase64' in row.index else None,
                "image": image_val,
            }
            if st.session_state.invoice_table.empty:
                st.session_state.invoice_table = pd.DataFrame([new_item])
            else:
                st.session_state.invoice_table = pd.concat(
                    [st.session_state.invoice_table, pd.DataFrame([new_item])], ignore_index=True
                )
            st.rerun()

    # ---------- SUMMARY ----------
    st.markdown("---")

    # Two columns: Summary Table (left) | Installation & Discount (right)
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("<div class='section-title'>Project Costs</div>",
                    unsafe_allow_html=True)

        # Professional summary table (like receipt)
        product_total = st.session_state.invoice_table["Line Total (AED)"].sum(
        )

        # Calculate installation/discount (needs to be defined before display)
        installation_cost = st.session_state.get("install_cost_inv_value", 0.0)
        discount_value = st.session_state.get("disc_value_inv_value", 0.0)
        discount_percent = st.session_state.get("disc_percent_inv_value", 0.0)

        percent_value = (product_total + installation_cost) * \
            (discount_percent / 100)
        total_discount = percent_value + discount_value
        grand_total = (product_total + installation_cost) - total_discount

        st.markdown("""
        <div style='background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:16px;'>
            <div style='display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border-soft);'>
                <span style='font-weight:600;color:var(--text-soft);'>Price (AED)</span>
                <span style='font-weight:700;color:var(--text);'>{:,.2f} AED</span>
            </div>
            <div style='display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border-soft);'>
                <span style='font-weight:600;color:var(--text-soft);'>Installation & Operation Devices</span>
                <span style='font-weight:700;color:var(--text);'>{:,.2f} AED</span>
            </div>
            <div style='display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border-soft);'>
                <span style='font-weight:600;color:var(--text-soft);'>Discount</span>
                <span style='font-weight:700;color:var(--text);'>-{:,.2f} AED</span>
            </div>
            <div style='display:flex;justify-content:space-between;padding:15px 0;background:var(--bg-input);margin-top:8px;border-radius:8px;padding-left:12px;padding-right:12px;'>
                <span style='font-weight:700;font-size:16px;color:var(--text);'>TOTAL AMOUNT</span>
                <span style='font-weight:700;font-size:18px;color:var(--text);'>{:,.2f} AED</span>
            </div>
        </div>
        """.format(product_total, installation_cost, total_discount, grand_total), unsafe_allow_html=True)

    with col_right:
        st.markdown(
            "<div class='section-title'>Installation & Discount</div>", unsafe_allow_html=True)

        # Installation Cost
        installation_cost = st.number_input(
            "Installation & Operation Devices (AED)", min_value=0.0, step=50.0, key="install_cost_inv")
        st.session_state["install_cost_inv_value"] = installation_cost

        # Discount section
        st.markdown("<div style='margin-top:12px;'></div>",
                    unsafe_allow_html=True)
        cD1, cD2 = st.columns(2)
        with cD1:
            discount_value = st.number_input(
                "Discount Value (AED)", min_value=0.0, key="disc_value_inv")
            st.session_state["disc_value_inv_value"] = discount_value
        with cD2:
            discount_percent = st.number_input(
                "Discount %", min_value=0.0, max_value=100.0, key="disc_percent_inv")
            st.session_state["disc_percent_inv_value"] = discount_percent

    # ======================================================
    #      PAYMENT TERMS
    # ======================================================
    st.markdown("---")
    st.markdown("<div class='section-title'>Payment Terms</div>",
                unsafe_allow_html=True)

    # Initialize session state for payment terms if not exists
    if 'payment_terms_count' not in st.session_state:
        st.session_state.payment_terms_count = 2
    if 'payment_terms' not in st.session_state:
        st.session_state.payment_terms = [
            {'percent': 30, 'description': 'upon contract signing, covering smart home infrastructure works including cabling, wiring, point preparation, and technical layouts.'},
            {'percent': 70, 'description': 'upon supply of smart home devices, including installation, system programming, configuration, testing, and commissioning.'},
        ]

    # Quick preset buttons
    col_presets = st.columns(3)
    with col_presets[0]:
        if st.button("📋 Preset: 30-70", use_container_width=True):
            st.session_state.payment_terms_count = 2
            st.session_state.payment_terms = [
                {'percent': 30, 'description': 'upon contract signing, covering smart home infrastructure works including cabling, wiring, point preparation, and technical layouts.'},
                {'percent': 70, 'description': 'upon supply of smart home devices, including installation, system programming, configuration, testing, and commissioning.'},
            ]
            st.rerun()

    with col_presets[1]:
        if st.button("📋 Preset: 50-50", use_container_width=True):
            st.session_state.payment_terms_count = 2
            st.session_state.payment_terms = [
                {'percent': 50, 'description': 'upon order confirmation'},
                {'percent': 50, 'description': 'upon project completion and handover'},
            ]
            st.rerun()

    with col_presets[2]:
        if st.button("📋 Preset: 30-60-10", use_container_width=True):
            st.session_state.payment_terms_count = 3
            st.session_state.payment_terms = [
                {'percent': 30, 'description': 'upon contract signing, covering smart home infrastructure works including cabling, wiring, point preparation, and technical layouts.'},
                {'percent': 60, 'description': 'upon supply of smart home devices, including installation, system programming, configuration, testing, and commissioning.'},
                {'percent': 10, 'description': 'upon final project handover, system completion, client approval.'},
            ]
            st.rerun()

    st.markdown("<div style='margin:12px 0;'></div>", unsafe_allow_html=True)

    # Dynamic payment terms inputs
    st.markdown("**Add/Edit Payment Terms:**")

    payment_terms_list = []
    for i in range(st.session_state.payment_terms_count):
        col_term = st.columns([1, 3, 1])

        # Get existing value or default
        existing_term = st.session_state.payment_terms[i] if i < len(
            st.session_state.payment_terms) else {'percent': 0, 'description': ''}

        with col_term[0]:
            percent = st.number_input(f"% Payment {i+1}", min_value=0.0, max_value=100.0,
                                      value=float(existing_term.get('percent', 0)), step=1.0, key=f"payment_percent_{i}")

        with col_term[1]:
            description = st.text_input(f"Description {i+1}",
                                        value=existing_term.get(
                                            'description', ''),
                                        placeholder="e.g., upon contract signing...",
                                        key=f"payment_desc_{i}")

        with col_term[2]:
            if st.button("🗑️", key=f"delete_payment_{i}", help="Remove this payment term"):
                st.session_state.payment_terms_count -= 1
                st.session_state.payment_terms.pop(i)
                st.rerun()

        payment_terms_list.append(
            {'percent': percent, 'description': description})

    # Update session state with current values
    st.session_state.payment_terms = payment_terms_list

    # Add new term button
    if st.button("➕ Add Payment Term", use_container_width=True):
        st.session_state.payment_terms_count += 1
        st.session_state.payment_terms.append(
            {'percent': 0, 'description': ''})
        st.rerun()

    # ======================================================
    #      WARRANTY & LIABILITY
    # ======================================================
    st.markdown("<div class='section-title'>Warranty & Liability</div>",
                unsafe_allow_html=True)

    if 'warranty_shipping_cost' not in st.session_state:
        st.session_state.warranty_shipping_cost = 100.0

    if 'warranty_text' not in st.session_state:
        st.session_state.warranty_text = """Warranty is provided for manufacturing defects only. This does not cover:
• Wear and tear, misuse, or improper maintenance.
• External damages or influences beyond our control.
• Any third-party modifications to hardware or software.

Warranty claims must be submitted within two months of defect detection.
Clients are responsible for shipping costs (AED {shipping_cost}) related to warranty claims.
No cash refunds are provided under any circumstances."""

    col_warranty = st.columns([2, 1])

    with col_warranty[0]:
        warranty_text = st.text_area(
            "Warranty & Liability Text:",
            value=st.session_state.warranty_text,
            height=150,
            help="Use {shipping_cost} placeholder for dynamic cost",
            key="warranty_text_input"
        )
        st.session_state.warranty_text = warranty_text

    with col_warranty[1]:
        shipping_cost = st.number_input(
            "Shipping Cost (AED):",
            min_value=0.0,
            value=st.session_state.warranty_shipping_cost,
            step=10.0,
            key="warranty_cost_input"
        )
        st.session_state.warranty_shipping_cost = shipping_cost

    # ======================================================
    #      PROJECT DETAILS
    # ======================================================
    st.markdown("<div class='section-title'>Project Details</div>",
                unsafe_allow_html=True)

    if 'project_title' not in st.session_state:
        st.session_state.project_title = ""
    if 'project_description' not in st.session_state:
        st.session_state.project_description = ""

    col_project = st.columns([2, 1])

    with col_project[0]:
        project_title = st.text_input(
            "Project Title:",
            value=st.session_state.project_title,
            placeholder="e.g., Smart Home Setup - Villa Al Manara",
            key="project_title_input"
        )
        st.session_state.project_title = project_title

    with col_project[1]:
        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
        # Load API key from settings
        settings = load_settings()
        api_key = settings.get('openai_api_key', '').strip(
        ) if settings.get('openai_api_key') else ''

        if api_key:
            if st.button("✨ AI Generate", use_container_width=True, help="Auto-generate description using ChatGPT"):
                from utils.openai_utils import generate_project_description
                raw_items = df_to_list(st.session_state.get(
                    'invoice_table', pd.DataFrame()))
                try:
                    generated = generate_project_description(
                        raw_items, api_key)
                    if generated:
                        st.session_state.project_description = generated
                        st.success("✓ Description generated!")
                        st.rerun()
                    else:
                        st.warning(
                            "Could not generate description. Check your OpenAI API key or product list.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.info("💡 Add OpenAI API key in Settings to enable AI generation")

    project_description = st.text_area(
        "Project Description:",
        value=st.session_state.project_description,
        placeholder="Describe the project scope, devices to be installed, and work to be performed...",
        height=120,
        key="project_desc_input"
    )
    st.session_state.project_description = project_description

    # ======================================================
    #      DELIVERY & INSTALLATION
    # ======================================================
    st.markdown("<div class='section-title'>Delivery & Installation</div>",
                unsafe_allow_html=True)

    # Power provider dropdown - mapped by location
    power_providers = {
        "Abu Dhabi": "ADDC – Abu Dhabi",
        "Dubai": "DEWA – Dubai",
        "Sharjah": "SEWA – Sharjah",
        "Ajman": "EWE – Ajman",
        "Umm Al Quwain": "EWE – Umm Al Quwain",
        "Ras Al Khaimah": "FEWA – Ras Al Khaimah",
        "Fujairah": "EWE – Fujairah",
    }

    if 'power_provider' not in st.session_state:
        # Try to auto-select based on location
        client_location = st.session_state.get('inv_loc', '').strip()
        default_provider = None
        for location, provider in power_providers.items():
            if location.lower() in client_location.lower():
                default_provider = provider
                break
        st.session_state.power_provider = default_provider or "ADDC – Abu Dhabi"

    col_delivery = st.columns([2, 1])

    with col_delivery[0]:
        power_provider = st.selectbox(
            "Power Provider (excluded from installation scope):",
            options=list(power_providers.values()),
            index=list(power_providers.values()).index(
                st.session_state.power_provider) if st.session_state.power_provider in power_providers.values() else 0,
            key="power_provider_select"
        )
        st.session_state.power_provider = power_provider

    with col_delivery[1]:
        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Auto-detect", use_container_width=True, help="Auto-detect based on location"):
            client_location = st.session_state.get('inv_loc', '').strip()
            for location, provider in power_providers.items():
                if location.lower() in client_location.lower():
                    st.session_state.power_provider = provider
                    st.rerun()

    # Editable delivery & installation text (persisted to session)
    if 'inv_delivery_text' not in st.session_state:
        default_delivery = (
            "Estimated delivery time: 7–45 days from the date of receipt of the device supply payment.\n"
            "Installation includes testing, commissioning, and programming.\n"
            "Installation excludes the following:\n"
            "- Power supply sources and any related failures or interruptions.\n"
            "- Any structural or civil modifications required for installation works."
        )
        st.session_state.inv_delivery_text = default_delivery

    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
    delivery_text = st.text_area(
        "Delivery & Installation Text:",
        value=st.session_state.get('inv_delivery_text', ''),
        height=160,
        placeholder="Enter any specific delivery, installation exclusions or notes here...",
        key="inv_delivery_text_input"
    )
    st.session_state.inv_delivery_text = delivery_text

    # ======================================================
    #      EXPORT - SIMPLIFIED (HTML Only + Save)
    # ======================================================
    st.markdown("---")
    st.markdown('<div class="section-title">Download Invoice</div>',
                unsafe_allow_html=True)

    # Recalculate totals
    formatted_phone = format_phone_input(phone_raw) or phone_raw
    product_total = st.session_state.invoice_table["Line Total (AED)"].sum()
    installation_cost = st.session_state.get("install_cost_inv_value", 0.0)
    discount_value = st.session_state.get("disc_value_inv_value", 0.0)
    discount_percent = st.session_state.get("disc_percent_inv_value", 0.0)
    percent_value = (product_total + installation_cost) * (discount_percent / 100)
    total_discount = percent_value + discount_value
    grand_total = (product_total + installation_cost) - total_discount

    # Generate HTML Invoice
    try:
        # Prepare items
        raw_items = st.session_state.invoice_table.to_dict('records') if 'invoice_table' in st.session_state else []
        norm_items = []
        for r in raw_items:
            try:
                qty_val = r.get('Qty')
                qty = 0.0 if qty_val is None or qty_val == '' else float(qty_val)
            except Exception:
                qty = 0.0
            try:
                unit_price = float(r.get('Unit Price (AED)') or r.get('Unit Price') or r.get('unit_price') or 0)
            except Exception:
                unit_price = 0.0
            try:
                total = float(r.get('Line Total (AED)') or r.get('total') or qty * unit_price)
            except Exception:
                total = qty * unit_price
            item = {
                'description': r.get('Description') or r.get('Product / Device') or r.get('Product') or r.get('Device') or '',
                'qty': qty,
                'unit_price': unit_price,
                'total': total,
                'warranty': r.get('Warranty (Years)') or r.get('Warranty') or r.get('war_inv') or '',
                'ImagePath': None,
                'ImageBase64': r.get('ImageBase64') if 'ImageBase64' in r else None,
                'image': (r.get('image') if 'image' in r else ensure_data_url(r.get('ImageBase64') if 'ImageBase64' in r else None)),
            }
            norm_items.append(item)

        # Calculate payment details
        down_payment = float(st.session_state.get('inv_down_payment', 0.0) or 0.0)
        previously_paid = float(st.session_state.get('inv_previously_paid', 0.0) or 0.0)
        balance_due = grand_total - down_payment - previously_paid

        # Build payment terms HTML
        payment_terms_html = ""
        payment_terms = st.session_state.get('payment_terms', [])
        if payment_terms:
            for term in payment_terms:
                if term.get('percent') and term.get('description'):
                    payment_terms_html += f"<li>{term.get('percent'):.0f}% {term.get('description')}</li>"

        # Build warranty HTML
        warranty_text = st.session_state.get('warranty_text', '')
        warranty_shipping_cost = st.session_state.get('warranty_shipping_cost', 100.0)
        warranty_html = warranty_text.format(shipping_cost=warranty_shipping_cost)

        # Get additional details
        power_provider = st.session_state.get('power_provider', 'ADDC – Abu Dhabi')
        project_title = st.session_state.get('project_title', '')
        project_description = st.session_state.get('project_description', '')

        # Generate HTML
        html_content = render_quotation_html({
            'company_name': load_settings().get('company_name', 'Newton Smart Home'),
            'quotation_number': invoice_no,
            'quotation_date': datetime.today().strftime('%Y-%m-%d'),
            'client_name': client_name,
            'mobile': client_phone or phone_raw,
            'client_address': client_location,
            'project_location': client_location,
            'items': norm_items,
            'subtotal': product_total,
            'Installation': installation_cost,
            'total_amount': grand_total,
            'down_payment': down_payment,
            'previously_paid': previously_paid,
            'project_title': project_title,
            'project_description': project_description,
            'balance_due': balance_due,
            'payment_terms_html': payment_terms_html,
            'warranty_html': warranty_html,
            'power_provider': power_provider,
            'delivery_text': st.session_state.get('inv_delivery_text', ''),
            'bank_name': load_settings().get('bank_name', ''),
            'bank_account': load_settings().get('bank_account', ''),
            'bank_iban': load_settings().get('bank_iban', ''),
            'sig_name': load_settings().get('default_prepared_by', ''),
            'sig_role': load_settings().get('default_approved_by', ''),
        }, template_name='newton_invoice_A4.html')

        html_filename = f"Invoice_{invoice_no}.html"

        # Single Download Button (HTML + Save Record)
        if st.download_button(
            label="📥 Download Invoice (HTML)",
            data=html_content,
            file_name=html_filename,
            mime='text/html',
            use_container_width=True
        ):
            # Determine base_id
            base_id = None
            if mode == "From Quotation":
                try:
                    q_row = records[records["number"] == st.session_state.get("q_select_inline")].iloc[0]
                    base_id = q_row.get("base_id", None)
                except Exception:
                    base_id = None
            if not base_id:
                today_id = datetime.today().strftime('%Y%m%d')
                same_day = records[records["base_id"].astype(str).str.contains(today_id, na=False)] if not records.empty else pd.DataFrame()
                seq = len(same_day) + 1
                base_id = f"{today_id}-{str(seq).zfill(3)}"

            # Prepare invoice data
            invoice_data = {
                "base_id": base_id,
                "date": datetime.today().strftime('%Y-%m-%d'),
                "type": "i",
                "number": invoice_no,
                "amount": grand_total,
                "client_name": client_name,
                "phone": phone_raw,
                "location": client_location,
                "note": st.session_state.get("q_select_inline") or "",
                "products": norm_items,
                "installation_cost": installation_cost,
                "discount_value": discount_value,
                "discount_percent": discount_percent,
                "down_payment": down_payment,
                "previously_paid": previously_paid,
                "balance_due": balance_due,
            }

            # Save to records
            save_record(invoice_data)

            # Update customer
            upsert_customer_from_invoice(client_name, phone_raw, client_location)

            # Save HTML file locally
            out_dir = Path('data') / 'exports'
            out_dir.mkdir(parents=True, exist_ok=True)
            html_path = out_dir / html_filename
            with open(html_path, 'w', encoding='utf-8') as fh:
                fh.write(html_content)

            st.success(f"✅ Invoice saved! ID: {base_id}")

    except Exception as e:
        st.error(f"❌ Error generating invoice: {e}")


def save_record(record: dict):
    """حفظ سجل في records.xlsx (DB-first if available)"""
    # Try DB first
    if _db is not None:
        try:
            # Keep one latest record per (type, number)
            try:
                if record.get("type") and record.get("number"):
                    _db.db_execute(
                        "DELETE FROM records WHERE type = %s AND number = %s",
                        (record.get("type"), record.get("number")),
                    )
            except Exception:
                pass
            _db.db_execute(
                'INSERT INTO records(base_id, date, type, number, amount, client_name, phone, location, note) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (record.get('base_id'), record.get('date'), record.get('type'), record.get('number'), 
                 record.get('amount'), record.get('client_name'), record.get('phone'), record.get('location'), record.get('note'))
            )
            # Also save to Excel for backup
        except Exception:
            pass
    
    # Excel fallback/backup
    os.makedirs("data", exist_ok=True)
    path = "data/records.xlsx"
    try:
        df = pd.read_excel(path)
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception:
        df = pd.DataFrame(columns=[
            "base_id", "date", "type", "number", "amount", "client_name", "phone", "location", "note"
        ])
    if df.empty:
        df = pd.DataFrame([record])
    else:
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    df.to_excel(path, index=False)
