"""API 路由注册"""
from fastapi import APIRouter

from app.api.products import router as products_router
from app.api.summary import router as summary_router
from app.api.sync import router as sync_router
from app.api.finance import router as finance_router
from app.api.advertising import router as advertising_router
from app.api.returns import router as returns_router
from app.api.orders import router as orders_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(products_router)
api_router.include_router(summary_router)
api_router.include_router(sync_router)
api_router.include_router(finance_router)
api_router.include_router(advertising_router)
api_router.include_router(returns_router)
api_router.include_router(orders_router)
