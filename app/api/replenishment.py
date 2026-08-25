"""补货提示 API"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ReplenishmentConfig
from app.schemas.replenishment import ReplenishmentConfigItem
from app.services.replenishment_service import get_replenishment_data

router = APIRouter(prefix="/replenishment", tags=["replenishment"])


@router.get("")
def list_replenishment(
    store_id: int = Query(default=0, description="店铺 ID，0=全部"),
):
    """获取补货提示列表（含公式计算结果）"""
    return get_replenishment_data(store_id=store_id)


@router.post("/config", response_model=ReplenishmentConfigItem)
def upsert_config(
    payload: ReplenishmentConfigItem,
    db: Session = Depends(get_db),
):
    """新增/更新补货配置（安全天数、物流天数）。

    配置以 (store_id, offer_id) 为主键：
    - 已存在 → 更新安全/物流天数（新增时 product_name 为 None 时保留原值）
    - 不存在 → 插入新配置行
    """
    now = datetime.now()
    cfg = db.query(ReplenishmentConfig).filter_by(
        store_id=payload.store_id, offer_id=payload.offer_id
    ).first()

    if cfg is not None:
        cfg.safety_days = payload.safety_days
        cfg.logistics_days = payload.logistics_days
        if payload.product_name is not None:
            cfg.product_name = payload.product_name
        cfg.updated_at = now
    else:
        cfg = ReplenishmentConfig(
            store_id=payload.store_id,
            offer_id=payload.offer_id,
            product_name=payload.product_name,
            safety_days=payload.safety_days,
            logistics_days=payload.logistics_days,
            created_at=now,
            updated_at=now,
        )
        db.add(cfg)

    db.commit()
    db.refresh(cfg)
    return cfg
