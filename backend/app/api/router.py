from fastapi import APIRouter
from app.api import auth, documents, jobs, search, chat, conversations, metrics, evaluation

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(jobs.router)
api_router.include_router(search.router)
api_router.include_router(chat.router)
api_router.include_router(conversations.router)
api_router.include_router(metrics.router)
api_router.include_router(evaluation.router)
