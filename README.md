# Newton Smart Home – Quotation App

Streamlit app to generate Quotations, Invoices, and Receipts with Excel-backed data and Word template export.

## Run Locally

```powershell
# From repo root
pip install -r requirements.txt
streamlit run main.py
```

## Deploy on Streamlit Community Cloud

1. Push this folder to a public GitHub repository.
2. Go to <https://share.streamlit.io> and select your repo.
3. App entrypoint: `main.py` (Python 3.10+ recommended).
4. Add Streamlit secrets if needed in the cloud console (`[secrets]`).

Notes:

- The app auto-creates Excel files on first run for customers/products/records.
- Keep your Word templates in `data/`:
  - `data/quotation_template.docx`
  - `data/invoice_template.docx`
  - `data/receipt_template.docx`
- Runtime Excel data (`*.xlsx`) is ignored by Git (see `.gitignore`).

## Deploy to your own server (optional)

- Use `gunicorn` + `streamlit` or Docker. Minimal Dockerfile:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## Repository Structure (key paths)

- `main.py` – routing + global theme
- `pages_custom/` – pages: quotation, invoice, receipt, customers, products
- `data/` – Word templates and runtime Excel files
- `requirements.txt` – Python dependencies

## Pages

- `home.py` – Home page
- `quotation.py` – Quotation page
- `invoice.py` – Invoice page
- `receipt.py` – Receipt page
- `customers.py` – Customers page
- `products.py` – Products page
- `dashboard.py` – Dashboard page

## Active Page Logic

- `home.py` – Home page
- `quotation.py` – Quotation page
- `invoice.py` – Invoice page
- `receipt.py` – Receipt page
- `customers.py` – Customers page
- `products.py` – Products page
- `dashboard.py` – Dashboard page
# nEWO
