from fastapi import APIRouter, HTTPException

from app.schemas.chat import (
    ChatRequest,
    ChatResetRequest,
    ChatResetResponse,
    ChatResponse,
)
from app.services.chat_service import chat_with_user_memory, reset_user_memory

# v1 聊天路由。
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """按用户 ID 聊天：每个用户拥有独立上下文记忆。"""

    try:
        reply, history_size = await chat_with_user_memory(
            user_id=payload.user_id,
            message=payload.message,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"模型调用失败: {exc}") from exc

    return ChatResponse(
        user_id=payload.user_id,
        reply=reply,
        history_size=history_size,
    )


@router.post("/chat/reset", response_model=ChatResetResponse)
async def reset_chat(payload: ChatResetRequest) -> ChatResetResponse:
    """按用户 ID 一键清空会话上下文。"""

    try:
        previous_size, current_size = reset_user_memory(payload.user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"清空会话失败: {exc}") from exc

    return ChatResetResponse(
        user_id=payload.user_id,
        previous_history_size=previous_size,
        current_history_size=current_size,
    )
