from fastapi import APIRouter

from app.api.v1.balance import router as balance_router
from app.api.v1.chat import router as chat_router
from app.api.v1.extract import router as extract_router

api_router = APIRouter()
api_router.include_router(balance_router)
api_router.include_router(chat_router)
api_router.include_router(extract_router)
