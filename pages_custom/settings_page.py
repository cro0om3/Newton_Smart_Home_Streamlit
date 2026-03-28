"""
Settings Page - Complete Implementation with 5 Sections:
1. User Management
2. System Configuration  
3. Template Manager
4. Backup & Restore
5. Log Viewer
"""

import streamlit as st
import pandas as pd
import os
import json
import zipfile
from io import BytesIO
from datetime import datetime

# Import utilities
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.auth import load_users, save_users, is_admin
from utils.logger import log_event, load_logs
from utils.settings import load_settings, save_settings
try:
    from utils import db as _db
except Exception:
    _db = None


def _apply_settings_theme():
    """Apply Enterprise CRM-style theme for settings page."""
    st.markdown("""
    <style>
        /* ========================================
           ENTERPRISE CRM DESIGN SYSTEM
           Apple + HubSpot + Salesforce inspired
        ======================================== */
        
        /* Page background */
        .main .block-container {
            background: var(--bg-main);
            padding-top: 56px !important;
            padding-bottom: 60px !important;
            max-width: 1400px;
        }
        
        /* Header height control */
        header[data-testid="stHeader"] {
            height: 90px !important;
        }
        
        /* Page title */
        .settings-page-title {
            font-size: 32px;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 8px;
            margin-top: 12px;
            letter-spacing: -0.5px;
        }
        
        .settings-subtitle {
            font-size: 15px;
            color: var(--text-muted);
            margin-bottom: 40px;
        }
        
        /* CRM Card wrapper - refined */
        .crm-card {
            background: var(--bg-panel);
            border: 1px solid var(--border-soft);
            border-radius: 16px;
            padding: 22px;
            margin-top: 36px;
            margin-bottom: 12px;
            box-shadow: 0 2px 14px rgba(0,0,0,0.03);
        }
        
        /* Section headers inside cards */
        .crm-section-title {
            font-size: 22px;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 20px;
            letter-spacing: -0.3px;
            padding-bottom: 14px;
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }
        
        .crm-subsection {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-main);
            margin-top: 24px;
            margin-bottom: 14px;
        }
        
        /* Tabs redesign - enterprise CRM style */
        .stTabs [data-baseweb="tab-list"] {
            background: transparent;
            border-bottom: 1px solid rgba(0,0,0,0.08);
            gap: 12px;
            padding: 0;
            margin-bottom: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 15px;
            font-weight: 500;
            padding: 14px 28px;
            border-bottom: 2px solid transparent;
            transition: all 0.2s ease;
            margin: 0 4px;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            color: var(--text-main);
            background: rgba(0,0,0,0.02);
        }
        
        .stTabs [aria-selected="true"] {
            color: var(--accent-blue) !important;
            border-bottom: 2px solid var(--accent-blue) !important;
            background: transparent !important;
        }
        
        /* Tab content wrapper */
        .stTabs [data-baseweb="tab-panel"] {
            padding: 20px 0 0 0;
        }
        
        /* Buttons - Primary */
        .stButton > button[kind="primary"],
        .stButton > button[type="primary"],
        .stForm button[kind="primary"] {
            background: var(--accent-blue);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 11px 26px;
            font-weight: 500;
            font-size: 15px;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(10,132,255,0.2);
        }
        
        .stButton > button[kind="primary"]:hover,
        .stForm button[kind="primary"]:hover {
            background: var(--accent-cyan);
            box-shadow: 0 4px 12px rgba(56,189,248,0.18);
            transform: translateY(-1px);
        }
        
        /* Buttons - Secondary */
        .stButton > button[kind="secondary"],
        .stButton > button[type="secondary"] {
            background: var(--bg-panel);
            color: var(--text-main);
            border: 1px solid var(--border-soft);
            border-radius: 10px;
            padding: 11px 26px;
            font-weight: 500;
            font-size: 15px;
            transition: all 0.2s ease;
        }
        
        .stButton > button[kind="secondary"]:hover {
            background: #F7F7F8;
            border-color: rgba(0,0,0,0.12);
            transform: translateY(-1px);
        }
        
        /* Regular buttons */
        .stButton > button {
            background: var(--bg-panel);
            color: var(--text-main);
            border: 1px solid var(--border-soft);
            border-radius: 10px;
            padding: 11px 26px;
            font-weight: 500;
            font-size: 15px;
            transition: all 0.2s ease;
        }
        
        .stButton > button:hover {
            background: #F7F7F8;
            border-color: rgba(0,0,0,0.12);
            transform: translateY(-1px);
        }
        
        /* Form input wrapper - mini cards */
        .input-card {
            background: white;
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 12px;
        }
        
        /* Form labels */
        .stTextInput label, .stSelectbox label, .stMultiSelect label,
        .stFileUploader label, .stNumberInput label {
            font-size: 14px;
            font-weight: 500;
            color: #1D1D1F;
            margin-bottom: 8px;
        }
        
        /* Input fields - refined */
        .stTextInput > div > div > input,
        .stSelectbox > div > div > div,
        .stMultiSelect > div > div > div,
        .stNumberInput > div > div > input {
            border: 1px solid rgba(0,0,0,0.12) !important;
            border-radius: 10px !important;
            background: white !important;
            color: #1D1D1F !important;
            font-size: 15px;
            padding: 10px 14px !important;
            transition: all 0.2s ease;
        }
        
        .stTextInput > div > div > input:focus,
        .stSelectbox > div > div > div:focus-within,
        .stMultiSelect > div > div > div:focus-within,
        .stNumberInput > div > div > input:focus {
            border-color: var(--accent-blue) !important;
            box-shadow: 0 0 0 3px rgba(56,189,248,0.1) !important;
        }
        
        /* Expanders replaced with CRM cards */
        .streamlit-expanderHeader {
            background: white;
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 14px;
            padding: 18px 22px;
            font-size: 16px;
            font-weight: 600;
            color: #1D1D1F;
            transition: all 0.2s ease;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        }
        
        .streamlit-expanderHeader:hover {
            background: #FAFAFA;
            border-color: rgba(0,0,0,0.12);
            box-shadow: 0 4px 14px rgba(0,0,0,0.05);
        }
        
        .streamlit-expanderContent {
            background: white;
            border: 1px solid rgba(0,0,0,0.06);
            border-top: none;
            border-radius: 0 0 14px 14px;
            padding: 22px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        }
        
        /* DataFrames - enterprise look */
        .stDataFrame {
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 1px 8px rgba(0,0,0,0.02);
        }
        
        .stDataFrame > div {
            border-radius: 12px;
        }
        
        /* DataFrame headers */
        .stDataFrame thead tr {
            background: var(--bg-panel) !important;
        }
        
        .stDataFrame thead th {
            font-weight: 600 !important;
            color: var(--text-main) !important;
            border-bottom: 1px solid rgba(0,0,0,0.08) !important;
            padding: 12px 16px !important;
        }
        
        /* DataFrame rows */
        .stDataFrame tbody tr {
            border-bottom: 1px solid rgba(0,0,0,0.04);
            transition: background 0.15s ease;
        }
        
        .stDataFrame tbody tr:nth-child(even) {
            background: var(--bg-panel);
        }
        
        .stDataFrame tbody tr:hover {
            background: rgba(56,189,248,0.02) !important;
        }
        
        .stDataFrame tbody td {
            padding: 12px 16px !important;
            color: var(--text-main);
        }
        
        /* File uploader - refined */
        .stFileUploader {
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 14px;
            padding: 24px;
            background: var(--bg-panel);
            transition: all 0.2s ease;
            text-align: center;
        }
        
        .stFileUploader:hover {
            border-color: var(--accent-blue);
            background: linear-gradient(135deg, rgba(56,189,248,0.02), rgba(34,211,238,0.01));
            box-shadow: 0 2px 12px rgba(56,189,248,0.04);
        }
        
        .stFileUploader label {
            text-align: center;
            display: block;
        }
        
        /* Alerts - refined neutral style */
        .stAlert {
            border-radius: 12px;
            border: 1px solid rgba(0,0,0,0.06);
            padding: 16px 20px;
            font-size: 14px;
        }
        
        /* Warning - improved */
        div[data-baseweb="notification"] [data-testid="stNotificationContentWarning"],
        .stAlert[data-baseweb="notification"] {
            background: rgba(250,204,21,0.06) !important;
            border: 1px solid rgba(250,204,21,0.14) !important;
            color: #7A5B00 !important;
        }
        
        /* Success */
        div[data-baseweb="notification"] [data-testid="stNotificationContentSuccess"] {
            background: rgba(34,211,238,0.03);
            border-left: 3px solid var(--accent-cyan);
            color: var(--text-main);
        }
        
        /* Error */
        div[data-baseweb="notification"] [data-testid="stNotificationContentError"] {
            background: rgba(249,115,115,0.03);
            border-left: 3px solid var(--accent-gold);
            color: var(--text-main);
        }
        
        /* Info */
        div[data-baseweb="notification"] [data-testid="stNotificationContentInfo"] {
            background: rgba(56,189,248,0.02);
            border-left: 3px solid var(--accent-blue);
            color: var(--text-main);
        }
        
        /* Dividers */
        hr {
            border: none;
            border-bottom: 1px solid rgba(255,255,255,0.03);
            margin: 28px 0;
        }
        
        /* Download buttons */
        .stDownloadButton > button {
            background: var(--accent-blue);
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: 500;
            padding: 11px 26px;
            box-shadow: 0 2px 8px rgba(10,132,255,0.2);
            transition: all 0.2s ease;
        }
        
        .stDownloadButton > button:hover {
            background: var(--accent-cyan);
            box-shadow: 0 4px 12px rgba(56,189,248,0.18);
            transform: translateY(-1px);
        }
        
        /* Metrics for log viewer - neutral gray */
        .log-metric {
            background: var(--bg-panel);
            border: 1px solid var(--border-soft);
            border-radius: 16px;
            padding: 20px 24px;
            text-align: center;
            box-shadow: 0 2px 14px rgba(0,0,0,0.03);
            transition: all 0.2s ease;
        }
        
        .log-metric:hover {
            box-shadow: 0 4px 18px rgba(0,0,0,0.05);
            transform: translateY(-2px);
        }
        
        .log-metric-value {
            font-size: 26px;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 6px;
        }
        
        .log-metric-label {
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Spacing utilities */
        .spacing-sm { margin-bottom: 14px; }
        .spacing-md { margin-bottom: 24px; }
        .spacing-lg { margin-bottom: 36px; }
        
        /* Section dividers */
        .section-divider {
            border-bottom: 1px solid rgba(0,0,0,0.05);
            margin: 32px 0;
        }
        
        /* Remove empty white space */
        .element-container:empty {
            display: none;
        }
        
        /* Improved form spacing */
        .stForm {
            background: white;
            padding: 0;
        }
        
        /* Navigation cards (if any) */
        .nav-card {
            background: white;
            border: 1px solid rgba(0,0,0,0.05);
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
            transition: all 0.2s ease;
        }
        
        .nav-card:hover {
            box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            transform: translateY(-2px);
        }
    </style>
    """, unsafe_allow_html=True)


