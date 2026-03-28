import streamlit as st
import pandas as pd
from datetime import datetime
import os
from io import BytesIO
import base64
import tempfile
# Optional dependency: python-docx (used for Word export). Guard imports so missing packages don't crash the app.
HAVE_PYDOX = True
try:
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except Exception:
    HAVE_PYDOX = False

# Optional Streamlit components import (some Streamlit setups may not expose components in static analysis)
try:
    from streamlit.components.v1 import html as st_html
except Exception:
    st_html = None
from utils.quotation_utils import render_quotation_html, html_to_pdf
from pathlib import Path
import sys
import threading
import json
import subprocess
import time
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.logger import log_event
from utils.settings import load_settings
try:
    from utils import db as _db
except Exception:
    _db = None
from utils.image_utils import ensure_data_url
 # تم حذف الاستيراد غير المستخدم requests

def proper_case(text):
    if not text:
        return ""
    try:
        return text.title().strip()
    except:
        return text

# Apply the same visual theme used in dashboard_page.py
def _apply_quotation_theme():
    # Now inherits global Invoice theme from main.py
    st.markdown("<style></style>", unsafe_allow_html=True)

def quotation_app():
    _apply_quotation_theme()

    # Ensure session_state keys exist to avoid runtime KeyError when Streamlit first loads
    if 'product_table' not in st.session_state:
        st.session_state.product_table = pd.DataFrame(columns=[
            'Product / Device', 'Qty', 'Unit Price (AED)', 'Line Total (AED)', 'Warranty (Years)', 'Item No'
        ])

        # (Header hero removed to match invoice page)

    # =========================
    # Helper
    # =========================
    def format_phone_input(raw_input):
        digits = ''.join(filter(str.isdigit, raw_input))
        if digits.startswith("0"): digits = digits[1:]
        if digits.startswith("5") and len(digits) == 9:
            return f"+971 {digits[:2]} {digits[2:5]} {digits[5:]}"
        return None

    # =========================
    # UAE Locations
    # =========================
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
        "Fujairah - Al Faseel","Fujairah - Madhab","Fujairah - Dibba",
        "Fujairah - Sakamkam","Fujairah - Mirbah","Fujairah - Al Taween",
        "Fujairah - Kalba","Fujairah - Qidfa","Fujairah - Al Aqah",
        "UAQ - Al Salama","UAQ - Al Haditha","UAQ - Al Raas",
        "UAQ - Al Dar Al Baida","UAQ - Al Khor","UAQ - Al Ramlah",
        "UAQ - Al Maidan","UAQ - Emirates City",
    ]

    # =========================
    # Setup
    # =========================
    catalog = None
    if _db is not None:
        try:
            rows = _db.db_query(
                'SELECT device as "Device", description as "Description", unit_price as "UnitPrice", warranty as "Warranty", image_base64 as "ImageBase64", image_path as "ImagePath" FROM products ORDER BY id'
            )
            if rows:
                catalog = pd.DataFrame(rows)
        except Exception:
            catalog = None
    if catalog is None:
        try:
            catalog = pd.read_excel("data/products.xlsx")
        except Exception:
            st.error("❌ ERROR: Cannot load product catalog")
            return

    required_cols = ["Device", "Description", "UnitPrice", "Warranty"]
    for col in required_cols:
        if col not in catalog.columns:
            st.error(f"❌ Missing column: {col}")
            return

    # Records helpers (match invoice logic)
    def load_records():
        # Try DB first, fallback to Excel
        if _db is not None:
            try:
                rows = _db.db_query('SELECT base_id, date, type, number, amount, client_name, phone, location, note FROM records ORDER BY date')
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
                "base_id","date","type","number","amount","client_name","phone","location","note"
            ])

    def save_record(rec: dict):
        # Try saving to DB, fallback to Excel
        if _db is not None:
            try:
                # Delete existing by type+number then insert
                if rec.get('type') and rec.get('number'):
                    try:
                        _db.db_execute('DELETE FROM records WHERE type = %s AND number = %s', (rec.get('type'), rec.get('number')))
                    except Exception:
                        pass
                _db.db_execute(
                    'INSERT INTO records(base_id, date, type, number, amount, client_name, phone, location, note) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                    (rec.get('base_id'), rec.get('date'), rec.get('type'), rec.get('number'), rec.get('amount'), rec.get('client_name'), rec.get('phone'), rec.get('location'), rec.get('note'))
                )
                return
            except Exception:
                pass

        df = load_records()
        if not df.empty and {"type", "number"}.issubset(df.columns):
            df = df[~((df["type"] == rec.get("type")) & (df["number"] == rec.get("number")))]
        df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
        if {"type", "number"}.issubset(df.columns):
            df = df.drop_duplicates(subset=["type", "number"], keep="last")
        df.to_excel("data/records.xlsx", index=False)

    # Customers helpers (auto add from quotation)
    def ensure_customers_file():
        os.makedirs("data", exist_ok=True)
        path = "data/customers.xlsx"
        if not os.path.exists(path):
            cols = [
                "client_name","phone","location","email","status",
                "notes","tags","next_follow_up","assigned_to","last_activity"
            ]
            pd.DataFrame(columns=cols).to_excel(path, index=False)

    def load_customers():
        # Try DB first then fallback to Excel
        if _db is not None:
            try:
                rows = _db.db_query('SELECT id, name, phone, email, address FROM customers ORDER BY id')
                if rows:
                    df = pd.DataFrame(rows)
                    df = df.rename(columns={'name':'client_name', 'address':'location'})
                    df.columns = [c.strip().lower() for c in df.columns]
                    return df
            except Exception:
                pass
        ensure_customers_file()
        try:
            df = pd.read_excel("data/customers.xlsx")
            df.columns = [c.strip().lower() for c in df.columns]
            return df
        except:
            return pd.DataFrame(columns=[
                "client_name","phone","location","email","status",
                "notes","tags","next_follow_up","assigned_to","last_activity"
            ])

    def save_customers(df: pd.DataFrame):
        os.makedirs("data", exist_ok=True)
        # Try DB sync (upsert) then write Excel to preserve app-specific fields
        if _db is not None:
            try:
                for _, row in df.iterrows():
                    name = str(row.get('client_name') or '')
                    phone = row.get('phone')
                    email = row.get('email')
                    address = row.get('location')
                    try:
                        existing = _db.db_query('SELECT id FROM customers WHERE name = %s AND phone = %s', (name, phone))
                    except Exception:
                        existing = []
                    if existing:
                        try:
                            _db.db_execute('UPDATE customers SET email = %s, address = %s WHERE id = %s', (email, address, existing[0].get('id')))
                        except Exception:
                            pass
                    else:
                        try:
                            _db.db_execute('INSERT INTO customers(name, phone, email, address) VALUES (%s,%s,%s,%s)', (name, phone, email, address))
                        except Exception:
                            pass
                df.to_excel("data/customers.xlsx", index=False)
                return
            except Exception:
                pass
        df.to_excel("data/customers.xlsx", index=False)

    def upsert_customer_from_quotation(name: str, phone: str, location: str):
        if not str(name).strip():
            return
        # Try DB upsert matching DB schema, otherwise fall back to Excel logic
        if _db is not None:
            try:
                # Simple phone/name lookup
                existing = []
                try:
                    existing = _db.db_query('SELECT id FROM customers WHERE name = %s OR phone = %s', (proper_case(name), phone))
                except Exception:
                    existing = []
                if existing:
                    try:
                        _db.db_execute('UPDATE customers SET phone = %s, address = %s WHERE id = %s', (phone, proper_case(location), existing[0].get('id')))
                    except Exception:
                        pass
                else:
                    try:
                        _db.db_execute('INSERT INTO customers(name, phone, email, address) VALUES (%s,%s,%s,%s)', (proper_case(name), phone, '', proper_case(location)))
                    except Exception:
                        pass
                return
            except Exception:
                pass

        # Fallback: original Excel behaviour
        ensure_customers_file()
        cdf = load_customers()
        key = str(name).strip().lower()
        exists = None
        if not cdf.empty and "client_name" in cdf.columns:
            m = cdf["client_name"].astype(str).str.strip().str.lower() == key
            if m.any():
                exists = cdf[m].index[0]
            else:
                # Try phone-based matching when names differ
                cdf_phone = cdf.get("phone", pd.Series([], dtype=str)).apply(lambda x: x if pd.isna(x) else str(x))
                try_phone = phone
                def norm(x):
                    digits = ''.join(filter(str.isdigit, str(x)))
                    if digits.startswith('971') and len(digits) >= 12 and digits[3] == '5':
                        return '0' + digits[3:12]
                    if len(digits) == 9 and digits.startswith('5'):
                        return '0' + digits
                    if len(digits) == 10 and digits.startswith('05'):
                        return digits
                    return digits[-10:]
                if try_phone:
                    m2 = cdf_phone.apply(norm) == norm(try_phone)
                    if m2.any():
                        exists = cdf[m2].index[0]
        if exists is not None:
            cdf.at[exists, 'client_name'] = proper_case(name)
            cdf.at[exists, 'phone'] = phone
            cdf.at[exists, 'location'] = proper_case(location)
        else:
            new_row = {
                'client_name': proper_case(name),
                'phone': phone,
                'location': proper_case(location),
                'email': '',
                'status': 'Active',
                'notes': '',
                'tags': '',
                'next_follow_up': '',
                'assigned_to': '',
                'last_activity': datetime.today().strftime('%Y-%m-%d')
            }
            cdf = pd.concat([cdf, pd.DataFrame([new_row])], ignore_index=True)
        save_customers(cdf)

    # Quotation summary inputs (Client name, Quotation No, Location, Mobile, Prepared/Approved)
    if 'quo_client_name' not in st.session_state:
        st.session_state['quo_client_name'] = ''
    if 'quo_phone' not in st.session_state:
        st.session_state['quo_phone'] = ''
    if 'quo_loc' not in st.session_state:
        st.session_state['quo_loc'] = uae_locations[0] if uae_locations else ''
    if 'quo_no' not in st.session_state:
        # New numbering system: QYYYY#### (e.g., Q20260001)
        current_year = datetime.today().year
        records = load_records()
        year_quotations = records[(records['type']=='q') & (records['number'].astype(str).str.startswith(f'Q{current_year}'))]
        next_seq = len(year_quotations) + 1
        st.session_state['quo_no'] = f"Q{current_year}{str(next_seq).zfill(4)}"
    if 'quo_prepared_by' not in st.session_state:
        st.session_state['quo_prepared_by'] = 'Mr Bukhry'
    if 'quo_approved_by' not in st.session_state:
        st.session_state['quo_approved_by'] = 'Mr Mohammed'
    if 'quo_project_title' not in st.session_state:
        st.session_state['quo_project_title'] = ''
    if 'quo_project_description' not in st.session_state:
        st.session_state['quo_project_description'] = ''

    st.markdown('<div class="section-title">Quotation Summary</div>', unsafe_allow_html=True)
    ql, qr = st.columns([1,1])
    with ql:
        st.text_input("Client Name", value=st.session_state.get('quo_client_name', ''), key='quo_client_name', help='Client name used in exports')
        st.selectbox("Project Location (UAE)", uae_locations, index=uae_locations.index(st.session_state['quo_loc']) if st.session_state['quo_loc'] in uae_locations else 0, key='quo_loc')
        st.text_input("Mobile Number", value=st.session_state.get('quo_phone', ''), placeholder="050xxxxxxx", key='quo_phone')
    with qr:
        st.text_input("Quotation No", value=st.session_state.get('quo_no', ''), key='quo_no')
        st.text_input("Prepared By", value='Mr Bukhry', key='quo_prepared_by', disabled=True)
        st.text_input("Approved By", value='Mr Mohammed', key='quo_approved_by', disabled=True)
    
    # Project Details Section with AI Generation
    st.markdown('<div class="section-title">Project Details</div>', unsafe_allow_html=True)
    proj_col1, proj_col2 = st.columns([3, 1])
    with proj_col1:
        st.text_input(
            "Project Title",
            value=st.session_state.get('quo_project_title', ''),
            key='quo_project_title',
            placeholder="e.g., Smart Home Installation - Villa 123",
            help="Enter project title or click Generate to auto-create"
        )
        st.text_area(
            "Project Description",
            value=st.session_state.get('quo_project_description', ''),
            key='quo_project_description',
            placeholder="e.g., Complete smart home system including lighting control, security cameras, and automation",
            help="Enter project description or click Generate to auto-create",
            height=100
        )
    with proj_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🤖 Generate with AI", key="generate_project_details", use_container_width=True, type="primary"):
            if st.session_state.product_table.empty:
                st.warning("⚠️ Please add products first to generate project details")
            else:
                with st.spinner("🔄 Generating project details..."):
                    try:
                        from utils.openai_utils import chat_with_ai
                        
                        # Build product list
                        products_list = []
                        for _, row in st.session_state.product_table.iterrows():
                            products_list.append(f"- {row['Product / Device']} (Qty: {int(row['Qty'])})")
                        products_str = "\n".join(products_list)
                        
                        # Generate title
                        title_prompt = f"""Generate a short professional project title (max 8 words) for a smart home quotation with these products:
{products_str}

Client: {st.session_state.get('quo_client_name', 'Client')}
Location: {st.session_state.get('quo_loc', 'UAE')}

Return ONLY the title, nothing else."""
                        
                        title_response = chat_with_ai(title_prompt, [])
                        st.session_state['quo_project_title'] = title_response.strip()
                        
                        # Generate description
                        desc_prompt = f"""Generate a concise professional project description (2-3 sentences, max 150 words) for a smart home quotation with these products:
{products_str}

Client: {st.session_state.get('quo_client_name', 'Client')}
Location: {st.session_state.get('quo_loc', 'UAE')}

Return ONLY the description, nothing else. Focus on benefits and scope."""
                        
                        desc_response = chat_with_ai(desc_prompt, [])
                        st.session_state['quo_project_description'] = desc_response.strip()
                        
                        st.success("✅ Project details generated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error generating details: {str(e)}")

    st.session_state.num_entries = 1

    df = st.session_state.product_table.copy()

    if not df.empty:
        for idx, (i, row) in enumerate(df.iterrows()):
            cols = st.columns([4.5,0.7,1,1,0.7,0.7])

            with cols[0]:
                st.markdown(f"""
                    <div class='added-product-row'>
                        <span style="font-weight:bold;color:var(--accent);">✓</span>
                        <span style="font-weight:600;color:#1f2937;">{row['Product / Device']}</span>
                    </div>
                """, unsafe_allow_html=True)

            with cols[1]:
                st.markdown(f"<div class='added-product-row'><span class='product-value'>{int(row['Qty'])}</span></div>", unsafe_allow_html=True)

            with cols[2]:
                st.markdown(f"<div class='added-product-row'><span class='product-value'>{row['Unit Price (AED)']:.2f}</span></div>", unsafe_allow_html=True)

            with cols[3]:
                st.markdown(
                    f"<div class='added-product-row'><span class='product-value'>AED {row['Line Total (AED)']:.2f}</span></div>",
                    unsafe_allow_html=True
                )

            with cols[4]:
                st.markdown(f"<div class='added-product-row'><span class='product-value'>{int(row['Warranty (Years)'])} yr</span></div>", unsafe_allow_html=True)

            with cols[5]:
                if st.button("❌", key=f"del_q_{i}"):
                    st.session_state.product_table = st.session_state.product_table.drop(i).reset_index(drop=True)
                    st.session_state.product_table["Item No"] = range(1, len(st.session_state.product_table)+1)
                    st.rerun()

    for entry_idx in range(st.session_state.num_entries):
        cols = st.columns([4.5,0.7,1,1,0.7,0.7])

        with cols[0]:
            product = st.selectbox(
                "Product",
                catalog["Device"],
                key=f"prod_entry_{entry_idx}",
                label_visibility="collapsed"
            )
            row = catalog[catalog["Device"] == product].iloc[0]
            desc = row["Description"]

        key_qty = f"qty_val_{entry_idx}"
        key_price = f"price_val_{entry_idx}"
        key_war = f"war_val_{entry_idx}"
        if key_qty not in st.session_state:
            st.session_state[key_qty] = 1
        if key_price not in st.session_state:
            st.session_state[key_price] = float(row["UnitPrice"])
        if key_war not in st.session_state:
            st.session_state[key_war] = int(row["Warranty"])
        # Sync price and warranty when product changes
        last_key = f"last_prod_{entry_idx}"
        if st.session_state.get(last_key) != product:
            st.session_state[f"price_val_{entry_idx}"] = float(row["UnitPrice"])
            st.session_state[f"war_val_{entry_idx}"] = int(row["Warranty"])
            st.session_state[last_key] = product

        with cols[1]:
            st.number_input(
                "Qty",
                min_value=1,
                step=1,
                key=key_qty,
                label_visibility="collapsed"
            )

        with cols[2]:
            st.number_input(
                "Unit Price (AED)",
                min_value=0.0,
                step=10.0,
                key=key_price,
                label_visibility="collapsed"
            )

        qty = st.session_state[f"qty_val_{entry_idx}"]
        price = st.session_state[f"price_val_{entry_idx}"]
        line_price = qty * price

        with cols[3]:
            st.markdown(
                f"<div class='added-product-row'><span class='product-value'>AED {line_price:.2f}</span></div>",
                unsafe_allow_html=True
            )

        with cols[4]:
            st.number_input(
                "Warranty (Years)",
                min_value=0,
                step=1,
                key=key_war,
                label_visibility="collapsed"
            )

        warranty = st.session_state[f"war_val_{entry_idx}"]

        with cols[5]:
            if st.button("✅", key=f"add_row_{entry_idx}"):
                # attach image only from Base64 field (no filesystem/URL fallbacks)
                image_val = None
                try:
                    raw_b64 = row.get('ImageBase64') if 'ImageBase64' in row.index else None
                    image_val = ensure_data_url(raw_b64) if raw_b64 is not None else None
                except Exception:
                    image_val = None

                new_row = {
                    "Item No": len(st.session_state.product_table) + 1,
                    "Product / Device": product,
                    "Description": desc,
                    "Qty": qty,
                    "Unit Price (AED)": price,
                    "Line Total (AED)": line_price,
                    "Warranty (Years)": warranty,
                    # keep both raw columns for Word export and a normalized `image` for HTML rendering
                    "ImagePath": row.get('ImagePath') if 'ImagePath' in row.index else None,
                    "ImageBase64": row.get('ImageBase64') if 'ImageBase64' in row.index else None,
                    "image": image_val,
                }
                new_df = pd.DataFrame([new_row])
                if st.session_state.product_table.empty:
                    st.session_state.product_table = new_df
                else:
                    st.session_state.product_table = pd.concat(
                        [st.session_state.product_table, new_df],
                        ignore_index=True
                    )
                st.rerun()

    st.markdown("---")

    product_total = st.session_state.product_table["Line Total (AED)"].sum() if not st.session_state.product_table.empty else 0

    # =========================
    # SUMMARY (match invoice)
    # =========================
    st.markdown("---")
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("<div class='section-title'>Project Costs</div>", unsafe_allow_html=True)

        # Pull persisted values (so left card reflects right inputs)
        installation_cost_val = st.session_state.get("install_cost_quo_value", 0.0)
        discount_value_val = st.session_state.get("disc_value_quo_value", 0.0)
        discount_percent_val = st.session_state.get("disc_percent_quo_value", 0.0)

        percent_value = (product_total + installation_cost_val) * (discount_percent_val / 100)
        total_discount = percent_value + discount_value_val
        grand_total = (product_total + installation_cost_val) - total_discount

        st.markdown(
            """
            <div style='background:#fff;border:1px solid rgba(0,0,0,.08);border-radius:12px;padding:16px;box-shadow:0 2px 6px rgba(0,0,0,.04);'>
                <div style='display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(0,0,0,.06);'>
                    <span style='font-weight:600;color:#6e6e73;'>Price (AED)</span>
                    <span style='font-weight:700;color:#1d1d1f;'>{:,.2f} AED</span>
                </div>
                <div style='display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(0,0,0,.06);'>
                    <span style='font-weight:600;color:#6e6e73;'>Installation & Operation Devices</span>
                    <span style='font-weight:700;color:#1d1d1f;'>{:,.2f} AED</span>
                </div>
                <div style='display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(0,0,0,.06);'>
                    <span style='font-weight:600;color:#6e6e73;'>Discount</span>
                    <span style='font-weight:700;color:#1d1d1f;'>-{:,.2f} AED</span>
                </div>
                <div style='display:flex;justify-content:space-between;padding:15px 0;background:rgba(0,0,0,.02);margin-top:8px;border-radius:8px;padding-left:12px;padding-right:12px;'>
                    <span style='font-weight:700;font-size:16px;color:#1d1d1f;'>TOTAL AMOUNT</span>
                    <span style='font-weight:700;font-size:18px;color:#1d1d1f;'>{:,.2f} AED</span>
                </div>
            </div>
            """.format(product_total, installation_cost_val, total_discount, grand_total),
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown("<div class='section-title'>Installation & Discount</div>", unsafe_allow_html=True)

        installation_cost = st.number_input(
            "Installation & Operation Devices (AED)",
            min_value=0.0,
            step=50.0,
            key="install_cost_quo",
        )
        st.session_state["install_cost_quo_value"] = installation_cost

        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
        cD1, cD2 = st.columns(2)
        with cD1:
            discount_value = st.number_input("Discount Value (AED)", min_value=0.0, key="disc_value_quo")
            st.session_state["disc_value_quo_value"] = discount_value
        with cD2:
            discount_percent = st.number_input("Discount %", min_value=0.0, max_value=100.0, key="disc_percent_quo")
            st.session_state["disc_percent_quo_value"] = discount_percent

    # =========================
    # EXPORT - HTML Direct (Simplified)
    # =========================
    def _save_export_locally(data_bytes: bytes, filename: str) -> str:
        out_dir = Path('data') / 'exports'
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
        with open(out_path, 'wb') as f:
            f.write(data_bytes)
        return str(out_path)

    def generate_quotation_html() -> str:
        """Generate quotation HTML content"""
        products = st.session_state.product_table.to_dict('records') if 'product_table' in st.session_state else []
        _s = load_settings()
        
        # Recalculate totals
        product_total = st.session_state.product_table["Line Total (AED)"].sum() if not st.session_state.product_table.empty else 0.0
        installation_cost_val = float(st.session_state.get('install_cost_quo_value', 0.0) or 0.0)
        discount_value_val = float(st.session_state.get("disc_value_quo_value", 0.0) or 0.0)
        discount_percent_val = float(st.session_state.get("disc_percent_quo_value", 0.0) or 0.0)
        percent_value = (product_total + installation_cost_val) * (discount_percent_val / 100)
        total_discount = percent_value + discount_value_val
        grand_total = (product_total + installation_cost_val) - total_discount
        
        html_content = render_quotation_html({
            'company_name': _s.get('company_name', 'Newton Smart Home'),
            'quotation_number': st.session_state.get('quo_no', f"Q{datetime.today().year}0001"),
            'quotation_date': datetime.today().strftime('%Y-%m-%d'),
            'valid_until': '',
            'status': 'Pending Approval',
            'client_name': st.session_state.get('quo_client_name', ''),
            'mobile': st.session_state.get('quo_phone', ''),
            'client_company': '',
            'client_address': st.session_state.get('quo_loc', ''),
            'client_city': '',
            'client_trn': '',
            'project_title': st.session_state.get('quo_project_title', ''),
            'project_location': st.session_state.get('quo_loc', ''),
            'project_scope': st.session_state.get('quo_project_description', ''),
            'project_notes': '',
            'items': products,
            'subtotal': product_total,
            'Installation': installation_cost_val,
            'vat_amount': 0,
            'total_amount': grand_total,
            'bank_name': _s.get('bank_name', ''),
            'bank_account': _s.get('bank_account', ''),
            'bank_iban': _s.get('bank_iban', ''),
            'bank_company': _s.get('company_name', 'Newton Smart Home'),
            'sig_name': st.session_state.get('quo_prepared_by', 'Mr Bukhry'),
            'sig_role': st.session_state.get('quo_approved_by', 'Mr Mohammed'),
        }, template_name="newton_quotation_A4.html")
        return html_content

    st.markdown("---")
    st.markdown('<div class="section-title">Export Quotation</div>', unsafe_allow_html=True)

    # Recalculate totals for display
    product_total = st.session_state.product_table["Line Total (AED)"].sum() if not st.session_state.product_table.empty else 0.0
    installation_cost_val = st.session_state.get("install_cost_quo_value", 0.0)
    discount_value_val = st.session_state.get("disc_value_quo_value", 0.0)
    discount_percent_val = st.session_state.get("disc_percent_quo_value", 0.0)
    percent_value = (product_total + installation_cost_val) * (discount_percent_val / 100)
    total_discount = percent_value + discount_value_val
    grand_total = (product_total + installation_cost_val) - total_discount

    # Client data
    client_name = st.session_state.get('quo_client_name', '')
    client_location = st.session_state.get('quo_loc', '')
    quote_no = st.session_state.get('quo_no', f"Q{datetime.today().year}0001")
    phone_raw = st.session_state.get('quo_phone', '')

    # Generate HTML for download button
    try:
        html_content = generate_quotation_html()
        safe_name = client_name.replace(' ', '_') if client_name else 'Client'
        html_filename = f"Quotation_{safe_name}_{quote_no}.html"
        
        # Single download button that also saves the record
        clicked = st.download_button(
            label="💾 Save & Download Quotation",
            data=html_content,
            file_name=html_filename,
            mime="text/html",
            type="primary",
            use_container_width=True,
            key=f"save_dl_{quote_no}"
        )
        
        if clicked:
            # Save record
            today_id = datetime.today().strftime('%Y%m%d')
            existing = load_records()
            if not existing.empty and "base_id" in existing.columns:
                same_day = existing[existing.get("base_id", "").astype(str).str.contains(today_id, na=False)]
                seq = len(same_day) + 1
            else:
                seq = 1
            base_id = f"{today_id}-{str(seq).zfill(3)}"
            
            quotation_data = {
                "base_id": base_id,
                "date": datetime.today().strftime('%Y-%m-%d'),
                "type": "q",
                "number": quote_no,
                "amount": grand_total,
                "client_name": client_name,
                "phone": phone_raw,
                "location": client_location,
                "note": ""
            }
            save_record(quotation_data)
            
            upsert_customer_from_quotation(client_name, phone_raw, client_location)
            
            # Save HTML file locally
            out_dir = Path('data') / 'exports'
            out_dir.mkdir(parents=True, exist_ok=True)
            html_path = out_dir / html_filename
            with open(html_path, 'w', encoding='utf-8') as fh:
                fh.write(html_content)
            
            # Log event
            user = st.session_state.get("user", {})
            log_event(user.get("name", "Unknown"), "Quotation", "quotation_created", 
                     f"Client: {client_name}, Amount: {grand_total}")
            
            st.success(f"✅ Quotation saved! ID: {base_id}")
            
    except Exception as e:
        st.error(f"❌ Error: {e}")


