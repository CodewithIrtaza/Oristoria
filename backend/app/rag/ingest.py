"""PDF ingestion: validate, parse, split, embed, store.

Limits (from settings):
  - max_pdf_mb: 5 MB
  - max_pdf_pages: 40 pages
  - max_docs_per_conversation: 3

Implemented in Task 4. Stub with validation helpers here.
"""
from __future__ import annotations

from io import BytesIO

from app.config import settings

PDF_MAGIC = b"%PDF"


def validate_pdf_bytes(data: bytes) -> None:
    """Raise ValueError for oversized, non-PDF, or page-over-limit files."""
    max_bytes = settings.max_pdf_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise ValueError(f"File exceeds {settings.max_pdf_mb} MB limit")
    if not data.startswith(PDF_MAGIC):
        raise ValueError("File does not appear to be a PDF (missing %PDF header)")


def count_pdf_pages(data: bytes) -> int:
    """Return page count using pypdf; raise ValueError if no extractable pages."""
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    page_count = len(reader.pages)
    if page_count > settings.max_pdf_pages:
        raise ValueError(
            f"PDF has {page_count} pages; limit is {settings.max_pdf_pages}"
        )
    return page_count


# TODO Task 4: async def ingest_pdf(data, filename, conversation_id, db_pool, vector_store) -> dict
