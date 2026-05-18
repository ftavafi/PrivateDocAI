import re
import io
import pdfplumber


def extract_text(pdf_bytes: bytes) -> str:
    """Extract and clean text from a PDF byte payload."""
    raw = _extract_raw(pdf_bytes)
    return _clean(raw)


def _extract_raw(pdf_bytes: bytes) -> str:
    pages = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if text:
                pages.append(text)
    return "\n\n".join(pages)


def _clean(text: str) -> str:
    # Collapse runs of spaces/tabs within each line (layout mode leaves many)
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Strip lines that contain only whitespace
    text = re.sub(r"(?m)^[ \t]+$", "", text)
    # Strip lines that are only a page number (standalone digit(s))
    text = re.sub(r"(?m)^\s*\d+\s*$", "", text)
    # Collapse 3+ blank lines into two
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
