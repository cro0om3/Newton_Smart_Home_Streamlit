from typing import Dict, Any
import tempfile
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
import sys
import base64
import mimetypes
from utils.image_utils import ensure_data_url
from utils.template_validator import validate_template, format_mismatch_message


def render_quotation_html(context: Dict[str, Any], template_name: str = "newton_quotation_A4.html") -> str:
    """Render the quotation HTML from given context and template.

    Args:
        context: Data dictionary to pass to the template.
        template_name: Template filename located in `templates/` folder.

    Returns:
        Rendered HTML as string.
    """
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # NOTE: Template validation is performed after we normalize the context
    # (see below). We intentionally avoid validating here because callers may
    # provide keys under alternate names (e.g. `date` / `customer`) which we
    # will map into the template's expected top-level keys.

    # Add a simple currency filter
    def _currency(value, symbol="AED", sep=","):
        try:
            # accept numbers or strings like '1,350.00' or 'AED 1,350.00'
            if isinstance(value, str):
                # strip common currency symbols and spaces
                cleaned = value.replace(symbol, '').replace(',', '').strip()
            else:
                cleaned = value
            v = float(cleaned)
        except Exception:
            return ""
        # Format with two decimals and thousands separator
        formatted = f"{v:,.2f}"
        return f"{symbol} {formatted}"

    env.filters['currency'] = _currency
    template = env.get_template(template_name)
    # Normalize item fields so template can rely on `description`, `qty`, `unit_price`, `total`, `warranty`, `image`
    items = context.get('items', []) or []
    normalized = []
    for it in items:
        if isinstance(it, dict):
            # description mapping (many possible source keys)
            description = (
                it.get('description') or it.get('Description') or it.get('name') or it.get('Product / Device') or it.get('Item')
            )
            # quantity mapping
            qty = (
                it.get('qty') if it.get('qty') is not None else (
                    it.get('Qty') or it.get('Quantity') or it.get('quantity') or 0
                )
            )
            # unit price mapping
            unit_price = (
                it.get('unit_price') if it.get('unit_price') is not None else (
                    it.get('Unit Price (AED)') or it.get('Unit Price') or it.get('unit_price_aed') or it.get('price') or 0
                )
            )
            # total mapping (fallback to qty * unit_price)
            total = (
                it.get('total') if it.get('total') is not None else (
                    it.get('Line Total (AED)') or it.get('Amount') or None
                )
            )
            if total is None:
                try:
                    total = float(qty or 0) * float(unit_price or 0)
                except Exception:
                    total = 0
            # warranty mapping
            warranty = it.get('warranty') or it.get('Warranty') or it.get('Warranty (Years)') or ''
            # image mapping (prefer explicit `image` field, otherwise ImageBase64)
            image = it.get('image') or it.get('Image') or it.get('image_url') or it.get('img') or None
            b64_fallback = it.get('ImageBase64') or it.get('image_base64')

            # Normalize strictly to data URIs only. Do NOT read filesystem paths or accept http(s) URLs.
            try:
                image_candidate = None
                if isinstance(image, str) and image.strip():
                    image_candidate = ensure_data_url(image)
                if not image_candidate and isinstance(b64_fallback, str) and b64_fallback.strip():
                    image_candidate = ensure_data_url(b64_fallback)
                image = image_candidate
            except Exception:
                image = None

            normalized_item = dict(it)  # copy all original keys
            normalized_item.update({
                'description': description or '',
                'qty': qty or 0,
                'unit_price': unit_price or 0,
                'total': total,
                'warranty': warranty,
                'image': image,
            })
            normalized.append(normalized_item)
        else:
            normalized.append({'description': str(it), 'qty': 0, 'unit_price': 0, 'total': 0, 'warranty': '', 'image': None})
    context = dict(context)
    context['items'] = normalized

    # Normalize common top-level key aliases so callers with different key names
    # still validate against templates that expect specific identifiers.
    # Examples: tests use `date`/`customer`, templates expect `quotation_date`/
    # `client_name`/`mobile`.
    client_obj = context.get('client') or context.get('customer') or {}
    context['quotation_date'] = context.get('quotation_date') or context.get('date', '')
    context['quotation_number'] = context.get('quotation_number') or context.get('quote_no') or context.get('number', '')
    if isinstance(client_obj, dict):
        context['client_name'] = context.get('client_name') or client_obj.get('name') or client_obj.get('client_name') or ''
        context['mobile'] = context.get('mobile') or context.get('phone') or client_obj.get('phone') or ''
        context['project_location'] = context.get('project_location') or context.get('client_address') or client_obj.get('address') or ''
    else:
        context['client_name'] = context.get('client_name') or (str(client_obj) if client_obj else '')
        context['mobile'] = context.get('mobile') or context.get('phone', '')
        context['project_location'] = context.get('project_location') or context.get('client_address', '')
    context['project_scope'] = context.get('project_scope') or context.get('project_title') or context.get('project_notes', '') or ''
    context['valid_until'] = context.get('valid_until') or ''

    # Compute subtotal if not provided: sum of item totals
    if 'subtotal' not in context or context.get('subtotal') in (None, ''):
        try:
            context['subtotal'] = sum(float(it.get('total', 0) or 0) for it in normalized)
        except Exception:
            context['subtotal'] = 0

    # Accept Installation value from context if provided; normalize keys
    if 'Installation' not in context and 'installation' in context:
        context['Installation'] = context.get('installation')

    # Compute total_amount if missing: subtotal + Installation (numeric)
    if 'total_amount' not in context or context.get('total_amount') in (None, ''):
        try:
            inst = float(context.get('Installation') or 0)
        except Exception:
            inst = 0
        try:
            subtotal_val = float(context.get('subtotal') or 0)
        except Exception:
            subtotal_val = 0
        context['total_amount'] = subtotal_val + inst

    # Now validate template placeholders against the prepared context so we can
    # surface clear mismatches while allowing callers to supply common aliases.
    try:
        tpl_path = templates_dir / template_name
        missing, extra = validate_template(tpl_path, context)
        # Be permissive about extra keys (callers often pass more data than a
        # template needs). Only fail when required placeholders are missing.
        if missing:
            raise ValueError(f"Template placeholders mismatch for {template_name}: {format_mismatch_message(missing, extra)}")
    except Exception:
        raise

    html = template.render(**context)
    return html


