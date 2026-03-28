import streamlit as st
import pandas as pd
from datetime import datetime
from utils.quotation_utils import render_quotation_html
from utils.settings import load_settings
HAVE_PYDOCX = True
try:
    from docx import Document
except Exception:
    HAVE_PYDOCX = False
    Document = None
from io import BytesIO
try:
    from utils import db as _db
except Exception:
    _db = None


def receipt_app():

    # ===== Helpers shared with Invoice/Quotation =====
    def proper_case(text):
        if not text:
            return ""
        try:
            return str(text).title().strip()
        except Exception:
            return text

    def format_phone_input(raw_input):
        if not raw_input:
            return None
        digits = ''.join(filter(str.isdigit, str(raw_input)))
        if digits.startswith("0"):
            digits = digits[1:]
        if digits.startswith("5") and len(digits) == 9:
            return f"+971 {digits[:2]} {digits[2:5]} {digits[5:]}"
        return None

    def phone_flat10(raw_input):
        if raw_input is None:
            return ""
        digits = ''.join(filter(str.isdigit, str(raw_input)))
        if not digits:
            return ""
        if digits.startswith('971') and len(digits) >= 12 and digits[3] == '5':
            return '0' + digits[3:12]
        if len(digits) == 9 and digits.startswith('5'):
            return '0' + digits
        if len(digits) == 10 and digits.startswith('05'):
            return digits
        return digits[-10:]

    def phone_label_mask(raw_input):
        flat = phone_flat10(raw_input)
        return f"{flat} xxxxxxxxxx" if flat else "xxxxxxxxxx"

    # =====================================
    # HELPERS
    # =====================================
    def load_records():
        if _db is not None:
            try:
                rows = _db.db_query(
                    'SELECT base_id, date, type, number, amount, client_name, phone, location, note FROM records ORDER BY date')
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
                "base_id", "date", "type", "number", "amount",
                "client_name", "phone", "location", "note"
            ])

    def save_record(rec):
        # Try DB first then fallback to Excel
        if _db is not None:
            try:
                if rec.get('type') and rec.get('number'):
                    try:
                        _db.db_execute('DELETE FROM records WHERE type = %s AND number = %s', (rec.get(
                            'type'), rec.get('number')))
                    except Exception:
                        pass
                _db.db_execute('INSERT INTO records(base_id, date, type, number, amount, client_name, phone, location, note) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                               (rec.get('base_id'), rec.get('date'), rec.get('type'), rec.get('number'), rec.get('amount'), rec.get('client_name'), rec.get('phone'), rec.get('location'), rec.get('note')))
                return
            except Exception:
                pass

        df = load_records()
        if not df.empty and {"type", "number"}.issubset(df.columns):
            df = df[~((df["type"] == rec.get("type")) &
                      (df["number"] == rec.get("number")))]
        df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
        if {"type", "number"}.issubset(df.columns):
            df = df.drop_duplicates(subset=["type", "number"], keep="last")
        df.to_excel("data/records.xlsx", index=False)

    # =====================================
    # WORD TEMPLATE ONLY (pdfkit removed)
    # =====================================
    def generate_word(template, data_dict):
        if not HAVE_PYDOCX or Document is None:
            raise RuntimeError("Word export is unavailable because python-docx is not installed.")
        doc = Document(template)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for k, v in data_dict.items():
                        if k in cell.text:
                            cell.text = cell.text.replace(
                                k, "" if v is None else str(v))

        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

    # =====================================
    # THEME
    # Inherit global Invoice theme from main.py to keep design consistent
    # (No page-level overrides needed)

    # =====================================
    # LOAD DATABASE
    # =====================================
    records = load_records()
    if "amount" in records.columns:
        records["amount"] = pd.to_numeric(records["amount"], errors="coerce").fillna(0.0)
    invoices_df = records[records["type"] == "i"].copy()
    invoice_list = invoices_df["number"].astype(str).tolist()

    # =====================================
    # RECEIPT UI
    # =====================================
    st.markdown("<div class='section-title'>Receipt Summary</div>",
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        # Rich labels for type-to-search
        if not invoices_df.empty:
            df = invoices_df.fillna("")
            numbers = df["number"].astype(str).tolist()
            labels = {}
            for _, row in df.iterrows():
                labels[str(
                    row["number"])] = f"{row['number']}  |  {row.get('client_name','')}  |  {phone_label_mask(row.get('phone',''))}"
            selected_invoice = st.selectbox(
                "Select Invoice",
                options=numbers if numbers else ["No invoices"],
                key="rcpt_invoice_select",
                format_func=lambda n: labels.get(n, n),
            )
        else:
            selected_invoice = None

    with c2:
        today = datetime.today().strftime('%Y%m%d')
        st.text_input("Receipt Date", value=datetime.today().strftime(
            '%Y-%m-%d'), disabled=True)

    if selected_invoice:

        inv = records[records["number"] == selected_invoice].iloc[0]

        base_id = inv["base_id"]

        # New numbering system: RYYYY#### (e.g., R20260001)
        current_year = datetime.today().year
        if 'number_str' in records.columns:
            number_str = records['number_str']
        else:
            number_str = records['number'].astype(str)
        year_receipts = records[(records['type'] == 'r') & (number_str.str.startswith(f'R{current_year}'))]
        next_seq = len(year_receipts) + 1
        receipt_no = f"R{current_year}{str(next_seq).zfill(4)}"

        st.markdown("---")
        st.markdown(
            "<div class='section-title'>Client Information</div>", unsafe_allow_html=True)

        st.write(f"**Client Name:** {proper_case(inv.get('client_name',''))}")
        pretty_phone = format_phone_input(
            inv.get('phone', '')) or inv.get('phone', '')
        st.write(f"**Phone:** {pretty_phone}")
        st.write(f"**Location:** {proper_case(inv.get('location',''))}")
        invoice_total = float(pd.to_numeric(inv.get("amount", 0), errors="coerce") or 0.0)
        st.write(f"**Invoice Total:** {invoice_total:.2f} AED")

        st.markdown("---")

        # Previous payments and summary
        prev_receipts = records[(records["base_id"] == base_id) & (
            records["type"] == "r")]
        previous_paid_total = float(pd.to_numeric(prev_receipts["amount"], errors="coerce").fillna(0.0).sum()) if not prev_receipts.empty else 0.0

        st.markdown("---")
        col_left, col_right = st.columns([1, 1])

        with col_right:
            st.markdown("<div class='section-title'>Payment</div>",
                        unsafe_allow_html=True)
            max_allowed = max(invoice_total - previous_paid_total, 0.0)
            payment = st.number_input(
                "Payment Amount (AED)",
                min_value=0.0,
                max_value=float(max_allowed),
                key="rcpt_payment"
            )
            if payment > max_allowed:
                st.warning(
                    "Entered payment exceeds remaining balance; capped.")
                payment = max_allowed
            total_paid_after = previous_paid_total + payment
            remaining = invoice_total - total_paid_after
            st.metric("Remaining Balance", f"{remaining:,.2f} AED")

        with col_left:
            st.markdown(
                "<div class='section-title'>Payment Summary</div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style='background:#fff;border:1px solid rgba(0,0,0,.08);border-radius:12px;padding:16px;box-shadow:0 2px 6px rgba(0,0,0,.04);'>
                    <div style='display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,0,0,.06);'>
                        <span style='font-weight:600;color:#6e6e73;'>Invoice Total</span>
                        <span style='font-weight:700;color:#1d1d1f;'>{invoice_total:,.2f} AED</span>
                    </div>
                    <div style='display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,0,0,.06);'>
                        <span style='font-weight:600;color:#6e6e73;'>Previous Payments</span>
                        <span style='font-weight:700;color:#1d1d1f;'>{previous_paid_total:,.2f} AED</span>
                    </div>
                    <div style='display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,0,0,.06);'>
                        <span style='font-weight:600;color:#6e6e73;'>Current Payment</span>
                        <span style='font-weight:700;color:#1d1d1f;'>{payment:,.2f} AED</span>
                    </div>
                    <div style='display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,0,0,.06);'>
                        <span style='font-weight:600;color:#6e6e73;'>Total Paid</span>
                        <span style='font-weight:700;color:#1d1d1f;'>{total_paid_after:,.2f} AED</span>
                    </div>
                    <div style='display:flex;justify-content:space-between;padding:12px 0;background:rgba(0,0,0,.02);margin-top:8px;border-radius:8px;padding-left:12px;padding-right:12px;'>
                        <span style='font-weight:700;font-size:15px;color:#1d1d1f;'>Remaining</span>
                        <span style='font-weight:700;font-size:17px;color:#1d1d1f;'>{remaining:,.2f} AED</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # History list
            if not prev_receipts.empty:
                st.markdown(
                    "<div style='margin-top:14px;font-weight:600;color:#6e6e73;'>Previous Receipts</div>", unsafe_allow_html=True)
                for _, r in prev_receipts.sort_values("date", ascending=False).iterrows():
                    st.markdown(
                        f"<div style='font-size:13px;padding:4px 0;border-bottom:1px dashed rgba(0,0,0,.08);'>"
                        f"{r['number']} — {r['amount']:,.2f} AED</div>",
                        unsafe_allow_html=True,
                    )

        st.markdown("---")

        # Prepare data for exports
        data = {
            "{{client_name}}": inv.get("client_name", ""),
            "{{invoice_no}}": selected_invoice,
            "{{receipt_no}}": receipt_no,
            "{{client_phone}}": (format_phone_input(inv.get("phone", "")) or inv.get("phone", "")),
            "{{client_location}}": inv.get("location", ""),
            "{{amount}}": f"{payment:,.2f}",
            "{{balance}}": f"{remaining:,.2f}",
        }

        try:
            # Primary export path: HTML + Save (same behavior as quotation/invoice)
            html_receipt = render_quotation_html({
                'company_name': load_settings().get('company_name', 'Newton Smart Home'),
                'quotation_number': selected_invoice,
                'quotation_date': inv.get('date', datetime.today().strftime('%Y-%m-%d')),
                'client_name': inv.get('client_name', ''),
                'mobile': (format_phone_input(inv.get('phone', '')) or inv.get('phone', '')),
                'project_location': proper_case(inv.get('location', '')),
                'project_scope': f"Payment receipt for invoice {selected_invoice}",
                'items': [],
                'total_invoice_amount': invoice_total,
                'amount_paid': payment,
                'payment_method': 'Cash',
                'payment_date': datetime.today().strftime('%Y-%m-%d'),
                'remaining_balance': remaining,
            }, template_name='newton_receipt_A4.html')

            clicked_html = st.download_button(
                label="💾 Save & Download Receipt (HTML)",
                data=html_receipt,
                file_name=f"Receipt_{receipt_no}.html",
                mime='text/html',
                use_container_width=True,
                type="primary",
                key=f"save_dl_rcpt_{receipt_no}"
            )

            # Optional Word export (download only, does not affect save flow)
            if HAVE_PYDOCX:
                word_file = generate_word("data/receipt_template.docx", data)
                st.download_button(
                    label="Download Receipt (Word)",
                    data=word_file,
                    file_name=f"Receipt_{receipt_no}.docx",
                    key=f"dl_word_rcpt_{receipt_no}"
                )
            else:
                st.caption("Word export unavailable (python-docx missing).")
        except Exception as e:
            st.warning(f"Unable to prepare receipt HTML: {e}")
            clicked_html = False

        if clicked_html:
            try:
                save_record({
                    "base_id": base_id,
                    "date": datetime.today().strftime('%Y-%m-%d'),
                    "type": "r",
                    "number": receipt_no,
                    "amount": payment,
                    "client_name": inv.get("client_name", ""),
                    "phone": inv.get("phone", ""),
                    "location": inv.get("location", ""),
                    "note": ""
                })

                # Save HTML file locally for archive page retrieval
                from pathlib import Path
                out_dir = Path('data') / 'exports'
                out_dir.mkdir(parents=True, exist_ok=True)
                html_path = out_dir / f"Receipt_{receipt_no}.html"
                with open(html_path, 'w', encoding='utf-8') as fh:
                    fh.write(html_receipt)

                st.success(f"✅ Saved receipt {receipt_no}")
            except Exception as e:
                st.warning(f"⚠️ Downloaded, but failed to save record: {e}")
