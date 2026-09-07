import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.redis import redis_client
from app.core.security import get_password_hash
from app.models.domain import User, Document, DocumentChunk
from app.api.router import api_router
from app.ingestion.pipeline import ingestion_pipeline, IngestionPipeline
from app.retrieval.dense import qdrant_store
from app.retrieval.sparse import bm25_store
from app.core.logging import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize DB tables
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Initialize Redis Client
    await redis_client.init()

    # 3. Seed initial admin user & sample enterprise knowledge documents
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.email == "admin@enterprise.com")
        admin_user = (await db.execute(stmt)).scalar_one_or_none()
        if not admin_user:
            logger.info("Seeding default admin and employee accounts...")
            admin = User(
                email="admin@enterprise.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Enterprise Admin",
                roles=["ADMIN", "HR", "FINANCE"],
                department="Management"
            )
            employee = User(
                email="employee@enterprise.com",
                hashed_password=get_password_hash("employee123"),
                full_name="John Doe",
                roles=["EMPLOYEE"],
                department="Engineering"
            )
            db.add(admin)
            db.add(employee)
            await db.commit()

        # Seed sample documents if none exist
        doc_stmt = select(Document)
        existing_docs = (await db.execute(doc_stmt)).scalars().all()
        if not existing_docs:
            logger.info("Seeding initial enterprise knowledge policy documents...")
            seed_dir = "./data/sample_docs"
            os.makedirs(seed_dir, exist_ok=True)
            
            sample_policy = os.path.join(seed_dir, "Travel_Policy.pdf")
            with open(sample_policy, "w", encoding="utf-8") as f:
                f.write(
                    "# Enterprise Travel & Reimbursement Policy\n\n"
                    "## Eligibility & Proration\n"
                    "All full-time employees are eligible for travel allowance. "
                    "Employees who joined after June 30 receive a pro-rated travel allowance of 50%.\n\n"
                    "## International Travel\n"
                    "The maximum reimbursement allowed for international business travel is capped at $250 per day "
                    "for meals and incidental expenses. All international travel requires VP approval.\n\n"
                    "## Domestic Travel\n"
                    "Domestic business travel allows up to $120 per day for meals."
                )

            seed_doc = Document(
                name="Travel_Policy.pdf",
                file_path=sample_policy,
                file_hash=IngestionPipeline.calculate_file_hash(sample_policy),
                file_type="pdf",
                size_bytes=os.path.getsize(sample_policy),
                department="Finance",
                access_level="employee",
                version="2026.1",
                total_pages=1,
                status="COMPLETED"
            )
            db.add(seed_doc)
            await db.flush()

            # Create sample chunks
            c1 = DocumentChunk(
                document_id=seed_doc.id,
                chunk_index=0,
                text="All full-time employees are eligible for travel allowance. Employees who joined after June 30 receive a pro-rated travel allowance of 50%.",
                page_number=1,
                section_title="Eligibility & Proration",
                department="Finance",
                access_level="employee"
            )
            c2 = DocumentChunk(
                document_id=seed_doc.id,
                chunk_index=1,
                text="The maximum reimbursement allowed for international business travel is capped at $250 per day for meals and incidental expenses. All international travel requires VP approval.",
                page_number=1,
                section_title="International Travel",
                department="Finance",
                access_level="employee"
            )
            db.add(c1)
            db.add(c2)
            await db.commit()

            # Index into retrieval systems
            chunks_payload = [
                {
                    "id": c1.id,
                    "document_id": seed_doc.id,
                    "document_name": seed_doc.name,
                    "chunk_index": 0,
                    "text": c1.text,
                    "page_number": 1,
                    "section_title": "Eligibility & Proration",
                    "department": "Finance",
                    "access_level": "employee"
                },
                {
                    "id": c2.id,
                    "document_id": seed_doc.id,
                    "document_name": seed_doc.name,
                    "chunk_index": 1,
                    "text": c2.text,
                    "page_number": 1,
                    "section_title": "International Travel",
                    "department": "Finance",
                    "access_level": "employee"
                }
            ]
            qdrant_store.insert_chunks(chunks_payload)
            bm25_store.add_chunks(chunks_payload)
            logger.info("Successfully seeded sample knowledge base chunks into Qdrant & BM25.")

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Enterprise Knowledge Intelligence Platform API",
        "docs": "/docs",
        "version": settings.VERSION
    }
