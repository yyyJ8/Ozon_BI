"""API 路由注册"""
from fastapi import APIRouter

from app.api.products import router as products_router
from app.api.summary import router as summary_router
from app.api.sync import router as sync_router
from app.api.finance import router as finance_router
from app.api.advertising import router as advertising_router
from app.api.returns import router as returns_router
from app.api.orders import router as orders_router
from app.api.stocks import router as stocks_router
from app.api.stores import router as stores_router
from app.api.profit import router as profit_router
from app.api.anomalies import router as anomalies_router
from app.api.sku_management import router as sku_management_router
from app.api.procurement import router as procurement_router
from app.api.ozon_direct import router as ozon_direct_router
from app.api.replenishment import router as replenishment_router
from app.api.real_profit import router as real_profit_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(products_router)
api_router.include_router(summary_router)
api_router.include_router(sync_router)
api_router.include_router(finance_router)
api_router.include_router(advertising_router)
api_router.include_router(returns_router)
api_router.include_router(orders_router)
api_router.include_router(stocks_router)
api_router.include_router(stores_router)
api_router.include_router(profit_router)
api_router.include_router(anomalies_router)
api_router.include_router(sku_management_router)
api_router.include_router(procurement_router)
api_router.include_router(ozon_direct_router)
api_router.include_router(replenishment_router)
api_router.include_router(real_profit_router)
