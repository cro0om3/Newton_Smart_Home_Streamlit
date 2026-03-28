### Example UI Screenshots (placeholders)

Below are placeholder images for each major page. Replace these with real screenshots for production documentation.

#### Quotation Page

![Quotation UI](assets/quotation_ui.png)

#### Invoice Page

![Invoice UI](assets/invoice_ui.png)

#### Products Page

![Products UI](assets/products_ui.png)

#### Dashboard Page

![Dashboard UI](assets/dashboard_ui.png)

#### Settings Page

![Settings UI](assets/settings_ui.png)

# Newton Smart Home — Full Documentation

This document describes the Newton Smart Home Quotation app: features, structure, installation, configuration, pages, data files, templates, and deployment instructions.

**Project Summary:**

- A Streamlit-based web app to create Quotations, Invoices, Receipts and manage Products & Customers.
- Uses Excel files for data storage and Word templates for exported documents.

Example:

```py
from utils.settings import load_settings
s = load_settings()

#### save_settings(settings: dict) -> None

Example:

```py
settings['company_name'] = 'Acme Co'
save_settings(settings)
```

#### get_setting(key: str, default=None) and update_setting(key, value)

currency = get_setting('currency', 'AED')
update_setting('currency', 'USD')

```

### pages_custom/quotation_page.py

#### proper_case(text) -> str

Normalizes names/strings to Title Case and trims whitespace.

Example:

```py
proper_case('ahmed oMER')  # 'Ahmed Omer'
```

#### generate_word_file(data: dict) -> BytesIO

Fills `data/quotation_template.docx` by replacing template placeholders and inserting product images into the product table.

Important placeholder keys seen in the template usage:

- `{{client_name}}`, `{{quote_no}}`, `{{client_location}}`, `{{prepared_by}}`, `{{approved_by}}`
- `{{Price}}`, `{{Total}}`, `{{QTY}}`, `{{grand_total}}`

Example data payload:

```py
data = {
  '{{client_name}}': 'Ahmed Omer',
  '{{quote_no}}': 'QUO-20251207-001',
  '{{client_location}}': 'Dubai - Marina',
  '{{prepared_by}}': 'Sales Team',
  '{{Price}}': '5,000.00',
  '{{QTY}}': 3,
  '{{grand_total}}': '5,350.00'
}
doc_buf = generate_word_file(data)
# write to file for manual inspection
with open('out.docx','wb') as f: f.write(doc_buf.getvalue())
```

#### convert_to_pdf(word_buffer: BytesIO) -> bytes

Uses ConvertAPI to convert a DOCX buffer to PDF bytes. Note: ConvertAPI key is currently hard-coded; replace with environment config for production.

Example:

```py
pdf_bytes = convert_to_pdf(doc_buf)
with open('out.pdf','wb') as f: f.write(pdf_bytes)
```

#### load_records(), save_record(rec: dict)

Read/write helpers for `data/records.xlsx` used to persist quotes/invoices/receipts.

Example record dict:

```py
rec = {
  'base_id': '20251207-001',
  'date': '2025-12-07',
  'type': 'q',
  'number': 'QUO-20251207-001',
  'amount': 5350.0,
  'client_name': 'Ahmed Omer',
  'phone': '0501234567',
  'location': 'Dubai - Marina',
  'note': ''
}
save_record(rec)
```

#### upsert_customer_from_quotation(name, phone, location)

Adds or updates `data/customers.xlsx` based on incoming quotation data, normalizing phone formats.

### pages_custom/invoice_page.py

#### generate_word_invoice(template: str, data: dict) -> BytesIO

Simple placeholder replacement for `data/invoice_template.docx`.

Example data:

```py
data = {'{{client_name}}':'Ahmed Omer','{{invoice_no}}':'INV-20251207-001','{{grand_total}}':'1,200.00'}
buf = generate_word_invoice('data/invoice_template.docx', data)
```

#### upsert_customer_from_invoice(name, phone, location)

Similar behavior to the quotation upsert; merges by normalized name or phone.

### pages_custom/receipt_page.py

#### generate_word(template: str, data_dict: dict) -> BytesIO

Replaces placeholders in `data/receipt_template.docx` and returns a buffer for download.

Example data:

```py
payload = {'{{client_name}}':'Ahmed Omer','{{receipt_no}}':'R-20251207-20251207-001-1','{{amount}}':'500.00','{{balance}}':'700.00'}
buf = generate_word('data/receipt_template.docx', payload)
```

### pages_custom/customers_page.py

#### ensure_excel_files()

Guarantees `data/customers.xlsx` and `data/records.xlsx` exist (empty with expected columns if missing).

#### calculate_customer_finances(customer_name: str, customer_phone: str|None) -> (q,i,r,outstanding)

Aggregates totals for quotations, invoices, receipts and computes outstanding balance for the given customer by name or phone.

Example:

```py
q,i,r,o = calculate_customer_finances('Ahmed Omer','0501234567')
print(q,i,r,o)  # float totals
```

### pages_custom/products_page.py

#### image_to_base64(uploaded_file, target_size=None, mode='contain') -> str|None

Processes uploaded images (resizes, flattens background, compresses to JPEG) and returns base64 suitable for Excel cell storage.

Example use in the app:

```py
b64 = image_to_base64(uploaded_file)
```

#### save_original_image(uploaded_file, device_name) -> str|None

Saves PNG under `data/product_images/` for high-quality exports and returns the path.

#### insert_product_card(doc: Document, row: pd.Series, width_cm: float, height_cm: float, card_index: int)

Inserts product card (image + text) into a Word `Document` used by `build_word_cards_document`.

#### build_word_cards_document(products_df: pd.DataFrame) -> BytesIO

