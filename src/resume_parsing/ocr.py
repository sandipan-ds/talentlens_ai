"""OCR utilities for extracting text from image-based PDFs.

This module provides a *hybrid* text extractor:

1. Try ``pdfplumber`` to read selectable text from the PDF.
2. If no text is extractable (image-only / scanned PDF), fall back to OCR by
   rendering pages to images and running Tesseract.

PDF page rendering uses ``pypdfium2`` by default. ``pypdfium2`` is bundled with
a self-contained PDFium binary, so it does NOT require Poppler to be installed
on the host. If ``pypdfium2`` is unavailable, the legacy ``pdf2image`` path
(Poppler) is attempted, raising an informative error if neither renderer is
present.
"""

import io
from pathlib import Path
from typing import List, Optional

import pytesseract
from PIL import Image


# ---------------------------------------------------------------------------
# PDF -> PIL Image rendering
#
# We try ``pypdfium2`` first because it ships with a PDFium binary and avoids
# the Poppler system dependency. ``pdf2image`` (which DOES require Poppler) is
# kept as a fallback for backward compatibility.
# ---------------------------------------------------------------------------

def _render_with_pypdfium2(pdf_path: Path, dpi: int) -> Optional[List[Image.Image]]:
    """Render PDF pages to PIL images using pypdfium2. Returns None on failure."""
    try:
        import pypdfium2 as pdfium
    except ModuleNotFoundError:
        return None
    try:
        pdf = pdfium.PdfDocument(str(pdf_path))
        # 72 DPI is the PDF default; scale so we get roughly ``dpi`` output.
        scale = max(1.0, dpi / 72.0)
        images: List[Image.Image] = []
        for page_index in range(len(pdf)):
            page = pdf[page_index]
            pil_image = page.render(scale=scale).to_pil()
            images.append(pil_image)
        return images
    except Exception:
        return None


def _render_with_pdf2image(pdf_path: Path, dpi: int) -> List[Image.Image]:
    """Render PDF pages to PIL images using pdf2image (requires Poppler)."""
    try:
        from pdf2image import convert_from_path
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "pdf2image is not installed. Install with `pip install pdf2image`, "
            "or install `pypdfium2` (no Poppler required)."
        ) from exc
    return convert_from_path(str(pdf_path), dpi=dpi)


def pdf_to_images(pdf_path: Path, dpi: int = 300) -> List[Image.Image]:
    """Convert PDF pages to PIL Images using the best available renderer."""
    images = _render_with_pypdfium2(pdf_path, dpi)
    if images is not None:
        return images
    return _render_with_pdf2image(pdf_path, dpi)


def extract_text_from_image(image: Image.Image) -> str:
    """Extract text from a single image using Tesseract OCR."""
    return pytesseract.image_to_string(image)


def extract_text_from_pdf_ocr(pdf_path: Path) -> str:
    """Extract text from a PDF using OCR (for scanned/image-based PDFs)."""
    images = pdf_to_images(pdf_path)
    text_parts: List[str] = []
    for i, img in enumerate(images):
        text = extract_text_from_image(img)
        if text.strip():
            text_parts.append(f"[--- Page {i+1} ---\n{text}")
    return "\n".join(text_parts)


def is_pdf_text_extractable(pdf_path: Path) -> bool:
    """Check if a PDF has extractable text (vs being scanned/image-only)."""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    return True
        return False
    except Exception:
        return False


def extract_text_hybrid(pdf_path: Path) -> str:
    """Extract text using pdfplumber first, fall back to OCR if needed."""
    # 1) Try selectable-text extraction via pdfplumber.
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            text_parts: List[str] = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(f"[--- Page {i+1} ---\n{text}")
            extracted = "\n".join(text_parts)
            if extracted.strip():
                return extracted
    except Exception:
        pass

    # 2) Fall back to OCR. Surface a clear error if neither renderer works.
    try:
        return extract_text_from_pdf_ocr(pdf_path)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Text extraction from this PDF failed and OCR fallback is unavailable. "
            "Install `pypdfium2` (recommended, no Poppler required) with "
            "`pip install pypdfium2`, or install Poppler + `pdf2image`."
        ) from exc