from pathlib import Path
from datetime import datetime
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from utils.quotation_utils import render_quotation_html, html_to_pdf
from utils import db
from pages_custom.archive_page import _find_export_html, _load_records


def run():
    now = datetime.now()
    stamp = now.strftime("%Y%m%d%H%M%S")
    base_id = f"E2E-{stamp}"
    q_no = f"QTEST-{stamp}"
    i_no = f"ITEST-{stamp}"
    r_no = f"RTEST-{stamp}"

    exp = Path("data") / "exports"
    exp.mkdir(parents=True, exist_ok=True)

    quote_html = render_quotation_html(
        {
            "company_name": "Newton Smart Home",
            "quotation_number": q_no,
            "quotation_date": now.strftime("%Y-%m-%d"),
            "client_name": "E2E Client",
            "mobile": "0500000000",
            "project_location": "Dubai",
            "project_scope": "E2E scope",
            "items": [{"description": "Test Device", "qty": 1, "unit_price": 1000, "total": 1000, "warranty": "1 year"}],
            "subtotal": 1000,
            "Installation": 100,
            "total_amount": 1100,
            "sig_name": "QA",
            "sig_role": "QA",
        },
        template_name="newton_quotation_A4.html",
    )
    (exp / f"Quotation_E2E_{q_no}.html").write_text(quote_html, encoding="utf-8")

    invoice_html = render_quotation_html(
        {
            "company_name": "Newton Smart Home",
            "quotation_number": i_no,
            "quotation_date": now.strftime("%Y-%m-%d"),
            "client_name": "E2E Client",
            "mobile": "0500000000",
            "project_location": "Dubai",
            "project_title": "E2E Invoice Project",
            "project_description": "E2E invoice description",
            "project_scope": "E2E invoice",
            "power_provider": "DEWA",
            "items": [{"description": "Test Device", "qty": 1, "unit_price": 1100, "total": 1100, "warranty": "1 year"}],
            "subtotal": 1100,
            "Installation": 0,
            "total_amount": 1100,
            "down_payment": 0,
            "previously_paid": 0,
            "balance_due": 1100,
            "warranty_html": "<ul><li>1 year warranty</li></ul>",
            "payment_terms_html": "<ul><li>50% advance</li><li>50% on completion</li></ul>",
            "delivery_text": "Estimated delivery 7-14 days",
            "sig_name": "QA",
            "sig_role": "QA",
        },
        template_name="newton_invoice_A4.html",
    )
    (exp / f"Invoice_{i_no}.html").write_text(invoice_html, encoding="utf-8")

    receipt_html = render_quotation_html(
        {
            "company_name": "Newton Smart Home",
            "quotation_number": i_no,
            "quotation_date": now.strftime("%Y-%m-%d"),
            "client_name": "E2E Client",
            "mobile": "0500000000",
            "project_location": "Dubai",
            "project_scope": "E2E receipt",
            "total_invoice_amount": 1100,
            "amount_paid": 500,
            "remaining_balance": 600,
            "payment_method": "Bank transfer",
            "payment_date": now.strftime("%Y-%m-%d"),
        },
        template_name="newton_receipt_A4.html",
    )
    (exp / f"Receipt_{r_no}.html").write_text(receipt_html, encoding="utf-8")

    pdf_ok = True
    pdf_error = ""
    try:
        _ = html_to_pdf(invoice_html)
    except Exception as e:
        pdf_ok = False
        pdf_error = str(e)

    doc_date = now.strftime("%Y-%m-%d")
    records = [("q", q_no, 1100.0), ("i", i_no, 1100.0), ("r", r_no, 500.0)]
    for t, num, amt in records:
        db.db_execute(
            "INSERT INTO records(base_id, date, type, number, amount, client_name, phone, location, note) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (base_id, doc_date, t, num, amt, "E2E Client", "0500000000", "Dubai", "automated e2e test"),
        )

    assert _find_export_html("q", q_no) is not None
    assert _find_export_html("i", i_no) is not None
    assert _find_export_html("r", r_no) is not None

    loaded = _load_records()
    assert any(loaded["number"].astype(str) == q_no)
    assert any(loaded["number"].astype(str) == i_no)
    assert any(loaded["number"].astype(str) == r_no)

    print("E2E_DATA_OK", base_id, q_no, i_no, r_no, f"PDF_OK={pdf_ok}", f"PDF_ERROR={pdf_error}")


if __name__ == "__main__":
    run()
