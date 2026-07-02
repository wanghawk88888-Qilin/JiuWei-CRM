"""Resume parser service — extracts raw text from docx and pdf files."""

import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_docx(file_path: str) -> str:
    """Extract paragraph text from a .docx file using python-docx.

    Returns the concatenated text of all paragraphs.
    """
    from docx import Document

    doc = Document(file_path)
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def parse_pdf(file_path: str) -> str:
    """Extract text from a PDF file.

    Tries PyMuPDF first; falls back to pdfplumber if available.
    """
    # Try PyMuPDF (fitz) first
    try:
        import fitz  # PyMuPDF

        text_parts: list[str] = []
        with fitz.open(file_path) as doc:
            for page in doc:
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(page_text.strip())
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("PyMuPDF not available, trying pdfplumber")

    # Fallback to pdfplumber
    try:
        import pdfplumber

        text_parts: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(page_text.strip())
        return "\n".join(text_parts)
    except ImportError:
        raise RuntimeError("No PDF parser available. Install PyMuPDF or pdfplumber.")


def parse_resume_text(file_path: str, file_type: str) -> str:
    """Parse resume file and return extracted text.

    Args:
        file_path: Path to the resume file.
        file_type: One of 'docx' or 'pdf'.

    Returns:
        Extracted plain text.

    Raises:
        ValueError: If file_type is unsupported.
        RuntimeError: If parsing fails.
    """
    file_type_lower = file_type.lower().lstrip(".")

    if file_type_lower == "docx":
        return parse_docx(file_path)
    elif file_type_lower == "pdf":
        return parse_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
