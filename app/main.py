"""
Ozon BI Dashboard — FastAPI 应用入口

启动: uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：加载定时调度
    from app.scheduler import start_scheduler
    start_scheduler()
    yield
    # 关闭时：停止定时调度
    from app.scheduler import stop_scheduler
    stop_scheduler()


app = FastAPI(
    title="Ozon BI Dashboard",
    description="Ozon 电商平台 SKU 维度 BI 看板 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — 允许前端开发服务器跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
