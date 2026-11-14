"""Unit tests for PDF ingestion validation and processing."""
from __future__ import annotations

import pytest

from app.rag.ingest import validate_pdf_bytes, count_pdf_pages


class TestValidatePdfBytes:
    """Tests for validate_pdf_bytes function."""

    def test_rejects_oversize_file(self):
        """Files larger than max_pdf_mb should raise ValueError."""
        from app.config import settings
        max_bytes = settings.max_pdf_mb * 1024 * 1024
        oversized = b"%PDF-1.4\n" + b"x" * (max_bytes + 1)
        with pytest.raises(ValueError, match=r"exceeds.*MB limit"):
            validate_pdf_bytes(oversized)

    def test_rejects_non_pdf_magic_bytes(self):
        """Files without %PDF header should raise ValueError."""
        not_a_pdf = b"not a pdf file"
        with pytest.raises(ValueError, match=r"missing %PDF header"):
            validate_pdf_bytes(not_a_pdf)

    def test_accepts_valid_pdf_header(self):
        """Valid PDF header should pass validation."""
        valid_pdf = b"%PDF-1.4\n%content"
        # Should not raise
        validate_pdf_bytes(valid_pdf)

    def test_rejects_empty_file(self):
        """Empty files should raise ValueError (no magic bytes)."""
        with pytest.raises(ValueError, match=r"missing %PDF header"):
            validate_pdf_bytes(b"")


class TestCountPdfPages:
    """Tests for count_pdf_pages function."""

    def test_rejects_too_many_pages(self, tmp_path):
        """PDFs exceeding max_pdf_pages should raise ValueError."""
        from app.config import settings
        from pypdf import PdfWriter

        # Create a PDF with more pages than allowed
        writer = PdfWriter()
        for _ in range(settings.max_pdf_pages + 1):
            writer.add_blank_page(width=72, height=72)

        import io
        buffer = io.BytesIO()
        writer.write(buffer)
        pdf_bytes = buffer.getvalue()

        with pytest.raises(ValueError, match=r"pages; limit is"):
            count_pdf_pages(pdf_bytes)

    def test_returns_page_count_for_valid_pdf(self, tmp_path):
        """Valid PDF should return correct page count."""
        from pypdf import PdfWriter
        import io

        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.add_blank_page(width=72, height=72)
        writer.add_blank_page(width=72, height=72)

        buffer = io.BytesIO()
        writer.write(buffer)
        pdf_bytes = buffer.getvalue()

        count = count_pdf_pages(pdf_bytes)
        assert count == 3