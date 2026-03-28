import streamlit as st
import os
from datetime import datetime
from base64 import b64encode


def _sync_streamlit_secrets_to_env() -> None:
    """Mirror Cloud/local secrets into os.environ for modules that use getenv()."""
    try:
        sec = st.secrets
        for key in (
            "DB_CONNECTION_STRING",
            "DB_CONNECTION_STRING_POOLER",
            "SUPABASE_POOLER_REGION",
            "OPENAI_API_KEY",
            "CONVERTAPI_SECRET",
        ):
            if os.environ.get(key):
                continue
            try:
                val = sec[key]
            except Exception:
                continue
            if val:
                os.environ[key] = str(val).strip()
    except Exception:
        pass


_sync_streamlit_secrets_to_env()
from utils.db import check_db_connection
from pages_custom.quotation_page import quotation_app
from pages_custom.invoice_page import invoice_app
from pages_custom.receipt_page import receipt_app
from pages_custom.dashboard_new import dashboard_new_app
from pages_custom.customers_page import customers_app
from pages_custom.products_page import products_app
from pages_custom.reports_page import reports_app
from pages_custom.archive_page import archive_app
from pages_custom.settings_page import settings_app
from pages_custom.power_tools_page import power_tools_app
from utils.auth import validate_pin, can_access_page, is_admin
from utils.logger import log_event
from utils.settings import load_settings
import re
from pathlib import Path

# ===========================
# THEME ENGINE (Light/Dark Toggle)
# ===========================
# Persist UI theme in session state
if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = "light"
# Accent overlay (keeps light/dark but applies an accent color scheme)
if 'ui_accent' not in st.session_state:
    try:
        st.session_state.ui_accent = load_settings().get('ui_accent', 'none')
    except Exception:
        st.session_state.ui_accent = 'none'

light_css = """
<style>
:root {
    --bg-primary: #F6F8FB;
    --bg-card: #FFFFFF;
    --bg-input: #FFFFFF;
    --bg-sidebar: #EEF3FA;

    --text: #0F172A;
    --text-soft: #475569;

    --border: #D6DEE9;
    --border-soft: #E8EDF5;

    --button: #2F6FED;
    --button-hover: #1E5ADB;
    --on-accent: #FFFFFF;
    --accent-soft: #E8F0FF;
    --focus-ring: rgba(47,111,237,0.22);
    --success: #16A34A;
    --warning: #D97706;
    --danger: #DC2626;

    --hover-glow-rgba: rgba(47,111,237,0.18);

    --accent: #2F6FED;
}
/* Selectbox (light) – colors only */
[data-baseweb="select"] > div {
    background: var(--bg-input) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
}
[data-baseweb="select"] span { color: var(--text) !important; }
[data-baseweb="popover"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    z-index: 9999 !important;
}
[data-baseweb="menu-item"]:hover {
    background: var(--button-hover) !important;
    color: var(--text) !important;
}
[data-baseweb="menu"] li,
[data-baseweb="menu"] div {
    color: var(--text) !important;
    background: var(--bg-card) !important;
}
[data-baseweb="menu-item"][aria-selected="true"] {
    background: var(--accent) !important;
    color: white !important;
}
</style>
"""

dark_css = """
<style>
:root {
    --bg-primary: #0B1220;
    --bg-card: #111A2B;
    --bg-input: #172238;
    --bg-sidebar: #0A1424;

    --text: #E6EEF8;
    --text-soft: #9FB0C8;

    --border: #24344F;
    --border-soft: #1B2A41;

    --button: #5B8CFF;
    --button-hover: #7AA4FF;
    --accent: #5B8CFF;
    --on-accent: #FFFFFF;
    --accent-soft: #1B2C52;
    --focus-ring: rgba(91,140,255,0.28);
    --success: #22C55E;
    --warning: #F59E0B;
    --danger: #F87171;
    --hover-glow-rgba: rgba(91,140,255,0.20);
}

/* Selectbox (dark) – colors only */
[data-baseweb="select"] > div {
    background: var(--bg-input) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
}
[data-baseweb="select"] span { color: var(--text) !important; }
[data-baseweb="popover"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    z-index: 9999 !important;
}
[data-baseweb="menu-item"]:hover {
    background: var(--button-hover) !important;
    color: var(--text) !important;
}
[data-baseweb="menu"] li,
[data-baseweb="menu"] div {
    color: var(--text) !important;
    background: var(--bg-card) !important;
}
[data-baseweb="menu-item"][aria-selected="true"] {
    background: var(--accent) !important;
    color: white !important;
}
</style>
"""