def settings_app():
    """Main settings page with 5 sections."""
    
    # Apply theme
    _apply_settings_theme()
    
    user = st.session_state.get("user", {})
    user_name = user.get("name", "Unknown")
    user_role = user.get("role", "unknown").title()
    
    # Page header
    st.markdown(f"""
    <div class="settings-page-title">Settings</div>
    <div class="settings-subtitle">Manage system configuration and user access • Logged in as {user_name} ({user_role})</div>
    """, unsafe_allow_html=True)
    
    # Check if user is admin
    if not is_admin(user):
        st.warning("⚠️ Most settings require administrator privileges.")
    
    # Create tabs for sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Users",
        "Configuration",
        "Templates",
        "Backup & Restore",
        "Activity Logs"
    ])

    # Accent selector (non-blocking) - keep themes unchanged but allow overlay accents
    with st.expander("Theme Accent (optional)"):
        current = st.session_state.get('ui_accent', 'none')
        sel = st.selectbox("Accent Overlay", ["none", "winter"], index=["none","winter"].index(current))
        if sel != current:
            st.session_state['ui_accent'] = sel
            try:
                from utils.settings import update_setting
                update_setting('ui_accent', sel)
            except Exception:
                pass
            st.success(f"Accent set to: {sel}")
    
    with tab1:
        user_management_section(user, user_name)
    
    with tab2:
        system_config_section(user, user_name)
    
    with tab3:
        template_manager_section(user, user_name)
    
    with tab4:
        backup_restore_section(user, user_name)
    
    with tab5:
        log_viewer_section(user, user_name)


