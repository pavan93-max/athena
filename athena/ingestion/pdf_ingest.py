"""Utilities for extracting text from PDF files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class PageText:
    page: int
    text: str


def _extract_with_pymupdf(path: str) -> List[PageText]:
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    try:
        pages: List[PageText] = []
        for page in doc:
            text = page.get_text("text").strip()
            if text:
                pages.append(PageText(page=page.number + 1, text=text))
        return pages
    finally:
        doc.close()


def _extract_with_pypdf(path: str) -> List[PageText]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages: List[PageText] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = text.strip()
        if text:
            pages.append(PageText(page=i + 1, text=text))
    return pages


def extract_pdf_text(path: str) -> List[Dict[str, Optional[str]]]:
    """Extract text from each page of a PDF.

    Args:
        path: Filesystem path to the PDF document.

    Returns:
        List of dictionaries ``{"page": int, "text": str}``.
    """

    extractors = [_extract_with_pymupdf, _extract_with_pypdf]

    last_error: Optional[Exception] = None
    for extractor in extractors:
        try:
            pages = extractor(path)
            if pages:
                return [page.__dict__ for page in pages]
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if last_error:
        raise RuntimeError(f"Failed to extract PDF text from {path}: {last_error}")

    return []