def inject_theme():
    """Inject the currently selected theme CSS."""
    if st.session_state.ui_theme == "light":
        st.markdown(light_css, unsafe_allow_html=True)
    else:
        st.markdown(dark_css, unsafe_allow_html=True)
    # Inject accent overlay if selected
    accent = st.session_state.get('ui_accent', 'none')
    if accent == 'winter':
        st.markdown(
            """
            <style>
            :root {
                --accent: #7FD3FF; /* winter accent variant */
                --button: #7FD3FF;
                --button-hover: #AEEBFF;
            }
            /* subtle overlay for selected controls */
            button[key^="nav_"]:hover, button[key^="sidenav_"]:hover, [data-testid="stButton"] > button:hover {
                box-shadow: 0 10px 36px rgba(127,211,255,0.12) !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
    # Show a small startup toast if an accent is active (only once per session)
    if st.session_state.get('ui_accent', 'none') != 'none' and not st.session_state.get('_accent_toast_shown', False):
        acc = st.session_state.get('ui_accent', 'none')
        # Arabic message with dismiss (X) and auto-hide after 5s
        st.markdown(
            """
            <div id='accent_toast' style='position:fixed;right:20px;bottom:20px;z-index:99999;direction:rtl;'>
                <div style='background:rgba(10,132,255,0.06);border:1px solid rgba(127,211,255,0.18);padding:10px 14px;border-radius:10px;color:var(--text);backdrop-filter:blur(6px);box-shadow:0 6px 18px rgba(0,0,0,.12);min-width:180px;display:flex;align-items:center;gap:10px;'>
                    <div style='flex:1'>
                        <div style='font-size:13px;'>الثيم النشط:</div>
                        <div style='font-weight:700;color:var(--accent);'>""" + acc + """</div>
                    </div>
                    <button id='accent_toast_close' style='background:transparent;border:0;color:var(--text);font-weight:700;cursor:pointer;padding:6px 8px;border-radius:6px;'>✕</button>
                </div>
            </div>
            <script>
                const toast = document.getElementById('accent_toast');
                const closeBtn = document.getElementById('accent_toast_close');
                if (closeBtn) {
                    closeBtn.addEventListener('click', function(){ toast.style.transition='opacity 400ms'; toast.style.opacity='0'; setTimeout(function(){ toast.remove() },420); });
                }
                // Auto-hide after 5 seconds
                setTimeout(function(){ if (toast) { toast.style.transition='opacity 600ms'; toast.style.opacity='0'; setTimeout(function(){ try{ toast.remove() }catch(e){} },620); } }, 5000);
            </script>
            """,
            unsafe_allow_html=True,
        )
        st.session_state['_accent_toast_shown'] = True


st.set_page_config(page_title="Newton Smart Home OS", layout="wide")


def template_health_check():
    """Scan `templates/` for missing expected templates and simple Jinja issues.

    Detects:
    - Missing expected template files
    - Unbalanced '{{' vs '}}' occurrences
    - '{{ ... }}' print blocks that contain a '%' character (likely accidental)
    """
    tpl_dir = Path(__file__).resolve().parents[0] / 'templates'
    expected = [
        'newton_invoice_A4.html',
        'newton_quotation_A4.html',
        'newton_receipt_A4.html',
    ]
    issues = []
    if not tpl_dir.exists():
        issues.append(f"Templates folder not found: {tpl_dir}")
    else:
        for name in expected:
            if not (tpl_dir / name).exists():
                issues.append(f"Missing template: {name}")

        for p in sorted(tpl_dir.glob('*.html')):
            try:
                txt = p.read_text(encoding='utf-8')
            except Exception as e:
                issues.append(f"Cannot read {p.name}: {e}")
                continue
            # Unbalanced braces
            if txt.count('{{') != txt.count('}}'):
                issues.append(f"Unbalanced braces in {p.name}: '{{{{' x{txt.count('{{')}, '}}' x{txt.count('}}')} )")
            # Look for suspicious percent signs inside print blocks
            for m in re.finditer(r'\{\{\s*([^}]+?)\s*\}\}', txt):
                inner = m.group(1)
                if '%' in inner:
                    issues.append(f"Suspicious token in {p.name}: '{{{{ {inner.strip()} }}}}'")

    if issues:
        # Print to console for logs
        print("TEMPLATE HEALTH CHECK FOUND ISSUES:")
        for it in issues:
            print(" - ", it)
        try:
            # Show warnings in the Streamlit UI so users see issues early
            st.warning("Template health check found issues. Open console for details.")
        except Exception:
            pass


# Run template health check early so problems are visible on startup
if "_template_health_checked" not in st.session_state:
    template_health_check()
    st.session_state["_template_health_checked"] = True

# ===========================
# PIN LOGIN SYSTEM
# ===========================
# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "show_pin" not in st.session_state:
    st.session_state.show_pin = False

# Show login screen if not authenticated
if not st.session_state.authenticated:
    # Load logo for PIN page
    logo_path = Path("data") / "logo.png"
    logo_html = ""
    if logo_path.exists():
        import base64
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
            logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width:400px; margin-bottom:1px;">'
    
    st.markdown(f"""
        <div style='text-align:center; padding:10px 20px;'>
            {logo_html}
            <h1 style='color:var(--accent); font-size:28px; margin-bottom:1px;'>Secure Access</h1>
            <p style='color:var(--text-soft); font-size:14px;'>Enter your PIN to continue</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pin_input = st.text_input(
            "PIN",
            type="password" if not st.session_state.show_pin else "default",
            max_chars=6,
            placeholder="Enter 4-6 digit PIN",
            label_visibility="collapsed"
        )
        
        # Ensure the checkbox key exists in session_state (do not pass value=)
        if "show_pin_checkbox" not in st.session_state:
            st.session_state.show_pin_checkbox = st.session_state.show_pin
        show_hide = st.checkbox("Show PIN", key="show_pin_checkbox")
        if show_hide != st.session_state.show_pin:
            st.session_state.show_pin = show_hide
            st.rerun()
        
        if st.button("Login", use_container_width=True):
            user_data = validate_pin(pin_input)
            if user_data:
                st.session_state.authenticated = True
                st.session_state.user = user_data
                st.session_state.login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_event(user_data["name"], "Login", "login_success", f"Role: {user_data['role']}")
                st.success(f"✅ Welcome, {user_data['name']}!")
                st.rerun()
            else:
                log_event("Unknown", "Login", "login_failed", f"Invalid PIN: {pin_input[:2]}***")
                st.error("❌ Invalid PIN. Please try again.")
    
    st.stop()

# User is authenticated - continue with app

# Load logo as data URI



st.markdown(
    """
    <style>
    :root { 
        --brand-blue:#0a84ff; /* kept for nav highlights */
        --accent:#0a84ff; --accent-light:#5ac8fa; 
        --ink:#1d1d1f; --sub:#6e6e73; 
        --glass:rgba(255,255,255,.95); --glass-border:rgba(0,0,0,.06);
        --text-primary:#1d1d1f;
    }
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg,#fafafa 0%,#f0f0f5 100%);
        font-family: "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--text-primary);
    }
    [data-testid="stHeader"] { background-color: transparent; }

    .hero-card{
        background: linear-gradient(135deg, rgba(255,255,255,.95) 0%, rgba(248,248,252,.92) 100%);
        border: 1px solid var(--glass-border);
        border-radius: 24px;
        padding: 28px 32px;
        box-shadow: 0 2px 8px rgba(0,0,0,.04), 0 12px 32px rgba(0,0,0,.08);
        backdrop-filter: blur(20px);
        margin-bottom: 18px;
        overflow: visible;
        position: relative;
    }

    /* New header layout: left (page title) | center (nav buttons) | right (logo) */
    .header-container{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
        margin-bottom: 12px;
        min-height: 80px;
    }
    
    .page-title-section{
        flex: 0 0 auto;
        min-width: 200px;
    }
    
    .page-title{
        font-size: 28px;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0;
        line-height: 1.2;
    }
    
    .page-subtitle{
        font-size: 14px;
        color: #6e6e73;
        margin: 4px 0 0 0;
    }
    
    .nav-buttons-section{
        flex: 1;
        display: flex;
        justify-content: center;
        gap: 12px;
    }
    
    .logo-section{
        flex: 0 0 auto;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        min-width: 200px;
        position: absolute;
        right: -10px;
        top: 50%;
        transform: translateY(-50%);
    }
    
    .logo-badge{
        width: 350px;
        height: auto;
        max-height: none;
    }

    /* Compact vertical rhythm */
    [data-testid="block-container"]{ padding-top: 4px !important; }
    div[data-testid="element-container"]{ margin-bottom: 6px !important; }
    [data-testid="stButton"]{ margin-bottom: 0 !important; }

    /* Global compact buttons (match Invoice page sizing) */
    [data-testid="stButton"] > button{
        background: linear-gradient(145deg,#ffffff 0%,#f9f9fb 100%) !important;
        border: 1px solid rgba(0,0,0,.08) !important;
        border-radius: 12px !important;
        padding: 8px 16px !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        color: var(--ink) !important;
        box-shadow: 0 2px 6px rgba(0,0,0,.05) !important;
        transition: all .18s ease !important;
        white-space: nowrap !important;
    }
    [data-testid="stButton"] > button:hover{
        transform: translateY(-2px) !important;
        /* Winter-style hover: subtle icy glow using the accent hover color */
        box-shadow: 0 8px 30px var(--hover-glow-rgba) !important;
    }

    /* Uniform compact sizing for top nav buttons (4 cards) */
    button[key^="nav_"]{
        min-height: 44px !important;
        height: 44px !important;
        padding: 6px 14px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 12px !important;
        white-space: nowrap !important;
        font-size: 13px !important;
        line-height: 1 !important;
        transition: transform .18s ease, box-shadow .18s ease, background .12s ease !important;
    }
    /* Sidebar items consistent height as well */
    button[key^="sidenav_"]{
        min-height: 44px !important;
        height: 44px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 12px !important;
        font-size: 0.93rem !important;
    }

    /* Global form controls to match Invoice  pages */
    /* جميع الحقول تعتمد فقط على متغيرات الثيم */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] select{
        background: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        font-size: 14px !important;
        box-shadow: 0 2px 6px rgba(0,0,0,.04) !important;
        height: 40px !important;
        outline: none !important;
        transition: border-color .12s ease, box-shadow .12s ease !important;
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stSelectbox"] select:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--focus-ring) !important;
    }
    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stNumberInput"] input::placeholder{
        color: #9ca3af !important;
        opacity: 1 !important;
    }
    .stSelectbox div[data-baseweb="select"],
    .stSelectbox div[role="combobox"],
    .stSelectbox div[role="listbox"],
    .stSelectbox [role="option"]{
        background: var(--bg-input) !important;
        color: var(--text-primary) !important;
    }
    .stSelectbox div[data-baseweb="select"] > div,
    .stSelectbox div[role="combobox"] > div{
        background: var(--bg-input) !important;
    }
    .stSelectbox div[data-baseweb="select"]:focus-within,
    .stSelectbox div[role="combobox"]:focus-within{
        background: var(--bg-input) !important;
    }
    .stSelectbox svg{ color: var(--text-soft) !important; }
    /* أزرار + و - تعتمد فقط على متغيرات الثيم */
    [data-testid="stNumberInput"] button {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        border-radius: 8px !important;
        transition: background .15s;
    }
    [data-testid="stNumberInput"] button:hover {
        background: var(--bg-input) !important;
    }
    .stSelectbox [role="option"][aria-selected="true"]{
        background: var(--accent-soft) !important;
        color: var(--text-primary) !important;
    }

    /* Common utility classes from Invoice theme */
    .section-title{ font-size:20px; font-weight:700; margin:18px 0 10px; color:var(--ink); }
    .added-product-row{
        background: var(--bg-card); padding:10px 14px; border:1px solid var(--border);
        border-radius:12px; margin-bottom:6px; box-shadow:0 2px 6px rgba(0,0,0,.05);
    }
    .product-header{
        display:flex; gap:1rem; padding:8px 0 12px;
        border-bottom:1px solid rgba(0,0,0,.08); background:transparent;
        font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color: var(--text-soft);
        margin-bottom:10px; align-items:center;
    }
    .product-header span{text-align:center;}
    .product-header span:nth-child(1){flex:4.5; text-align:left;}
    .product-header span:nth-child(2){flex:0.7;}
    .product-header span:nth-child(3){flex:1;}
    .product-header span:nth-child(4){flex:1;}
    .product-header span:nth-child(5){flex:0.7;}
    .product-header span:nth-child(6){flex:0.7;}
    </style>
    """,
    unsafe_allow_html=True,
)

# Inject the selected theme AFTER app base CSS so theme wins in cascade
inject_theme()

# Base color mapping using variables (colors only; no sizes changed)
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] { background: var(--bg-primary) !important; color: var(--text) !important; }
    [data-testid="stHeader"] { color: var(--text) !important; }
    [data-testid="stSidebar"] { background: var(--bg-sidebar) !important; color: var(--text) !important; }

    .page-subtitle { color: var(--text-soft) !important; }
    .hero-card { background: var(--bg-card) !important; border: 1px solid var(--border-soft) !important; color: var(--text) !important; }

    /* Generic buttons (neutral). Keep geometry elsewhere; colors from variables */
    [data-testid=stButton] > button { background: var(--bg-card) !important; color: var(--text) !important; border: 1px solid var(--border) !important; }
    [data-testid=stButton] > button:hover { background: var(--button-hover) !important; color: var(--on-accent) !important; }

    /* Nav buttons (default neutral, active accent) */
    button[key^="nav_"] { background: var(--bg-card) !important; color: var(--text) !important; border: 1px solid var(--border) !important; }
    button[key^="nav_"]:hover { background: var(--button-hover) !important; color: var(--on-accent) !important; transform: translateY(-2px) !important; box-shadow: 0 8px 30px var(--hover-glow-rgba) !important; }

    /* Sidebar buttons (default neutral, active accent set below) */
    button[key^="sidenav_"] { background: var(--bg-card) !important; color: var(--text) !important; border: 1px solid var(--border) !important; }
    button[key^="sidenav_"]:hover { background: var(--button-hover) !important; color: var(--on-accent) !important; }

    /* Inputs */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] select,
    textarea, input, select {
        background: var(--bg-input) !important; color: var(--text) !important; border: 1px solid var(--border) !important;
    }
    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stNumberInput"] input::placeholder { color: var(--text-soft) !important; }

    /* Streamlit Selectbox (BaseWeb) — ensure dropdown and control use variables */
    .stSelectbox div[data-baseweb="select"],
    .stSelectbox div[role="combobox"] {
        background: var(--bg-input) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
    }
    .stSelectbox div[data-baseweb="select"]:focus-within,
    .stSelectbox div[role="combobox"]:focus-within {
        border-color: var(--accent) !important;
    }
    .stSelectbox svg { color: var(--text) !important; }
    .stSelectbox [role="listbox"],
    .stSelectbox [role="option"],
    [data-baseweb="menu"],
    [data-baseweb="popover"] [role="listbox"] {
        background: var(--bg-card) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
    }
    .stSelectbox [role="option"][aria-selected="true"],
    .stSelectbox [role="option"]:hover {
        background: var(--button-hover) !important;
        color: var(--on-accent) !important;
    }
    .stSelectbox [aria-placeholder="true"],
    .stSelectbox [data-baseweb="select"] [class*="placeholder"],
    .stSelectbox [role="combobox"] [class*="placeholder"] {
        color: var(--text-soft) !important;
    }

    /* Horizontal rule under subheaders or sections */
    [data-testid="stMarkdownContainer"] hr, hr { border: none !important; border-top: 1px solid var(--border-soft) !important; }

    /* Tables */
    [data-testid="stTable"] table { background: var(--bg-card) !important; color: var(--text) !important; }
    [data-testid="stTable"] th { color: var(--text-soft) !important; border-bottom: 1px solid var(--border) !important; }
    [data-testid="stTable"] td { color: var(--text) !important; border-bottom: 1px solid var(--border-soft) !important; }

    /* Utility */
    .section-title { color: var(--text) !important; }
    .added-product-row { background: var(--bg-card) !important; border: 1px solid var(--border-soft) !important; color: var(--text) !important; }
    .product-header { border-bottom: 1px solid var(--border-soft) !important; color: var(--text-soft) !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "active_page" not in st.session_state:
    st.session_state.active_page = "dashboard"

# Page titles mapping
PAGE_TITLES = {
    "dashboard": ("Newton Dashboard", "Monitor live analytics"),
    "quotation": ("Newton Quotation", "Draft elegant proposals"),
    "invoice": ("Newton Invoice", "Bill with confidence"),
    "receipt": ("Newton Receipt", "Acknowledge payments"),
    "customers": ("Customers", "Manage client accounts"),
    "products": ("Products", "Manage catalog"),
    "reports": ("Reports", "Business insights"),
    "archive": ("Archive", "Retrieve saved documents"),
    "settings": ("Settings", "Configure application"),
    "power_tools": ("⚡ Power Tools", "Unlimited admin capabilities"),
}

# Single source of truth for emojis used across nav buttons
ICON_MAP = {
    "dashboard": "📊",
    "quotation": "📝",
    "invoice": "💳",
    "receipt": "🧾",
    "customers": "👥",
    "products": "📦",
    "reports": "📈",
    "archive": "🗂️",
    "settings": "⚙️",
    "power_tools": "⚡",
    "logout": "🚪",
    "dark": "🌙",
    "light": "☀️",
}

# Load logo as data URI
def _load_logo_datauri():
    candidates = ["data/newton_logo.png", "data/newton_logo.svg", "data/logo.png", "data/logo.svg"]
    base = os.path.dirname(__file__)
    for rel in candidates:
        path = os.path.join(base, rel)
        if os.path.exists(path):
            ext = os.path.splitext(path)[1].lower()
            mime = "image/png" if ext == ".png" else "image/svg+xml" if ext == ".svg" else None
            if not mime:
                continue
            with open(path, "rb") as f:
                data = b64encode(f.read()).decode("utf-8")
            return f"data:{mime};base64,{data}"
    return None

# Load logo
_logo_uri = _load_logo_datauri()
# Render logo responsively so it fits within the hero card
_logo_html = (
    f'<img src="{_logo_uri}" alt="Newton Smart Home" class="logo-badge" '
    f'style="max-width:60%;height:auto;object-fit:contain;" />'
    if _logo_uri
    else '<div class="logo-badge" style="display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0a84ff,#5bc0ff);border-radius:16px;color:white;font-weight:700;font-size:18px;padding:10px 14px;">NEWTON</div>'
)

# Get current page info
current_title, current_subtitle = PAGE_TITLES.get(st.session_state.active_page, ("Dashboard", "Monitor live analytics"))

# Header structure
st.markdown(
    f"""
    <div class="hero-card">
        <div class="header-container">
            <div class="page-title-section">
                <h1 class="page-title">{current_title}</h1>
                <p class="page-subtitle">{current_subtitle}</p>
            </div>
            <div class="nav-buttons-section" id="nav-buttons-placeholder"></div>
            <div class="logo-section">
                {_logo_html}
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar navigation (mirrors top nav)
with st.sidebar:
    # User info and logout
    user = st.session_state.get("user", {})
    user_name = user.get("name", "User")
    user_role = user.get("role", "viewer")
    
    st.markdown(f"""
        <div style='padding:12px; background:var(--bg-card); border-radius:12px; margin-bottom:16px; border:1px solid var(--border-soft);'>
            <div style='font-weight:600; color:var(--text);'>User: {user_name}</div>
            <div style='font-size:12px; color:var(--text-soft); margin-top:4px;'>Role: {user_role.title()}</div>
        </div>
    """, unsafe_allow_html=True)

    _ok_db, _db_msg = check_db_connection()
    if _ok_db:
        st.caption("Supabase: متصل")
    else:
        with st.expander("Supabase: غير متصل", expanded=True):
            st.warning(_db_msg)

    if st.button(f"{ICON_MAP['logout']} Logout", use_container_width=True, key="logout_btn"):
        log_event(user_name, "System", "logout", f"User logged out")
        st.session_state.authenticated = False
        st.session_state.user = None
        st.rerun()
    
    st.markdown("---")
    
    # Theme toggle
    if st.session_state.ui_theme == "light":
        if st.button(f"{ICON_MAP['dark']} Dark Mode", key="toggle_dark"):
            st.session_state.ui_theme = "dark"
            st.rerun()
    else:
        if st.button(f"{ICON_MAP['light']} Light Mode", key="toggle_light"):
            st.session_state.ui_theme = "light"
            st.rerun()

    st.markdown("<div style='font-weight:700;margin:6px 0;color:var(--text);'>Navigation</div>", unsafe_allow_html=True)
    _side_nav_items = [
        ("dashboard", f"{ICON_MAP['dashboard']} Dashboard"),
        ("quotation", f"{ICON_MAP['quotation']} Quotation"),
        ("invoice", f"{ICON_MAP['invoice']} Invoice"),
        ("receipt", f"{ICON_MAP['receipt']} Receipt"),
        ("customers", f"{ICON_MAP['customers']} Customers"),
        ("products", f"{ICON_MAP['products']} Products"),
        ("reports", f"{ICON_MAP['reports']} Reports"),
        ("archive", f"{ICON_MAP['archive']} Archive"),
        ("settings", f"{ICON_MAP['settings']} Settings"),
    ]
    for page_id, title in _side_nav_items:
        # Check if user has access to this page
        if not can_access_page(user, page_id):
            # Show disabled button for pages without access
            st.markdown(f"<div style='padding:8px; color:var(--text-soft); opacity:0.5;'>{title} (Locked)</div>", unsafe_allow_html=True)
        else:
            if st.button(title, key=f"sidenav_{page_id}", use_container_width=True):
                st.session_state.active_page = page_id
                st.rerun()

    

# Navigation buttons (will appear in the center)
NAV_ITEMS = [
    ("dashboard", f"{ICON_MAP['dashboard']} Dashboard"),
    ("quotation", f"{ICON_MAP['quotation']} Quotation"),
    ("invoice", f"{ICON_MAP['invoice']} Invoice"),
    ("receipt", f"{ICON_MAP['receipt']} Receipt"),
]

nav_cols = st.columns(4)
for col, (page_id, title) in zip(nav_cols, NAV_ITEMS):
    with col:
        pressed = st.button(title, key=f"nav_{page_id}", use_container_width=True)
        if pressed:
            st.session_state.active_page = page_id
            st.rerun()

st.markdown(
    f"""
    <style>
    button[key="nav_{st.session_state.active_page}"] {{
        background: var(--accent) !important;
        color: var(--on-accent) !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ===========================
# PAGE ACCESS CONTROL
# ===========================
current_page = st.session_state.active_page
user = st.session_state.get("user", {})

# Check if user has access to current page
if not can_access_page(user, current_page):
    log_event(user.get("name", "Unknown"), current_page, "access_denied", f"Attempted to access {current_page}")
    st.error("Access Denied")
    st.warning(f"You don't have permission to access the **{current_page.title()}** page.")
    st.info(f"Your role: **{user.get('role', 'unknown').title()}**")
    st.markdown("Please contact an administrator if you need access to this page.")
    st.stop()

# Log successful page access
if st.session_state.get("_last_logged_page") != current_page:
    log_event(user.get("name", "Unknown"), current_page, "access_granted", f"Opened {current_page} page")
    st.session_state["_last_logged_page"] = current_page

if st.session_state.active_page == "dashboard":
    dashboard_new_app()
elif st.session_state.active_page == "quotation":
    quotation_app()
elif st.session_state.active_page == "invoice":
    invoice_app()
elif st.session_state.active_page == "receipt":
    receipt_app()
elif st.session_state.active_page == "customers":
    customers_app()
elif st.session_state.active_page == "products":
    products_app()
elif st.session_state.active_page == "reports":
    reports_app()
elif st.session_state.active_page == "archive":
    archive_app()
elif st.session_state.active_page == "settings":
    settings_app()
elif st.session_state.active_page == "power_tools":
    power_tools_app()
