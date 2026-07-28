"""
异常检测 API — 根据 YAML 规则自动检测异常 SKU
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.anomalies import AnomalyResponse
from app.services.anomaly_service import detect_anomalies

router = APIRouter(prefix="/anomalies", tags=["anomalies"])

STORE_ID = Query(default=1, description="店铺 ID，0=全部店铺")


@router.get("", response_model=AnomalyResponse)
def get_anomalies(
    date_from: Optional[date] = Query(default=None, description="起始日期，默认当月1日"),
    date_to: Optional[date] = Query(default=None, description="截止日期，默认昨天"),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    """
    执行全部异常检测规则，返回异常 SKU 列表及汇总统计。

    默认检测当月（1日 → 昨天），可通过 date_from/date_to 自定义范围。
    规则定义在 app/anomaly_rules.yaml，改 YAML 即可调整阈值。
    """
    result = detect_anomalies(db, store_id, date_from, date_to)
    return AnomalyResponse(**result)