def html_to_pdf(html_str: str, output_path: str | None = None) -> bytes:
    """Convert HTML string to PDF bytes using WeasyPrint.

    Args:
        html_str: HTML content to convert.
        output_path: Optional filesystem path to save the PDF. If not provided,
            the PDF bytes are returned and no file is written.

    Returns:
        PDF content as bytes.
    """
    # Preferred: use WeasyPrint (local). If unavailable, attempt ConvertAPI fallback
    try:
        from weasyprint import HTML
        if output_path:
            HTML(string=html_str).write_pdf(output_path)
            return Path(output_path).read_bytes()
        else:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            HTML(string=html_str).write_pdf(tmp_path)
            data = tmp_path.read_bytes()
            try:
                tmp_path.unlink()
            except Exception:
                pass
            return data
    except Exception:
        # Fallback #1: Try a local Playwright headless-converter script (chromium)
        try:
            # Write temporary HTML file
            with tempfile.TemporaryDirectory() as tmpdir:
                html_path = Path(tmpdir) / "tmp_quotation.html"
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_str)
                # Run the repository's convert_with_playwright.py script if available
                script = Path(__file__).resolve().parents[1] / 'scripts' / 'convert_with_playwright.py'
                if script.exists():
                    # Use same pixel sizes as template if provided via env, else don't pass sizes
                    vw = os.environ.get('PLAYWRIGHT_PDF_WIDTH')
                    vh = os.environ.get('PLAYWRIGHT_PDF_HEIGHT')
                    cmd = [sys.executable, str(script), str(html_path)]
                    if vw and vh:
                        cmd.extend([str(int(vw)), str(int(vh))])
                    import subprocess
                    subprocess.run(cmd, check=True)
                    out_pdf = html_path.parent / f"{html_path.stem}.pdf"
                    if out_pdf.exists():
                        pdf_bytes = out_pdf.read_bytes()
                        if output_path:
                            with open(output_path, 'wb') as f:
                                f.write(pdf_bytes)
                        return pdf_bytes
        except Exception:
            # If Playwright fallback fails, continue to next fallback
            pass

        # Fallback #2: ConvertAPI (only if user has explicitly set CONVERTAPI_SECRET)
        import os
        key = os.environ.get("CONVERTAPI_SECRET")
        if not key:
            raise RuntimeError("PDF conversion is unavailable.")
        try:
            import convertapi
            convertapi.api_credentials = key
            # converthtml via ConvertAPI: pass HTML as file by writing tmp .html
            with tempfile.TemporaryDirectory() as tmpdir:
                html_path = Path(tmpdir) / "temp.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_str)
                result = convertapi.convert(
                    'pdf',
                    {
                        'File': str(html_path),
                        'FileName': 'quotation'
                    },
                    from_format='html'
                )
                saved = result.save_files(tmpdir)
                if not saved:
                    raise RuntimeError('ConvertAPI returned no files')
                pdf_path = saved[0]
                with open(pdf_path, 'rb') as pf:
                    pdf_bytes = pf.read()
                if output_path:
                    with open(output_path, 'wb') as f:
                        f.write(pdf_bytes)
                return pdf_bytes
        except Exception as e:
            raise RuntimeError("Failed to convert HTML to PDF (weasyprint missing and all fallbacks failed).") from e
