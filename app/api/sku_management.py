"""SKU 管理 API — 手动维护的 SKU 业务数据 CRUD"""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, Stock, SkuManagement
from app.schemas.sku_management import (
    SkuManagementItem,
    SkuManagementBatchUpdate,
)
from app.services.sku_formulas import INPUT_FIELDS, COMPUTED_FIELDS, compute_formulas

router = APIRouter(prefix="/sku-management", tags=["sku-management"])

# 可保存字段 = 输入字段 + 计算字段（计算字段由公式引擎自动填充）
SAVEABLE_FIELDS = INPUT_FIELDS + COMPUTED_FIELDS

# 莫斯科时区（UTC+3，无夏令时）— 快照表 record_date 以莫斯科日期为准，与 scheduler 语义一致
MOSCOW_TZ = timezone(timedelta(hours=3))


def _moscow_today() -> date:
    """当前莫斯科日期"""
    return datetime.now(MOSCOW_TZ).date()


def _upsert_snapshot(db: Session, store_id: int, sku_id: int, record_date: date, values: dict) -> None:
    """将 sku_management 的绿标价同步到 sku_daily_snapshot 当日记录。

    折扣在 SQL 中按 1 - 绿标价 ÷ 售价 实时计算，保证与当天售价自洽。
    当日记录不存在则创建（价格/库存取自 products + stocks，与 scheduler 相同），
    已存在则只更新 green_price / discount_pct / synced_at，不覆盖历史快照的价格与库存。
    """
    db.execute(text("""
        INSERT INTO ozon.sku_daily_snapshot
            (store_id, sku_id, record_date, offer_id,
             price, old_price, marketing_seller_price, min_price,
             green_price, discount_pct,
             stock_present, stock_reserved, synced_at)
        SELECT
            p.store_id, p.sku_id, :record_date, p.offer_id,
            p.price, p.old_price, p.marketing_seller_price, p.min_price,
            :green_price,
            CASE
                WHEN :green_price IS NOT NULL
                     AND p.marketing_seller_price IS NOT NULL
                     AND p.marketing_seller_price > 0
                THEN ROUND((1 - :green_price / p.marketing_seller_price) * 100, 2)
                ELSE NULL
            END,
            COALESCE(s.present, 0), COALESCE(s.reserved, 0), now()
        FROM ozon.products p
        LEFT JOIN (
            SELECT store_id, sku_id, SUM(present) AS present, SUM(reserved) AS reserved
            FROM ozon.stocks GROUP BY store_id, sku_id
        ) s ON p.store_id = s.store_id AND p.sku_id = s.sku_id
        WHERE p.store_id = :store_id AND p.sku_id = :sku_id
        ON CONFLICT (store_id, sku_id, record_date) DO UPDATE SET
            green_price  = EXCLUDED.green_price,
            discount_pct = EXCLUDED.discount_pct,
            synced_at    = now()
    """), {
        "store_id": store_id,
        "sku_id": sku_id,
        "record_date": record_date,
        "green_price": values.get("green_price"),
    })


def _row_to_item(product, mgmt, p_name, p_offer_id, p_image, p_price, p_category, sp, p_commission) -> SkuManagementItem:
    """将 ORM 行转换为响应模型"""
    data = {"store_id": product.store_id, "sku_id": product.sku_id}
    if mgmt is not None:
        for col in SkuManagement.__table__.columns:
            key = col.name
            if key in ("store_id", "sku_id"):
                continue
            data[key] = getattr(mgmt, key, None)
    else:
        for col in SkuManagement.__table__.columns:
            if col.name in ("store_id", "sku_id"):
                continue
            data[col.name] = None

    data["name"] = p_name
    data["offer_id"] = p_offer_id
    data["primary_image"] = p_image
    data["price"] = float(p_price) if p_price is not None else None
    data["category_name"] = p_category
    data["stock_present"] = int(sp) if sp is not None else 0
    # 佣金从 products 表自动读取，转为整数百分比（0.40 → 40.0）
    data["fbo_commission_pct"] = float(p_commission) * 100 if p_commission is not None else None
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
        Product.marketing_seller_price,
        Product.category_id,
        Product.commission_fbo_pct,
        func.coalesce(stock_sub.c.present, 0).label("stock_present"),
    )
    if store_id != 0:
        prod_q = prod_q.filter(Product.store_id == store_id)
    prod_q = prod_q.outerjoin(
        SkuManagement,
        (Product.store_id == SkuManagement.store_id) & (Product.sku_id == SkuManagement.sku_id),
    ).outerjoin(stock_sub, Product.sku_id == stock_sub.c.sku_id)

    # 过滤软删除：保留无管理记录（NULL）和未归档（false）的行
    prod_q = prod_q.filter(
        (SkuManagement.is_archived.is_(None)) | (SkuManagement.is_archived.is_(False))
    )

    rows = prod_q.order_by(Product.name).all()

    # category_id -> name 简单映射（可后续从 Ozon API 获取真实类目名）
    result = []
    for p, mgmt, p_name, p_offer_id, p_image, p_price, p_cat, p_commission, sp in rows:
        item = _row_to_item(p, mgmt, p_name, p_offer_id, p_image, p_price, str(p_cat) if p_cat else None, sp, p_commission)
        result.append(item)
    return result


