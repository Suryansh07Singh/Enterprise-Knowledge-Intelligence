import os
import hashlib
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.domain import Document, DocumentChunk, IngestionJob
from app.ingestion.parser import DocumentParser
from app.ingestion.chunker import IntelligentChunker
from app.retrieval.dense import qdrant_store
from app.retrieval.sparse import bm25_store
from app.core.logging import logger

class IngestionPipeline:
    """Async Document Ingestion Pipeline worker."""

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def process_document(
        self,
        db: AsyncSession,
        document_id: str,
        job_id: str
    ) -> bool:
        """Asynchronously parses, chunks, embeds, and indexes a document."""
        # 1. Fetch document and job
        doc_stmt = select(Document).where(Document.id == document_id)
        res = await db.execute(doc_stmt)
        doc = res.scalar_one_or_none()

        job_stmt = select(IngestionJob).where(IngestionJob.id == job_id)
        j_res = await db.execute(job_stmt)
        job = j_res.scalar_one_or_none()

        if not doc or not job:
            logger.error(f"Ingestion failed: Document {document_id} or Job {job_id} not found.")
            return False

        try:
            # Update status
            doc.status = "PROCESSING"
            job.status = "PROCESSING"
            job.progress = 0.1
            await db.commit()

            # 2. Parse file
            logger.info(f"Parsing document file: {doc.file_path}")
            parsed_pages = DocumentParser.parse_file(doc.file_path, doc.file_type)
            doc.total_pages = len(parsed_pages)
            job.progress = 0.3
            await db.commit()

            # 3. Chunk text
            chunker = IntelligentChunker()
            doc_meta = {
                "id": doc.id,
                "name": doc.name,
                "department": doc.department,
                "access_level": doc.access_level,
                "version": doc.version
            }
            chunks_data = chunker.chunk_document(parsed_pages, doc_meta)
            job.progress = 0.5
            await db.commit()

            # 4. Save chunks to SQL DB
            db_chunks = []
            for cdata in chunks_data:
                dchunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=cdata["chunk_index"],
                    text=cdata["text"],
                    token_count=cdata["token_count"],
                    page_number=cdata["page_number"],
                    section_title=cdata["section_title"],
                    access_level=cdata["access_level"],
                    department=cdata["department"]
                )
                db_chunks.append(dchunk)
                db.add(dchunk)
            
            await db.flush()
            job.progress = 0.7
            await db.commit()

            # 5. Index into Dense Vector Store (Qdrant) & Sparse Store (BM25)
            logger.info(f"Indexing {len(chunks_data)} chunks into vector & BM25 stores...")
            
            # Map chunk DB IDs to chunk payloads
            for i, cdata in enumerate(chunks_data):
                cdata["id"] = db_chunks[i].id

            qdrant_store.insert_chunks(chunks_data)
            bm25_store.add_chunks(chunks_data)

            # 6. Complete Job
            doc.status = "COMPLETED"
            job.status = "COMPLETED"
            job.progress = 1.0
            await db.commit()

            logger.info(f"Successfully processed and indexed document {doc.id} ({doc.name})")
            return True

        except Exception as e:
            logger.error(f"Ingestion failed for document {document_id}: {e}", exc_info=True)
            doc.status = "FAILED"
            doc.error_message = str(e)
            job.status = "FAILED"
            job.error_message = str(e)
            await db.commit()
            return False

ingestion_pipeline = IngestionPipeline()
