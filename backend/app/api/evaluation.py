from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.domain import User, EvaluationRun
from app.schemas.pydantic_models import EvaluationRunRequest, EvaluationRunResponse
from app.evaluation.runner import benchmark_runner

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Benchmarks"])

@router.post("/run", response_model=List[EvaluationRunResponse])
async def trigger_benchmark_run(
    req: EvaluationRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    roles_lower = [r.lower() for r in current_user.roles]
    if "admin" not in roles_lower:
        raise HTTPException(status_code=403, detail="Only administrators can execute benchmark evaluations")

    runs = []
    for mode in req.modes:
        res = await benchmark_runner.run_evaluation(db, run_name=req.name, mode=mode)
        runs.append(EvaluationRunResponse(**res))

    return runs

@router.get("/results", response_model=List[EvaluationRunResponse])
async def list_evaluation_results(db: AsyncSession = Depends(get_db)):
    stmt = select(EvaluationRun).order_by(EvaluationRun.created_at.desc())
    res = await db.execute(stmt)
    runs = res.scalars().all()
    return [EvaluationRunResponse.model_validate(r) for r in runs]