Produces a DOCX catalog from `data/catalog_template.docx` populated with product cards.

### pages_custom/reports_page.py

#### _load_records(), _load_customers(), _load_products()

Robust loaders that normalize columns and datatypes; used by `reports_app()`.

#### _apply_filters(records: pd.DataFrame) -> (filtered, meta)

Applies date, type, location and amount filters from UI and returns the filtered DataFrame and a dict of filter values.

### pages_custom/settings_page.py

#### _apply_settings_theme()

Injects CSS for the settings page design.

#### user_management_section(user, user_name) / system_config_section(user, user_name) / template_manager_section(...) / backup_restore_section(...) / log_viewer_section(...)

The five sections of `settings_app()`; each performs access checks via `utils.auth.is_admin()` and calls relevant utilities (`load_users()`, `save_users()`, `load_logs()`, etc.).

## Template Placeholder Examples

### Quotation template keys (examples used by `quotation_page.py`)

- `{{client_name}}`, `{{quote_no}}`, `{{client_location}}`, `{{prepared_by}}`, `{{approved_by}}`
- `{{Price}}`, `{{installation_cost}}`, `{{total_discount}}`, `{{grand_total}}`, `{{QTY}}`

### Invoice template keys (examples used by `invoice_page.py`)

- `{{client_name}}`, `{{invoice_no}}`, `{{client_location}}`, `{{client_phone}}`, `{{grand_total}}`

### Receipt template keys (examples used by `receipt_page.py`)

- `{{client_name}}`, `{{invoice_no}}`, `{{receipt_no}}`, `{{amount}}`, `{{balance}}`

## Screenshot Guidance (how-to)

I can add actual screenshots on request. For now, here's a short checklist for capturing reproducible screenshots to include in docs:

- Start the app locally: `streamlit run main.py`.
- Navigate to the page you want to capture (Quotation/Invoice/Products/etc.).
- Use a consistent viewport (e.g., 1366x768) and capture the entire window or the main content area.
- Save images under `docs/assets/` and reference them in the docs like: `![Quotation UI](assets/quotation_ui.png)`.

### Example UI Screenshots (placeholders)

Below are placeholder images for each major page. Replace these with real screenshots for production documentation.

#### Quotation Page

![Quotation UI](assets/quotation_ui.png)

#### Invoice Page

![Invoice UI](assets/invoice_ui.png)

#### Products Page

![Products UI](assets/products_ui.png)

#### Dashboard Page

![Dashboard UI](assets/dashboard_ui.png)

#### Settings Page

![Settings UI](assets/settings_ui.png)

## Next steps I can take for you

- Option A: Extract full function signatures and include small example tests (unit-test style) for each helper and add to `docs/`.
- Option B: Add real screenshots — I can run the app in a headless environment and capture images, but I need permission to run dependencies if you want me to do that here.
- Option C: Create a `docs/assets/` folder and add placeholder images and update the docs with inline examples.

Tell me which of the next steps to perform (A, B, or C) or if you'd like all of them; I'll proceed and update the todo list accordingly.

- Docker: use the example Dockerfile from `README.md`, expose port `8501`.

Security & Production Notes

- Replace demo PINs and avoid hard-coded convert/API credentials in code (e.g., ConvertAPI key found in `quotation_page.py`).
- Apply proper access controls and consider moving sensitive data to a secure storage or database for production use.

Development & Contribution

- Use feature branches and PRs. Add unit tests for `utils/` modules and critical page helpers.
- Keep formatting consistent with the existing code style.

Where to look next

- Authentication: `utils/auth.py`
- Settings management: `utils/settings.py`
- Page implementations: `pages_custom/*` (see per-page section above)

Contact & Support

- For issues or feature requests, open an issue in the repository or contact the project owner.

----
Generated documentation: reference for maintainers. If you want, I can:

- expand each page's function-level docstrings and example inputs/outputs,
- add screenshots and template placeholder examples,
- or run a Markdown linter and make additional style fixes.

Template Placeholder Examples

- Quotation template keys (examples used by `quotation_page.py`):
  - `{{client_name}}`, `{{quote_no}}`, `{{client_location}}`, `{{prepared_by}}`, `{{approved_by}}`
  - `{{Price}}`, `{{installation_cost}}`, `{{total_discount}}`, `{{grand_total}}`, `{{QTY}}`

- Invoice template keys (examples used by `invoice_page.py`):
  - `{{client_name}}`, `{{invoice_no}}`, `{{client_location}}`, `{{client_phone}}`, `{{grand_total}}`

- Receipt template keys (examples used by `receipt_page.py`):
  - `{{client_name}}`, `{{invoice_no}}`, `{{receipt_no}}`, `{{amount}}`, `{{balance}}`

Screenshot Guidance (how-to)

- I can add actual screenshots on request. For now, here's a short checklist for capturing reproducible screenshots to include in docs:
  - Start the app locally: `streamlit run main.py`.
  - Navigate to the page you want to capture (Quotation/Invoice/Products/etc.).
  - Use a consistent viewport (e.g., 1366x768) and capture the entire window or the main content area.
  - Save images under `docs/assets/` and reference them in the docs like: `![Quotation UI](assets/quotation_ui.png)`.

Next steps I can take for you

- Option A: Extract full function signatures and include small example tests (unit-test style) for each helper and add to `docs/`.
- Option B: Add real screenshots — I can run the app in a headless environment and capture images, but I need permission to run dependencies if you want me to do that here.
- Option C: Create a `docs/assets/` folder and add placeholder images and update the docs with inline examples.

Tell me which of the next steps to perform (A, B, or C) or if you'd like all of them; I'll proceed and update the todo list accordingly.
