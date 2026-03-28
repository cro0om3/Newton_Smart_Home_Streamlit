"""Simple importer from data/*.xlsx into Postgres using utils.db helpers.

Usage: python scripts/import_from_excel.py
Make sure DB connection is set in env DB_CONNECTION_STRING or in Streamlit secrets.
"""
from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

import pandas as pd
from utils import db


def import_products():
    p = Path('data/products.xlsx')
    if not p.exists():
        print('No data/products.xlsx found — skipping products import')
        return
    df = pd.read_excel(p)
    # normalize column names that might be used in this project
    df = df.rename(columns={
        'Device': 'device', 'Description': 'description', 'UnitPrice': 'unit_price',
        'Warranty': 'warranty', 'ImagePath': 'image_path', 'ImageBase64': 'image_base64', 'SKU': 'sku'
    })
    conn = None
    inserted = 0
    for _, row in df.iterrows():
        device = str(row.get('device') or '')
        description = row.get('description')
        unit_price = row.get('unit_price')
        try:
            unit_price = float(str(unit_price).replace('AED','').replace(',','')) if unit_price not in (None, '') else 0.0
        except Exception:
            unit_price = 0.0
        warranty = row.get('warranty')
        image_path = row.get('image_path')
        image_base64 = row.get('image_base64')
        sku = row.get('sku')

        sql = (
            "INSERT INTO products(device, description, sku, unit_price, warranty, image_path, image_base64)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s)"
        )
        params = (device, description, sku, unit_price, warranty, image_path, image_base64)
        try:
            db.db_execute(sql, params)
            inserted += 1
        except Exception as e:
            print('Failed to insert product', device, e)
    print(f'Inserted {inserted} products')


def import_customers():
    p = Path('data/customers.xlsx')
    if not p.exists():
        print('No data/customers.xlsx found — skipping customers import')
        return
    df = pd.read_excel(p)
    df = df.rename(columns={'Name': 'name', 'Phone': 'phone', 'Email': 'email', 'Address': 'address'})
    inserted = 0
    for _, row in df.iterrows():
        name = str(row.get('name') or '')
        phone = row.get('phone')
        email = row.get('email')
        address = row.get('address')
        sql = "INSERT INTO customers(name, phone, email, address) VALUES (%s,%s,%s,%s)"
        try:
            db.db_execute(sql, (name, phone, email, address))
            inserted += 1
        except Exception as e:
            print('Failed to insert customer', name, e)
    print(f'Inserted {inserted} customers')


def main():
    print('Starting import — ensure DB connection is configured in st.secrets or env DB_CONNECTION_STRING')
    import_products()
    import_customers()


if __name__ == '__main__':
    main()
