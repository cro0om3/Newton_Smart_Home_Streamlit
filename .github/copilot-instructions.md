# Copilot / AI Agent Instructions 
دايما رد علي باللغة العربية لوسمحت و لاتغير المنطق في الكود و يوم ارسلك تمبلت او شيء لا تغير فيه في التصميم او الشكل اعتمد نفس كل شيئ 

Short, practical guidance for an AI coding assistant working on this repository.

1. Big picture
- App type: a Streamlit single-process web app. Entrypoint: `main.py` which handles authentication, theme injection and routes into page modules under `pages_custom/`.
- Pages live in `pages_custom/` (e.g. `quotation_page.py`, `invoice_page.py`, `receipt_page.py`, `dashboard_new.py`). Each page exports a page function (e.g. `quotation_app`) that `main.py` imports and calls.
- Utilities and shared logic live in `utils/` (examples: `auth.py`, `settings.py`, `logger.py`, `quotation_utils.py`). Data storage is flat files under `data/` (Excel `.xlsx`, JSON settings, Word templates).

2. Key data flows & service boundaries
- Authentication: PIN-based with users stored in `data/users.xlsx` and helpers in `utils/auth.py`. Default pins are created automatically (Admin=1234, Staff=5678, Viewer=9999).
- Product/customer/record persistence: stored as Excel files in `data/` (e.g. `products.xlsx`, `customers.xlsx`, `records.xlsx`). Code frequently uses `pandas.read_excel` and `to_excel`.
- Document generation: quotation HTML rendering and PDF conversion happens via `utils/quotation_utils.py` (uses HTML -> PDF utilities such as `weasyprint`, `pdfkit`, `aspose-words`, or `convertapi` depending on environment and availability).

3. Project-specific conventions you must follow
- File-backed state: do not assume a database. Always read/write the `data/` files using the helpers (or follow the same patterns): ensure `data/` exists, handle missing files by creating default templates.
- Column names matter: many routines expect specific columns. Examples:
  - `data/products.xlsx` must include `Device`, `Description`, `UnitPrice`, `Warranty` (see `pages_custom/quotation_page.py`).
  - `data/users.xlsx` is created with `name`, `pin`, `role`, `allowed_pages` (see `utils/auth.py`).
  - `data/records.xlsx` expected columns include `base_id, date, type, number, amount, client_name, phone, location, note` (see `quotation_page.py`).
- Session state keys: the app relies heavily on `st.session_state`. Important keys:
  - `ui_theme` ("light"/"dark")
  - `authenticated`, `user`, `show_pin`
  - `product_table` (DataFrame of products added to a quotation)
  - page-specific keys prefixed with `quo_`, `inv_`, etc.
- UI/Styling: `main.py` injects CSS strings (`light_css`, `dark_css`) 

4. Typical developer workflows (commands and notes)
- Local dev (Windows PowerShell):
  - Install deps: `pip install -r requirements.txt`
  - Run app: `streamlit run main.py`
  - Quick test: `python scripts/test_quotation_render.py` (exercise the quotation renderer)
- Docker: README includes a minimal `Dockerfile` example (Streamlit on port `8501`). For CI or production, prefer containerization and an external PDF conversion service if using licensed tools.

5. Integration & external dependencies
- The `requirements.txt` includes third-party services that may require credentials or paid licenses: `convertapi`, `aspose-words`, `docx2pdf`, `weasyprint`. If your change touches document conversion, add fallbacks and config checks for API keys.
- Secrets: Streamlit deployment expects any API keys in Streamlit secrets. Locally, the code reads from `data/` files; do not hardcode credentials in code.

6. Tests and validation
- There are lightweight scripts under `scripts/` (not a full test suite). Example: `scripts/test_quotation_render.py` demonstrates rendering a quotation to HTML/PDF and can be run directly.

7. Safe edit patterns for AI agents
- Preserve data creation logic: if adding or refactoring persistence, keep the helper that ensures `data/` and default files exist (e.g. `ensure_users_file`, `ensure_customers_file`, `ensure_settings_file`).
- When changing spreadsheet schemas, update every consumer: many functions use column names directly (no central schema validation).
- Avoid adding runtime blocking network calls in UI render paths; use background tasks or explicit user-triggered actions when calling external APIs.

8. Examples from the codebase (copy/paste friendly)
- Load products and validate columns:
```py
catalog = pd.read_excel("data/products.xlsx")
required_cols = ["Device", "Description", "UnitPrice", "Warranty"]
for col in required_cols:
    if col not in catalog.columns:
        raise RuntimeError(f"Missing column: {col}")
```
- Validate PIN and build user dict (see `utils/auth.py`):
```py
user = validate_pin(pin)
if user:
    st.session_state.authenticated = True
    st.session_state.user = user
```

9. Where to look when things break
- Authentication/login: `utils/auth.py` + `main.py` login block
- Theme and CSS issues: `main.py` (theme injection functions) and `pages_custom/*` which assume CSS classes exist
- Document rendering: `utils/quotation_utils.py` and `scripts/test_quotation_render.py`

10. If you modify or add high-level behavior
- Update `README.md` and `docs/full_documentation_en.md` with any changed runtime steps.
- When adding new external services, document required config/secrets and add defensive checks to avoid runtime errors for users without keys.

If anything here is unclear or you want more detail (for example: a mapping of all `st.session_state` keys, or a list of all data file schemas), tell me which area to expand and I'll iterate.
