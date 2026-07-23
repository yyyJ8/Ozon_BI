"""店铺管理 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Store

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("")
def list_stores(db: Session = Depends(get_db)):
    """获取所有启用的店铺列表"""
    stores = db.query(Store).filter_by(is_active=True).order_by(Store.id).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "is_active": s.is_active,
        }
        for s in stores
    ]
