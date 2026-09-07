import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, AsyncSessionLocal
from app.api.auth import get_current_user
from app.models.domain import User, Document, IngestionJob, DocumentChunk
from app.schemas.pydantic_models import DocumentResponse, IngestionJobResponse
from app.ingestion.pipeline import ingestion_pipeline, IngestionPipeline
from app.retrieval.dense import qdrant_store
from app.retrieval.sparse import bm25_store
from app.core.logging import logger

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "./data/uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def _bg_ingest_wrapper(document_id: str, job_id: str):
    """Background task wrapper opening a new DB session."""
    async with AsyncSessionLocal() as db:
        await ingestion_pipeline.process_document(db, document_id, job_id)

@router.post("/upload", response_model=IngestionJobResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    department: str = Form("General"),
    access_level: str = Form("employee"),
    version: str = Form("1.0"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Only HR, Finance, Admin or authorized employees can upload
    ext = os.path.splitext(file.filename)[1].lower().strip(".")
    if ext not in ["pdf", "docx", "doc", "md", "markdown", "txt", "html", "htm"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file format '.{ext}'")

    file_path = os.path.join(UPLOAD_DIR, f"{current_user.id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_hash = IngestionPipeline.calculate_file_hash(file_path)

    # Check duplicate hash
    dup_stmt = select(Document).where(Document.file_hash == file_hash, Document.status != "DELETED")
    dup_doc = (await db.execute(dup_stmt)).scalar_one_or_none()
    if dup_doc:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Duplicate document already exists (ID: {dup_doc.id})")

    size_bytes = os.path.getsize(file_path)

    doc = Document(
        name=file.filename,
        file_path=file_path,
        file_hash=file_hash,
        file_type=ext,
        size_bytes=size_bytes,
        department=department or current_user.department,
        access_level=access_level,
        version=version,
        status="PENDING"
    )
    db.add(doc)
    await db.flush()

    job = IngestionJob(
        document_id=doc.id,
        status="PENDING",
        progress=0.0
    )
    db.add(job)
    await db.commit()

    # Launch non-blocking background ingestion worker task
    background_tasks.add_task(_bg_ingest_wrapper, doc.id, job.id)

    return IngestionJobResponse(
        job_id=job.id,
        document_id=doc.id,
        status="PROCESSING",
        progress=0.0,
        created_at=job.created_at
    )

@router.get("", response_model=List[DocumentResponse])
async def list_documents(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Document).where(Document.status != "DELETED").order_by(Document.created_at.desc())
    res = await db.execute(stmt)
    docs = res.scalars().all()
    
    # Filter viewable documents by user permissions
    allowed = []
    roles_lower = [r.lower() for r in current_user.roles]
    for d in docs:
        acc = d.access_level.lower()
        if "admin" in roles_lower or acc in ["public", "employee"] or d.department == current_user.department or acc in roles_lower:
            allowed.append(d)

    return allowed

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Document).where(Document.id == document_id, Document.status != "DELETED")
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/{document_id}")
async def delete_document(document_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Document).where(Document.id == document_id)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    roles_lower = [r.lower() for r in current_user.roles]
    if "admin" not in roles_lower and current_user.department != doc.department:
        raise HTTPException(status_code=403, detail="Unauthorized to delete this document")

    doc.status = "DELETED"
    await db.commit()

    # Remove from Vector & BM25 indexes
    qdrant_store.delete_document_chunks(document_id)
    bm25_store.remove_document_chunks(document_id)

    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    return {"message": "Document successfully deleted", "document_id": document_id}
