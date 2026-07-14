"""
Ozon BI Dashboard — FastAPI 应用入口

启动: uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router

app = FastAPI(
    title="Ozon BI Dashboard",
    description="Ozon 电商平台 SKU 维度 BI 看板 API",
    version="0.1.0",
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