@router.put("/batch", response_model=list[SkuManagementItem])
def batch_update(
    payload: SkuManagementBatchUpdate,
    store_id: int = Query(default=1),
    db: Session = Depends(get_db),
):
    """批量 upsert SKU 管理数据，自动计算公式字段，返回更新后的全量数据。

    store_id=0 表示全部店铺：按每个 SKU 在 products 中的真实店铺写入
    （同一 SKU 存在于多个店铺时，全部写入），避免"全部店铺"下静默丢保存。
    """
    # ── 解析每个 SKU 的真实店铺（sku_id → [store_id, ...]）──
    sku_store_map: dict[int, list[int]] = {}
    sku_rows = db.query(Product.store_id, Product.sku_id).filter(
        Product.sku_id.in_([it.sku_id for it in payload.items])
    )
    if store_id != 0:
        sku_rows = sku_rows.filter(Product.store_id == store_id)
    for sid, sku in sku_rows:
        sku_store_map.setdefault(sku, []).append(sid)

    # 批量获取促销价 + 佣金（公式计算需要售价和佣金，按 (store_id, sku_id) 区分）
    price_rows = (
        db.query(Product.store_id, Product.sku_id, Product.marketing_seller_price, Product.commission_fbo_pct)
        .filter(Product.sku_id.in_(list(sku_store_map.keys())))
        .all()
    )
    price_map = {(sid, sku): float(p) if p else None for sid, sku, p, _ in price_rows}
    commission_map = {(sid, sku): float(c) if c else None for sid, sku, _, c in price_rows}

    updated = 0
    # 需要同步到快照表（sku_daily_snapshot）的记录：绿标价/折扣变更时
    snapshot_sync: dict[tuple[int, int], dict] = {}

    for item in payload.items:
        stores = sku_store_map.get(item.sku_id)
        if not stores:
            continue

        # 只取用户提交的输入字段
        user_input = {
            k: v for k, v in item.model_dump(exclude_unset=True).items()
            if k != "sku_id" and k in INPUT_FIELDS
        }

        for sid in stores:
            existing = db.query(SkuManagement).filter_by(
                store_id=sid, sku_id=item.sku_id
            ).first()

            # 合并：已有输入值 + 用户本次修改的输入值
            merged_input: dict = {}
            for field in INPUT_FIELDS:
                merged_input[field] = getattr(existing, field, None) if existing else None
            merged_input.update(user_input)

            # 佣金从 products 表自动读取，注入公式引擎
            merged_input["fbo_commission_pct"] = commission_map.get((sid, item.sku_id))

            # 运行公式引擎
            price = price_map.get((sid, item.sku_id))
            computed = compute_formulas(merged_input, price)

            # 最终写入 = 输入字段 + 计算字段
            update_data = {**merged_input, **computed}

            # 过滤：只保留 SkuManagement 模型实际有的列
            model_columns = {c.name for c in SkuManagement.__table__.columns}
            update_data = {k: v for k, v in update_data.items() if k in model_columns}

            if existing:
                for key, value in update_data.items():
                    setattr(existing, key, value)
            else:
                db.add(SkuManagement(store_id=sid, sku_id=item.sku_id, **update_data))
            updated += 1

            # 绿标价被修改时，同步到快照表当日记录（折扣由快照 SQL 按当天售价计算）
            if "green_price_rub" in user_input:
                snapshot_sync[(sid, item.sku_id)] = {
                    "green_price": update_data.get("green_price_rub"),
                }

    # 与 sku_management 同事务写入快照表（避免前端保存后快照仍是旧值）
    if snapshot_sync:
        record_date = _moscow_today()
        for (sid, sku), sync in snapshot_sync.items():
            _upsert_snapshot(db, sid, sku, record_date, sync)

    db.commit()

    # 返回全量数据（store_id=0 时返回全部店铺，与 list_all 一致）
    stock_q = (
        db.query(Stock.sku_id, func.coalesce(func.sum(Stock.present), 0).label("present"))
    )
    if store_id != 0:
        stock_q = stock_q.filter(Stock.store_id == store_id)
    stock_sub = stock_q.group_by(Stock.sku_id).subquery()

    rows = (
        db.query(
            Product,
            SkuManagement,
            Product.name,
            Product.offer_id,
            Product.primary_image,
            Product.marketing_seller_price,
            Product.category_id,
            Product.commission_fbo_pct,
            func.coalesce(stock_sub.c.present, 0).label("stock_present"),
        )
    )
    if store_id != 0:
        rows = rows.filter(Product.store_id == store_id)
    rows = (
        rows.outerjoin(
            SkuManagement,
            (Product.store_id == SkuManagement.store_id) & (Product.sku_id == SkuManagement.sku_id),
        )
        .outerjoin(stock_sub, Product.sku_id == stock_sub.c.sku_id)
        .filter((SkuManagement.is_archived.is_(None)) | (SkuManagement.is_archived.is_(False)))
        .order_by(Product.name)
        .all()
    )

    return [
        _row_to_item(p, mgmt, p_name, p_offer_id, p_image, p_price, str(p_cat) if p_cat else None, sp, p_commission)
        for p, mgmt, p_name, p_offer_id, p_image, p_price, p_cat, p_commission, sp in rows
    ]


@router.delete("/{sku_id}")
def archive_sku(
    sku_id: int,
    store_id: int = Query(default=1),
    db: Session = Depends(get_db),
):
    """软删除：将 sku_management 记录标记为归档，不再在列表展示

    store_id=0 表示全部店铺：归档该 SKU 在所有店铺的管理记录。
    """
    q = db.query(SkuManagement).filter_by(sku_id=sku_id)
    if store_id != 0:
        q = q.filter_by(store_id=store_id)
    mgmt_rows = q.all()
    if not mgmt_rows:
        # 无管理记录时，直接视为成功（列表本就不应展示额外数据）
        return {"ok": True, "sku_id": sku_id, "archived": False}

    for mgmt in mgmt_rows:
        mgmt.is_archived = True
    db.commit()
    return {"ok": True, "sku_id": sku_id, "archived": True}
