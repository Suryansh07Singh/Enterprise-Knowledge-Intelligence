from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.domain import User, IngestionJob
from app.schemas.pydantic_models import IngestionJobResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/{job_id}", response_model=IngestionJobResponse)
async def get_job_status(job_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(IngestionJob).where(IngestionJob.id == job_id)
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return IngestionJobResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        progress=job.progress,
        error_message=job.error_message,
        created_at=job.created_at
    )
