"""Document upload, list, and delete endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from psycopg_pool import AsyncConnectionPool

from app.api.conversations import get_conversation_or_404
from app.config import settings
from app.core.anon_id import get_anon_id
from app.db.repositories import ConversationRepository
from app.rag.ingest import ingest_pdf, validate_pdf_bytes

router = APIRouter(tags=["documents"])

MAX_UPLOAD_SIZE = settings.max_pdf_mb * 1024 * 1024


def _pool(request: Request) -> AsyncConnectionPool:
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(status_code=500, detail="Database pool not available")
    return pool


async def _verify_conversation(
    conversation_id: uuid.UUID,
    anon_id: str,
    pool: AsyncConnectionPool,
) -> uuid.UUID:
    """Verify conversation exists and belongs to anon_id."""
    await get_conversation_or_404(conversation_id, anon_id, pool)
    return conversation_id


@router.post(
    "/conversations/{conversation_id}/documents",
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    request: Request,
    conversation_id: uuid.UUID,
    anon_id: Annotated[str, Depends(get_anon_id)],
    file: Annotated[UploadFile, File(...)],
):
    """Upload a PDF document for a conversation.

    Validates:
    - File is a PDF (magic bytes)
    - File size <= max_pdf_mb
    - Page count <= max_pdf_pages
    - Max 3 documents per conversation
    - Extractable text exists (not scanned)

    On success, extracts text, chunks, embeds, and stores in pgvector.
    """
    pool = _pool(request)
    await _verify_conversation(conversation_id, anon_id, pool)

    # Validate content type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File must be a PDF",
        )

    # Read file content
    content = await file.read()

    # Validate size
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_pdf_mb} MB limit",
        )

    # Validate PDF magic bytes and page count
    try:
        validate_pdf_bytes(content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e),
        )

    # Check document limit
    repo = ConversationRepository(pool)
    doc_count = await repo.count_documents(conversation_id)
    if doc_count >= settings.max_docs_per_conversation:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Maximum {settings.max_docs_per_conversation} documents per conversation reached",
        )

    # Ingest PDF (extract, chunk, embed, store)
    try:
        result = await ingest_pdf(
            data=content,
            filename=file.filename or "document.pdf",
            conversation_id=conversation_id,
            pool=pool,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return result


@router.get("/conversations/{conversation_id}/documents")
async def list_documents(
    request: Request,
    conversation_id: uuid.UUID,
    anon_id: Annotated[str, Depends(get_anon_id)],
):
    """List all documents for a conversation."""
    pool = _pool(request)
    await _verify_conversation(conversation_id, anon_id, pool)
    repo = ConversationRepository(pool)
    docs = await repo.list_documents(conversation_id)
    return {"items": docs}


@router.delete(
    "/conversations/{conversation_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    request: Request,
    conversation_id: uuid.UUID,
    document_id: uuid.UUID,
    anon_id: Annotated[str, Depends(get_anon_id)],
):
    """Delete a document (cascades to chunks)."""
    pool = _pool(request)
    await _verify_conversation(conversation_id, anon_id, pool)
    repo = ConversationRepository(pool)
    deleted = await repo.delete_document(document_id, conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return None