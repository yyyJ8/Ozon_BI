"""SKU 管理 API — 手动维护的 SKU 业务数据 CRUD"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, Stock, SkuManagement
from app.schemas.sku_management import (
    SkuManagementItem,
    SkuManagementBatchUpdate,
)

router = APIRouter(prefix="/sku-management", tags=["sku-management"])

# 可编辑字段列表
EDITABLE_FIELDS = [
    "main_sku", "source_url_1688", "specification", "sales_manager",
    "listed_stores", "product_status", "key_notes",
    "length_cm", "width_cm", "height_cm", "actual_weight_kg", "volume_cbm", "density",
    "first_leg_unit_price", "units_per_carton",
    "carton_length_cm", "carton_width_cm", "carton_height_cm",
    "gross_weight_kg", "volume_liters",
    "purchase_cost_rmb", "warehousing_fee_rmb", "fbo_delivery_fee_rmb", "first_leg_cost_rmb",
    "acquiring_fee_pct", "fbo_commission_pct", "logistics_rub", "delivery_pickup_rub",
    "advertising_rate_pct", "return_rate_pct", "tax_and_fee_pct", "risk_reserve_rub",
    "exchange_rate", "green_price_rub",
    "competitor_1", "competitor_2", "competitor_sales",
    "purchase_cost_pct", "first_leg_pct", "last_mile_pct",
    "product_cost_rmb", "discount_pct",
    "platform_payout_rub", "actual_payout_rub",
    "profit_rmb", "profit_rub", "profit_margin_pct",
]


def _row_to_item(product, mgmt, p_name, p_offer_id, p_image, p_price, p_category, sp) -> SkuManagementItem:
    """将 ORM 行转换为响应模型"""
    data = {"store_id": product.store_id, "sku_id": product.sku_id}
    if mgmt is not None:
        for col in SkuManagement.__table__.columns:
            key = col.name
            if key in ("store_id", "sku_id", "created_at", "updated_at"):
                continue
            data[key] = getattr(mgmt, key, None)
        data["created_at"] = mgmt.created_at
        data["updated_at"] = mgmt.updated_at
    else:
        for col in SkuManagement.__table__.columns:
            if col.name in ("store_id", "sku_id"):
                continue
            data[col.name] = None
        data["created_at"] = None
        data["updated_at"] = None

    data["name"] = p_name
    data["offer_id"] = p_offer_id
    data["primary_image"] = p_image
    data["price"] = float(p_price) if p_price is not None else None
    data["category_name"] = p_category
    data["stock_present"] = int(sp) if sp is not None else 0
    return SkuManagementItem(**data)


@router.get("", response_model=list[SkuManagementItem])
def list_all(
    store_id: int = Query(default=1, description="店铺 ID，0=全部"),
    db: Session = Depends(get_db),
):
    """获取所有 SKU 管理数据（含 products 表信息）"""
    # 库存子查询
    stock_q = (
        db.query(Stock.sku_id, func.coalesce(func.sum(Stock.present), 0).label("present"))
    )
    if store_id != 0:
        stock_q = stock_q.filter(Stock.store_id == store_id)
    stock_sub = stock_q.group_by(Stock.sku_id).subquery()

    # products + sku_management LEFT JOIN
    prod_q = db.query(
        Product,
        SkuManagement,
        Product.name,
        Product.offer_id,
        Product.primary_image,
        Product.price,
        Product.category_id,
        func.coalesce(stock_sub.c.present, 0).label("stock_present"),
    )
    if store_id != 0:
        prod_q = prod_q.filter(Product.store_id == store_id)
    prod_q = prod_q.outerjoin(
        SkuManagement,
        (Product.store_id == SkuManagement.store_id) & (Product.sku_id == SkuManagement.sku_id),
    ).outerjoin(stock_sub, Product.sku_id == stock_sub.c.sku_id)

    rows = prod_q.order_by(Product.name).all()

    # category_id -> name 简单映射（可后续从 Ozon API 获取真实类目名）
    result = []
    for p, mgmt, p_name, p_offer_id, p_image, p_price, p_cat, sp in rows:
        item = _row_to_item(p, mgmt, p_name, p_offer_id, p_image, p_price, str(p_cat) if p_cat else None, sp)
        result.append(item)
    return result


@router.put("/batch", response_model=list[SkuManagementItem])
def batch_update(
    payload: SkuManagementBatchUpdate,
    store_id: int = Query(default=1),
    db: Session = Depends(get_db),
):
    """批量 upsert SKU 管理数据，返回更新后的全量数据"""
    # 预查有效的 SKU
    valid_skus = set(
        sku for (sku,) in
        db.query(Product.sku_id).filter(Product.store_id == store_id).all()
    )
    updated = 0

    for item in payload.items:
        if item.sku_id not in valid_skus:
            continue

        update_data = {k: v for k, v in item.model_dump(exclude_unset=True).items()
                       if k != "sku_id" and k in EDITABLE_FIELDS}

        existing = db.query(SkuManagement).filter_by(
            store_id=store_id, sku_id=item.sku_id
        ).first()

        if existing:
            for key, value in update_data.items():
                setattr(existing, key, value)
        else:
            db.add(SkuManagement(store_id=store_id, sku_id=item.sku_id, **update_data))
        updated += 1

    db.commit()

    # 返回全量数据
    stock_q = (
        db.query(Stock.sku_id, func.coalesce(func.sum(Stock.present), 0).label("present"))
        .filter(Stock.store_id == store_id)
        .group_by(Stock.sku_id)
    ).subquery()

    rows = (
        db.query(
            Product,
            SkuManagement,
            Product.name,
            Product.offer_id,
            Product.primary_image,
            Product.price,
            Product.category_id,
            func.coalesce(stock_q.c.present, 0).label("stock_present"),
        )
        .filter(Product.store_id == store_id)
        .outerjoin(
            SkuManagement,
            (Product.store_id == SkuManagement.store_id) & (Product.sku_id == SkuManagement.sku_id),
        )
        .outerjoin(stock_q, Product.sku_id == stock_q.c.sku_id)
        .order_by(Product.name)
        .all()
    )

    return [
        _row_to_item(p, mgmt, p_name, p_offer_id, p_image, p_price, str(p_cat) if p_cat else None, sp)
        for p, mgmt, p_name, p_offer_id, p_image, p_price, p_cat, sp in rows
    ]
