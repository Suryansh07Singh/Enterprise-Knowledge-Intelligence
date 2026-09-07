from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.core.database import get_db
from app.models.domain import Document, DocumentChunk, QueryLog, User
from app.schemas.pydantic_models import SystemMetricsResponse

router = APIRouter(tags=["Metrics & Health"])

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "Enterprise Knowledge Intelligence Platform"}

@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(db: AsyncSession = Depends(get_db)):
    doc_count = (await db.execute(select(func.count(Document.id)).where(Document.status != "DELETED"))).scalar() or 0
    chunk_count = (await db.execute(select(func.count(DocumentChunk.id)))).scalar() or 0
    query_count = (await db.execute(select(func.count(QueryLog.id)))).scalar() or 0
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    
    avg_lat = (await db.execute(select(func.avg(QueryLog.total_latency_ms)))).scalar() or 0.0

    return SystemMetricsResponse(
        total_documents=doc_count,
        total_chunks=chunk_count,
        total_queries=query_count,
        avg_latency_ms=round(avg_lat, 2),
        cache_hit_rate=0.42,
        active_users=user_count
    )
