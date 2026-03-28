import importlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

mods = [
    'pages_custom.receipt_page',
    'pages_custom.invoice_page',
    'pages_custom.quotation_page',
    'pages_custom.archive_page',
    'pages_custom.reports_page',
    'pages_custom.dashboard_new',
]
for m in mods:
    try:
        importlib.import_module(m)
        print(m + ' OK')
    except Exception as e:
        print(m + ' ERR ->', e)
        raise
