import os, sys
# make repo root importable so `utils` package resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.quotation_utils import render_quotation_html
import pandas as pd
import sys
from utils.settings import load_settings

catalog = pd.read_excel('data/products.xlsx')
# Optional device name arg
device_arg = sys.argv[1] if len(sys.argv) > 1 else None
row = None
if device_arg:
    matches = catalog[catalog['Device'].astype(str).str.lower() == device_arg.lower()]
    if not matches.empty:
        row = matches.iloc[0]
# fallback: first product with ImageBase64 or ImagePath
if row is None:
    for i, r in catalog.iterrows():
        if (not pd.isna(r.get('ImageBase64'))) or (not pd.isna(r.get('ImagePath'))):
            row = r
            break
if row is None:
    print('No product with image found')
    exit(0)

item = {
    'description': row.get('Description') or row.get('Device'),
    'qty': 1,
    'unit_price': float(row.get('UnitPrice') or 0),
    'total': float(row.get('UnitPrice') or 0),
    'warranty': row.get('Warranty') or '',
}
# attach image if present
if not pd.isna(row.get('ImagePath')):
    item['image'] = str(row.get('ImagePath'))
elif not pd.isna(row.get('ImageBase64')):
    item['image'] = str(row.get('ImageBase64'))

html = render_quotation_html({
    'company_name': load_settings().get('company_name','Newton Smart Home'),
    'quotation_number': 'PREVIEW-1',
    'quotation_date': '2025-12-08',
    'client_name': 'Preview Client',
    'items': [item],
})
# print a focused snippet around the first <img
idx = html.find('<img')
if idx!=-1:
    snippet = html[idx:idx+800]
    print(snippet)
else:
    # fallback: print the items table part
    start = html.find('<table class="items-table"')
    if start!=-1:
        print(html[start:start+2000])
    else:
        print('Rendered HTML does not contain an image tag')
