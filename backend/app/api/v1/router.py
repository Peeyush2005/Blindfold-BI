"""
Aggregated v1 API Router for Blindfold BI.
Prefix: /api/v1
"""

from fastapi import APIRouter
from app.api.v1.chat import router as chat_router
from app.api.v1.runs import router as runs_router
from app.api.v1.meta import router as meta_router
from app.api.v1.tools import router as tools_router
from app.api.v1.data import router as data_router
from app.api.v1.admin_keys import router as admin_keys_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(chat_router)
api_v1_router.include_router(runs_router)
api_v1_router.include_router(meta_router)
api_v1_router.include_router(tools_router)
api_v1_router.include_router(data_router)
api_v1_router.include_router(admin_keys_router)
