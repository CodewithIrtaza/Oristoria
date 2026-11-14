"""PDF ingestion: validate, parse, split, embed, store.

Limits (from settings):
  - max_pdf_mb: 5 MB
  - max_pdf_pages: 40 pages
  - max_docs_per_conversation: 3
"""
from __future__ import annotations

import uuid
from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool

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


async def extract_pdf_text_by_page(data: bytes) -> list[tuple[int, str]]:
    """Extract text from each page of the PDF.

    Returns list of (page_number, text) tuples. Page numbers are 1-indexed.
    Raises ValueError if total extractable text is empty (scanned PDF).
    """
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    results: list[tuple[int, str]] = []
    total_text = ""

    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            results.append((i, text))
            total_text += text

    if not total_text.strip():
        raise ValueError("PDF appears to be scanned (no extractable text)")

    return results


async def chunk_text_by_page(
    pages: list[tuple[int, str]],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[tuple[int, str]]:
    """Split page text into overlapping chunks using recursive splitter.

    Returns list of (page_number, chunk_text) tuples.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks: list[tuple[int, str]] = []
    for page_num, text in pages:
        page_chunks = splitter.split_text(text)
        for chunk in page_chunks:
            chunks.append((page_num, chunk))

    return chunks


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using local sentence-transformers model.

    Uses all-MiniLM-L6-v2 (384 dimensions) for fast local inference.
    """
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings.tolist()


async def ingest_pdf(
    data: bytes,
    filename: str,
    conversation_id: uuid.UUID,
    pool: "AsyncConnectionPool",
) -> dict:
    """Full PDF ingestion pipeline: validate -> extract -> chunk -> embed -> store.

    Returns dict with document metadata including chunk_count and page_count.
    """
    # Step 1: Validate
    validate_pdf_bytes(data)
    page_count = count_pdf_pages(data)

    # Step 2: Check document limit per conversation
    from app.db.repositories import ConversationRepository
    repo = ConversationRepository(pool)
    doc_count = await repo.count_documents(conversation_id)
    if doc_count >= settings.max_docs_per_conversation:
        raise ValueError(
            f"Maximum {settings.max_docs_per_conversation} documents per conversation reached"
        )

    # Step 3: Extract text by page
    pages = await extract_pdf_text_by_page(data)

    # Step 4: Chunk text
    chunks = await chunk_text_by_page(pages)

    # Step 5: Generate embeddings
    chunk_texts = [c[1] for c in chunks]
    embeddings = await generate_embeddings(chunk_texts)

    # Step 6: Store in database (documents + doc_chunks)
    document_id = uuid.uuid4()
    async with pool.connection() as conn:
        # Insert document record
        await conn.execute(
            """
            insert into documents (id, conversation_id, filename, size_bytes, page_count, chunk_count, status)
            values (%s, %s, %s, %s, %s, %s, 'ready')
            """,
            (
                document_id,
                conversation_id,
                filename,
                len(data),
                page_count,
                len(chunks),
            ),
        )

        # Insert chunks with embeddings
        for i, ((page_num, text), embedding) in enumerate(zip(chunks, embeddings)):
            await conn.execute(
                """
                insert into doc_chunks (id, thread_id, document_id, page, content, embedding)
                values (%s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid.uuid4(),
                    conversation_id,
                    document_id,
                    page_num,
                    text,
                    embedding,
                ),
            )

    return {
        "id": str(document_id),
        "filename": filename,
        "size_bytes": len(data),
        "page_count": page_count,
        "chunk_count": len(chunks),
        "status": "ready",
    }