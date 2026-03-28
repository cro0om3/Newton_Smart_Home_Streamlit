"""
Extract client name, phone, location, and total amount from Newton invoice/quotation PDFs.
Handles spaced-out headings (e.g. C L I E N T  I N F O) from some renderers.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict


def _money(s: str) -> float:
    s = (s or "").replace(",", "").strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _pdf_text(path: Path) -> str:
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    try:
        parts = []
        for page in doc:
            parts.append(page.get_text("text") or "")
        return "\n".join(parts)
    finally:
        doc.close()


# Spaced ALLCAPS labels as produced by some PDF generators
_CLIENT_INFO = r"(?:C\s+L\s+I\s+E\s+N\s+T\s+I\s+N\s+F\s+O|CLIENT\s+INFO|Client\s+info)"
_TOTAL_INV = r"(?:T\s+O\s+T\s+A\s+L\s+I\s+N\s+V\s+O\s+I\s+C\s+E\s+A\s+M\s+O\s+U\s+N\s+T|Total\s+Invoice\s+Amount)"
_TOTAL_AMT = r"(?:T\s+O\s+T\s+A\s+L\s+A\s+M\s+O\s+U\s+N\s+T|Total\s+Amount)"


def extract_fields_from_pdf(path: Path) -> Dict[str, Any]:
    """
    Returns keys: client_name, phone, location, amount (float), text_ok (bool).
    """
    out: Dict[str, Any] = {
        "client_name": "",
        "phone": "",
        "location": "",
        "amount": 0.0,
        "text_ok": False,
    }
    try:
        text = _pdf_text(path)
    except Exception:
        return out

    if not text or len(text.strip()) < 30:
        return out

    out["text_ok"] = True
    t = text.replace("\r", "\n")

    # --- Client: line(s) immediately after CLIENT INFO, stop before Mobile/Location/PROJECT ---
    m = re.search(
        rf"{_CLIENT_INFO}\s*\n+([^\n]+)(?:\n+([^\n]+))?",
        t,
        re.I,
    )
    if m:
        line1 = m.group(1).strip()
        line2 = (m.group(2) or "").strip()
        skip = re.compile(r"^(Mobile|Location|Project|P\s+R\s+O|Q\s+U\s+O)", re.I)

        def _take_name(s: str) -> str:
            s = re.sub(r"^Client\s*Name:\s*", "", s, flags=re.I).strip()
            if not s or s.lower() in ("nan", "none"):
                return ""
            if "{" in s or "}}" in s or "client_name" in s.lower():
                return ""
            # Drop obvious template / garbage lines
            if len(s) > 120 or s.count("$") >= 1:
                return ""
            letters = sum(1 for c in s if c.isalpha())
            if letters > 0 and letters / max(len(s), 1) < 0.25:
                return ""
            return s[:200]

        n1 = _take_name(line1) if line1 and not skip.match(line1) else ""
        n2 = _take_name(line2) if line2 and not skip.match(line2) else ""
        if n1:
            out["client_name"] = n1
        elif n2 and line1.lower().startswith("mobile"):
            out["client_name"] = n2

    # --- Phone ---
    pm = re.search(
        r"Mobile:\s*([+0-9][\d\s\-\u00a0\u200f]{5,35})",
        t,
        re.I,
    )
    if pm:
        out["phone"] = re.sub(r"\s+", " ", pm.group(1).strip())[:60]
    if not out["phone"]:
        pm2 = re.search(
            r"Mobile:\s*\n+\s*([+0-9][\d\s\-]{5,35})",
            t,
            re.I,
        )
        if pm2:
            out["phone"] = re.sub(r"\s+", " ", pm2.group(1).strip())[:60]

    # --- Location ---
    lm = re.search(r"Location:\s*([^\n]+)", t, re.I)
    if lm:
        loc = lm.group(1).strip()[:200]
        if "{" not in loc and "}}" not in loc:
            out["location"] = loc

    # --- Amount: prefer invoice total, then quotation total ---
    amount = 0.0
    for pat in (
        rf"{_TOTAL_INV}\s*\n+\s*AED\s*([\d,]+\.?\d*)",
        rf"{_TOTAL_AMT}\s*\n+\s*AED\s*([\d,]+\.?\d*)",
        rf"{_TOTAL_INV}\s+AED\s*([\d,]+\.?\d*)",
        rf"{_TOTAL_AMT}\s+AED\s*([\d,]+\.?\d*)",
        r"Balance\s+Due\s*\n+\s*AED\s*([\d,]+\.?\d*)",
        r"Balance\s+Due\s+AED\s*([\d,]+\.?\d*)",
        r"Total\s+Invoice\s+Amount\s*AED\s*([\d,]+\.?\d*)",
        r"Total\s+Amount\s*AED\s*([\d,]+\.?\d*)",
    ):
        mm = re.search(pat, t, re.I)
        if mm:
            amount = max(amount, _money(mm.group(1)))

    # Fallback: last "AED 9,999.00" in totals section (avoid tiny warranty fees)
    if amount <= 0:
        candidates = []
        for mm in re.finditer(r"AED\s*([\d,]+\.?\d{0,2})\b", t, re.I):
            v = _money(mm.group(1))
            if 10 <= v <= 99_999_999:
                candidates.append(v)
        if candidates:
            # Prefer values that look like document totals (often among largest)
            amount = max(candidates)

    out["amount"] = round(amount, 2)
    return out


def merge_pdf_into_row(path: Path, row: dict) -> None:
    """
    Update row dict in place: amount, client_name, phone, location from PDF.
    Filename hints in row are kept when PDF has no client line.
    """
    try:
        ex = extract_fields_from_pdf(path)
    except Exception:
        return
    if ex.get("amount", 0) and ex["amount"] > 0:
        row["amount"] = float(ex["amount"])
    cn = (ex.get("client_name") or "").strip()
    if "{" in cn or "project_location" in cn.lower():
        cn = ""
    if cn:
        row["client_name"] = cn[:200]
    else:
        prev = str(row.get("client_name") or "")
        if prev and (
            "{" in prev
            or prev.strip().lower() in ("nan", "none")
            or "$" in prev
        ):
            row["client_name"] = "-"
        if row.get("client_name") in ("-", "", None) and ex.get("location"):
            row["client_name"] = f"Client · {ex['location']}"[:200]
    if ex.get("phone"):
        row["phone"] = str(ex["phone"])[:60]
    if ex.get("location"):
        row["location"] = str(ex["location"])[:200]
