"""补货提示 API"""
from fastapi import APIRouter, Depends, Query

from app.services.replenishment_service import get_replenishment_data

router = APIRouter(prefix="/replenishment", tags=["replenishment"])


@router.get("")
def list_replenishment(
    store_id: int = Query(default=0, description="店铺 ID，0=全部"),
):
    """获取补货提示列表（含公式计算结果）"""
    return get_replenishment_data(store_id=store_id)