# ========================================================
# SECTION 1: USER MANAGEMENT
# ========================================================
def user_management_section(user, user_name):
    """Manage users, roles, permissions."""
    
    if not is_admin(user):
        st.error("Administrator privileges required to manage users.")
        return
    
    # Display existing users
    st.markdown('<div class="crm-section-title">Current Users</div>', unsafe_allow_html=True)
    
    users_df = load_users()
    
    if not users_df.empty:
        display_df = users_df.copy()
        display_df["pin"] = "••••"
        display_df.columns = ["Name", "PIN", "Role", "Allowed Pages"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No users found in system.")
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # Add user section
    with st.expander("➕ Add New User"):
        with st.form("add_user"):
            st.markdown('<div class="crm-subsection">Create User Account</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Full Name", placeholder="John Doe")
                new_pin = st.text_input("PIN Code (4-6 digits)", max_chars=6, type="password", placeholder="1234")
            with col2:
                new_role = st.selectbox("User Role", ["admin", "staff", "viewer"])
                new_pages = st.multiselect("Access Permissions", 
                    ["dashboard", "quotation", "invoice", "receipt", "customers", "products", "reports", "settings"],
                    default=["dashboard"],
                    help="Select which pages this user can access")
            
            st.markdown('<div class="spacing-sm"></div>', unsafe_allow_html=True)
            
            if st.form_submit_button("Create User", type="primary"):
                if not new_name or not new_pin or len(new_pin) < 4:
                    st.error("Please provide valid name and PIN (4-6 digits).")
                elif new_pin in users_df["pin"].astype(str).values:
                    st.error("This PIN is already in use. Choose a different one.")
                else:
                    new_user = pd.DataFrame([{
                        "name": new_name,
                        "pin": new_pin,
                        "role": new_role,
                        "allowed_pages": ",".join(new_pages)
                    }])
                    users_df = pd.concat([users_df, new_user], ignore_index=True)
                    save_users(users_df)
                    log_event(user_name, "Settings", "user_created", f"User: {new_name}, Role: {new_role}")
                    st.success(f"✓ User '{new_name}' created successfully")
                    st.rerun()
    
    st.markdown('<div class="spacing-md"></div>', unsafe_allow_html=True)
    
    # Edit user section
    with st.expander("✏️ Edit Existing User"):
        if not users_df.empty:
            edit_name = st.selectbox("Select User to Edit", users_df["name"].tolist())
            row = users_df[users_df["name"] == edit_name].iloc[0]
            
            with st.form("edit_user"):
                st.markdown('<div class="crm-subsection">Update User Details</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    e_name = st.text_input("Full Name", value=row["name"])
                    e_pin = st.text_input("New PIN (leave blank to keep current)", type="password", placeholder="Leave empty to keep")
                with col2:
                    e_role = st.selectbox("User Role", ["admin","staff","viewer"], 
                        index=["admin","staff","viewer"].index(row["role"]))
                    curr_pages = [p.strip() for p in str(row["allowed_pages"]).split(",") if p.strip()]
                    e_pages = st.multiselect("Access Permissions", 
                        ["dashboard","quotation","invoice","receipt","customers","products","reports","settings"],
                        default=curr_pages)
                
                st.markdown('<div class="spacing-sm"></div>', unsafe_allow_html=True)
                
                if st.form_submit_button("Update User", type="primary"):
                    idx = users_df[users_df["name"] == edit_name].index[0]
                    users_df.at[idx, "name"] = e_name
                    if e_pin and len(e_pin) >= 4:
                        users_df.at[idx, "pin"] = e_pin
                    users_df.at[idx, "role"] = e_role
                    users_df.at[idx, "allowed_pages"] = ",".join(e_pages)
                    save_users(users_df)
                    log_event(user_name, "Settings", "user_updated", f"User: {e_name}, Role: {e_role}")
                    st.success(f"✓ User '{e_name}' updated successfully")
                    st.rerun()
        else:
            st.info("No users available to edit.")
    
    st.markdown('<div class="spacing-md"></div>', unsafe_allow_html=True)
    
    # Delete user section
    with st.expander("Remove User"):
        if not users_df.empty:
            st.warning("⚠️ This action cannot be undone. The user will lose all access immediately.")
            st.markdown('<div class="spacing-sm"></div>', unsafe_allow_html=True)
            del_name = st.selectbox("Select User to Remove", users_df["name"].tolist(), key="del")
            st.markdown('<div class="spacing-sm"></div>', unsafe_allow_html=True)
            
            if st.button("Delete User", type="secondary"):
                users_df = users_df[users_df["name"] != del_name]
                save_users(users_df)
                log_event(user_name, "Settings", "user_deleted", f"User: {del_name}")
                st.success(f"✓ User '{del_name}' removed successfully")
                st.rerun()
        else:
            st.info("No users available to delete.")


# ========================================================
# SECTION 2: SYSTEM CONFIGURATION
# ========================================================
def system_config_section(user, user_name):
    """Company info and defaults."""
    
    if not is_admin(user):
        st.error("Administrator privileges required to modify system configuration.")
        return
    
    st.markdown('<div class="crm-section-title">Company Information</div>', unsafe_allow_html=True)
    
    settings = load_settings()
    
    with st.form("config"):
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("Company Name", value=settings.get("company_name", ""), placeholder="Newton Smart Home")
            email = st.text_input("Contact Email", value=settings.get("contact_email", ""), placeholder="info@company.com")
            currency = st.text_input("Currency", value=settings.get("currency", "AED"), placeholder="AED")
        with col2:
            phone = st.text_input("Contact Phone", value=settings.get("contact_phone", ""), placeholder="+971 50 123 4567")
            prepared_by = st.text_input("Default Prepared By", value=settings.get("default_prepared_by", ""), placeholder="Sales Manager")
            approved_by = st.text_input("Default Approved By", value=settings.get("default_approved_by", ""), placeholder="Finance Manager")
        
        st.markdown('<div class="spacing-md"></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="crm-subsection">AI Integration (Optional)</div>', unsafe_allow_html=True)
        openai_key = st.text_input(
            "OpenAI API Key",
            value=settings.get("openai_api_key", ""),
            type="password",
            placeholder="sk-...",
            help="Enter your OpenAI API key for auto-generating project descriptions. Leave empty to disable."
        )
        st.caption("🔐 Your API key is stored securely. Used only for project description generation.")
        
        st.markdown('<div class="spacing-md"></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="crm-subsection">Product Image Sizes</div>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            ui_w = st.number_input("UI Image Width (px)", min_value=40, max_value=800, value=int(settings.get("ui_product_image_width_px", 133)))
            ui_h = st.number_input("UI Image Height (px)", min_value=30, max_value=800, value=int(settings.get("ui_product_image_height_px", 57)))
            st.caption("Used in Products page thumbnails")
        with g2:
            q_w = st.number_input("Quotation Image Width (cm)", min_value=0.5, max_value=20.0, value=float(settings.get("quote_product_image_width_cm", 3.49)))
            q_h = st.number_input("Quotation Image Height (cm)", min_value=0.5, max_value=20.0, value=float(settings.get("quote_product_image_height_cm", 1.5)))
            st.caption("Used in Word quotation table")
        
        st.markdown('<div class="spacing-md"></div>', unsafe_allow_html=True)
        
        save_clicked = st.form_submit_button("Save Configuration", type="primary")

    if save_clicked:
        settings.update({
            "company_name": company_name,
            "default_prepared_by": prepared_by,
            "default_approved_by": approved_by,
            "contact_email": email,
            "contact_phone": phone,
            "currency": currency,
            "openai_api_key": openai_key,
            "ui_product_image_width_px": int(ui_w),
            "ui_product_image_height_px": int(ui_h),
            "quote_product_image_width_cm": float(q_w),
            "quote_product_image_height_cm": float(q_h)
        })
        save_settings(settings)
        log_event(user_name, "Settings", "config_updated", "System configuration saved")
        st.success("✓ Configuration saved successfully")
        st.rerun()

    st.markdown('<div class="spacing-lg"></div>', unsafe_allow_html=True)
    st.markdown('<div class="crm-subsection">\u0623\u062f\u0648\u0627\u062a \u0627\u0644\u062a\u0634\u062e\u064a\u0635 \u0627\u0644\u0633\u0631\u064a\u0639</div>', unsafe_allow_html=True)
    st.caption("استخدم الأزرار التالية لفحص أكثر الأعطال شيوعا دون تغيير أي بيانات.")

    dbg_col1, dbg_col2, dbg_col3 = st.columns(3)

    if dbg_col1.button("\u200f\u0641\u062d\u0635 \u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a", key="debug_files"):
        files = [
            ("products.xlsx", "data/products.xlsx"),
            ("customers.xlsx", "data/customers.xlsx"),
            ("records.xlsx", "data/records.xlsx"),
            ("users.xlsx", "data/users.xlsx"),
            ("logs.xlsx", "data/logs.xlsx"),
            ("settings.json", "data/settings.json")
        ]
        status_rows = []
        for name, path in files:
            exists = os.path.exists(path)
            status_rows.append({
                "الملف": name,
                "المسار": path,
                "الحالة": "موجود" if exists else "مفقود"
            })
        st.dataframe(pd.DataFrame(status_rows))

    if dbg_col2.button("\u200f\u0639\u0631\u0636 \u0622\u062e\u0631 \u0627\u0644\u0633\u062c\u0644\u0627\u062a", key="debug_logs"):
        logs_df = load_logs()
        if logs_df.empty:
            st.info("لا توجد سجلات محفوظة حاليا.")
        else:
            preview = logs_df.head(10)
            st.dataframe(preview)

    if dbg_col3.button("\u200f\u0641\u062d\u0635 \u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0627\u062a\u0635\u0627\u0644", key="debug_connection"):
        if _db is None:
            st.warning("مكتبة قاعدة البيانات غير محمّلة حاليا.")
        else:
            try:
                conn_value = _db.get_connection_string()
            except Exception as err:
                st.error(f"خطأ أثناء قراءة الإعدادات: {err}")
            else:
                if conn_value:
                    masked = conn_value[: min(6, len(conn_value))] + "***"
                    st.success(f"تم العثور على سلسلة اتصال: {masked}")
                else:
                    st.info("لا توجد سلسلة اتصال مهيأة. تأكد من secrets أو المتغيرات البيئية.")


# ========================================================
# SECTION 3: TEMPLATE MANAGER
# ========================================================
def template_manager_section(user, user_name):
    """Upload document templates."""
    
    if not is_admin(user):
        st.error("Administrator privileges required to manage templates.")
        return
    
    st.markdown('<div class="crm-section-title">Document Templates</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color: var(--text-muted); font-size: 14px; margin-bottom: 24px;">'
        'Manage Word document templates for quotations, invoices, and receipts.</p>',
        unsafe_allow_html=True,
    )
    
    templates = {
        "Quotation": "quotation_template.docx",
        "Invoice": "invoice_template.docx",
        "Receipt": "receipt_template.docx"
    }
    
    for name, filename in templates.items():
        with st.expander(f"{name} Template"):
            path = f"data/{filename}"
            
            col1, col2 = st.columns([2, 1])
            with col1:
                if os.path.exists(path):
                    file_size = os.path.getsize(path)
                    size_kb = file_size / 1024
                    st.success(f"✓ Template active: {filename} ({size_kb:.1f} KB)")
                else:
                    st.warning(f"⚠️ Template not found: {filename}")
            
            st.markdown('<div class="spacing-sm"></div>', unsafe_allow_html=True)
            upload = st.file_uploader(f"Upload new {name} template", type=["docx"], key=f"tpl_{name}", help="Upload a .docx file")
            
            if upload and st.button(f"Replace Template", key=f"btn_{name}", type="primary"):
                try:
                    os.makedirs("data", exist_ok=True)
                    with open(path, "wb") as f:
                        f.write(upload.read())
                    log_event(user_name, "Settings", "template_uploaded", f"{name} template: {filename}")
                    st.success(f"✓ {name} template updated successfully")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error uploading template: {e}")


# ========================================================
# SECTION 4: BACKUP & RESTORE
# ========================================================
def backup_restore_section(user, user_name):
    """Backup and restore data."""
    
    if not is_admin(user):
        st.error("Administrator privileges required for backup operations.")
        return
    
    # Backup section
    st.markdown('<div class="crm-section-title">Create Backup</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color: var(--text-muted); font-size: 14px; margin-bottom: 20px;">'
        'Download a complete backup of all system data including users, products, customers, records, logs, and settings.</p>',
        unsafe_allow_html=True,
    )
    
    if st.button("Download Full Backup", type="primary"):
        try:
            buf = BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                files_included = []
                for fname in ["products.xlsx", "customers.xlsx", "records.xlsx", 
                             "users.xlsx", "logs.xlsx", "settings.json"]:
                    path = f"data/{fname}"
                    if os.path.exists(path):
                        zf.write(path, fname)
                        files_included.append(fname)
            buf.seek(0)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_event(user_name, "Settings", "backup_created", f"Full backup: {len(files_included)} files")
            st.download_button("⬇ Download Backup ZIP", buf, f"newton_backup_{ts}.zip", "application/zip")
            st.success(f"✓ Backup created successfully ({len(files_included)} files)")
        except Exception as e:
            st.error(f"Error creating backup: {e}")
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # Restore section
    st.markdown('<div class="crm-section-title">Restore from Backup</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background: #FFFBEA; border: 1px solid #FFE8A3; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;">
        <div style="color: #7A5B00; font-size: 14px; font-weight: 500;">
            ⚠️ Warning: This operation will replace all existing data with the backup contents. This action cannot be undone.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    restore = st.file_uploader("Upload Backup ZIP File", type=["zip"], help="Select a backup file created from this system")
    
    if restore:
        st.markdown('<div class="spacing-sm"></div>', unsafe_allow_html=True)
        if st.button("Restore Data", type="secondary"):
            try:
                with zipfile.ZipFile(restore, "r") as zf:
                    os.makedirs("data", exist_ok=True)
                    file_list = zf.namelist()
                    zf.extractall("data")
                log_event(user_name, "Settings", "restore_completed", f"Restored {len(file_list)} files")
                st.success(f"✓ Data restored successfully ({len(file_list)} files). Please refresh the page.")
            except Exception as e:
                st.error(f"Error restoring backup: {e}")


# ========================================================
# SECTION 5: LOG VIEWER
# ========================================================
def log_viewer_section(user, user_name):
    """View system logs."""
    
    st.markdown('<div class="crm-section-title">Activity Logs</div>', unsafe_allow_html=True)
    
    logs = load_logs()
    
    if logs.empty:
        st.info("No activity logs found.")
        return
    
    # Metrics - neutral gray design
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="log-metric"><div class="log-metric-value">{}</div><div class="log-metric-label">Total</div></div>'.format(len(logs)), unsafe_allow_html=True)
    with col2:
        unique_users = logs["user"].nunique() if "user" in logs.columns else 0
        st.markdown('<div class="log-metric"><div class="log-metric-value">{}</div><div class="log-metric-label">Users</div></div>'.format(unique_users), unsafe_allow_html=True)
    with col3:
        unique_pages = logs["page"].nunique() if "page" in logs.columns else 0
        st.markdown('<div class="log-metric"><div class="log-metric-value">{}</div><div class="log-metric-label">Pages</div></div>'.format(unique_pages), unsafe_allow_html=True)
    with col4:
        unique_actions = logs["action"].nunique() if "action" in logs.columns else 0
        st.markdown('<div class="log-metric"><div class="log-metric-value">{}</div><div class="log-metric-label">Actions</div></div>'.format(unique_actions), unsafe_allow_html=True)
    
    st.markdown('<div class="spacing-lg"></div>', unsafe_allow_html=True)
    
    # Filters
    st.markdown('<div class="crm-subsection">Filter Logs</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        f_user = st.text_input("User", placeholder="Search by user name")
    with c2:
        f_page = st.text_input("Page", placeholder="Search by page")
    with c3:
        f_action = st.text_input("Action", placeholder="Search by action")
    
    filtered = logs.copy()
    if f_user:
        filtered = filtered[filtered["user"].str.contains(f_user, case=False, na=False)]
    if f_page:
        filtered = filtered[filtered["page"].str.contains(f_page, case=False, na=False)]
    if f_action:
        filtered = filtered[filtered["action"].str.contains(f_action, case=False, na=False)]
    
    st.markdown('<div class="spacing-sm"></div>', unsafe_allow_html=True)
    st.markdown(f'<p style="color: var(--text-muted); font-size: 14px;">Showing <strong>{len(filtered)}</strong> of <strong>{len(logs)}</strong> logs</p>', unsafe_allow_html=True)
    
    st.dataframe(filtered, use_container_width=True, hide_index=True, height=400)
    
    st.markdown('<div class="spacing-sm"></div>', unsafe_allow_html=True)
    if st.button("Export to CSV", type="primary"):
        csv = filtered.to_csv(index=False)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button("⬇ Download CSV", csv, f"activity_logs_{ts}.csv", "text/csv")
