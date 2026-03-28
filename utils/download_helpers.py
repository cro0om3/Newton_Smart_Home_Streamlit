def auto_download_bytes(data_bytes: bytes, filename: str, mime: str = "application/octet-stream") -> str:
    """Return an HTML snippet that triggers a single-click download of `data_bytes`.

    Usage in Streamlit:
        st.markdown(auto_download_bytes(bytes_data, "file.html", "text/html"), unsafe_allow_html=True)

    The returned HTML contains a small script that creates a blob URL and auto-clicks
    a temporary anchor to start the download. If JS is disabled, a visible link is provided.
    """
    import base64
    b64 = base64.b64encode(data_bytes).decode("ascii")
    safe_name = filename.replace('"', '').replace("'", "")
    html = (
        f"<a id=dl href=\"data:{mime};base64,{b64}\" download=\"{safe_name}\">Download</a>"
        "<script>"
        "(function(){var a=document.getElementById('dl'); if(!a) return; a.click();})();"
        "</script>"
    )
    return html
import base64
from streamlit.components.v1 import html as st_html
from pathlib import Path
from typing import Optional


def auto_download_bytes(data_bytes: bytes, filename: str, mime: str):
    """Trigger a one-click auto-download in Streamlit using an embedded JS snippet.

    This writes a small anchor and simulates a click. If the browser blocks it, the
    function also prints a visible fallback link.
    """
    b64 = base64.b64encode(data_bytes).decode('utf-8')
    # Visible fallback link (in case browser blocks auto-download)
    from streamlit import markdown
    markdown(
        f"If the download didn't start, click here: [Download {filename}](data:{mime};base64,{b64})",
        unsafe_allow_html=True,
    )
    js = (
        "<script>"
        "(function(){"
        f"const b64='{b64}';"
        f"const mime='{mime}';"
        "const byteChars=atob(b64);"
        "const byteNumbers=new Array(byteChars.length);"
        "for(let i=0;i<byteChars.length;i++)byteNumbers[i]=byteChars.charCodeAt(i);"
        "const byteArray=new Uint8Array(byteNumbers);"
        "const blob=new Blob([byteArray],{type:mime});"
        "const url=URL.createObjectURL(blob);"
        "const a=document.createElement('a');a.href=url;"
        f"a.download='{filename}';"
        "document.body.appendChild(a);a.click();"
        "setTimeout(function(){URL.revokeObjectURL(url);a.remove();},1000);"
        "})();</script>"
    )
    st_html(js, height=0)
