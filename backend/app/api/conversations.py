from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.domain import User, Conversation, Message
from app.schemas.pydantic_models import ConversationResponse, MessageResponse

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("", response_model=List[ConversationResponse])
async def list_conversations(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).where(Conversation.user_id == current_user.id).order_by(Conversation.updated_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
    conv = (await db.execute(stmt)).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    m_stmt = select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at.asc())
    msgs = (await db.execute(m_stmt)).scalars().all()
    
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[MessageResponse.model_validate(m) for m in msgs]
    )
