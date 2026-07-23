"""
商品数据同步 — 从 Ozon API 拉取商品和库存，写入 products + stocks 表
"""
from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.clients.ozon import OzonClient
from app.models import Product, Stock


def _parse_price(val) -> Optional[float]:
    """解析 Ozon 价格字段（可能是 "" 或 None）"""
    if not val or val == "":
        return None
    return float(val)


def sync_products(db: Session, client: OzonClient, store_id: int) -> dict:
    """
    同步商品主数据和库存
    流程: 拉 product_list → 拉 product_info → upsert products → upsert stocks
    返回: {products_updated, stocks_upserted}
    """
    logger.info(f"=== [store={store_id}] 开始同步商品 ===")

    # 1. 拉取 product_list（获取所有 product_id）
    product_list = client.get_product_list()
    logger.info(f"[store={store_id}] product_list: {len(product_list)} 条")

    # 2. 提取 product_id 并拉取详情
    product_ids = list(set(p["product_id"] for p in product_list if p.get("product_id")))
    product_infos = client.get_product_info(product_ids)
    logger.info(f"[store={store_id}] product_info: {len(product_infos)} 条")

    # 3. Upsert products
    now = datetime.now()
    products_updated = 0
    stocks_to_insert: list[dict] = []

    for info in product_infos:
        commissions = info.get("commissions", [])
        fbo_commission = next(
            (c for c in commissions if c.get("sale_schema") == "FBO"),
            None,
        )
        primary_images = info.get("primary_image", [])

        product_data = {
            "store_id": store_id,
            "sku_id": info.get("sku"),
            "product_id": info.get("id"),
            "name": info.get("name"),
            "offer_id": info.get("offer_id"),
            "category_id": info.get("description_category_id"),
            "barcode": (info.get("barcodes") or [None])[0],
            "price": _parse_price(info.get("price")),
            "old_price": _parse_price(info.get("old_price")),
            "min_price": _parse_price(info.get("min_price")),
            "commission_fbo_pct": fbo_commission.get("percent") / 100 if fbo_commission else None,
            "volume_weight": _parse_price(info.get("volume_weight")),
            "status": info.get("statuses", {}).get("status"),
            "is_archived": info.get("is_archived", False),
            "images": info.get("images"),
            "primary_image": primary_images[0] if primary_images else None,
            "updated_at": now,
        }

        stmt = pg_insert(Product).values(**product_data).on_conflict_do_update(
            constraint=Product.__table__.primary_key,
            set_=product_data,
        )
        db.execute(stmt)
        products_updated += 1

        # 4. 收集库存数据
        stocks_data = info.get("stocks", {}).get("stocks", [])
        for s in stocks_data:
            stocks_to_insert.append({
                "store_id": store_id,
                "sku_id": s.get("sku", info.get("sku")),
                "present": s.get("present", 0),
                "reserved": s.get("reserved", 0),
                "source": s.get("source", "fbo"),
                "updated_at": now,
            })

    # 5. Upsert stocks
    stocks_upserted = 0
    for s_data in stocks_to_insert:
        stmt = pg_insert(Stock).values(**s_data).on_conflict_do_update(
            index_elements=["store_id", "sku_id", "source"],
            set_={
                "present": s_data["present"],
                "reserved": s_data["reserved"],
                "updated_at": now,
            },
        )
        db.execute(stmt)
        stocks_upserted += 1

    db.commit()
    logger.info(f"[store={store_id}] 商品同步完成: {products_updated} 商品, {stocks_upserted} 库存")
    return {"products_updated": products_updated, "stocks_upserted": stocks_upserted}


def sync_stocks_v4(db: Session, client: OzonClient, store_id: int) -> dict:
    """
    从 v4 专用库存接口全量拉取并更新 stocks 表（独立于商品同步）
    v4 返回 type 字段(如 "fbo")，映射到 stocks.source
    """
    logger.info(f"=== [store={store_id}] 开始同步库存 (v4) ===")
    now = datetime.now()

    all_items: list[dict] = []
    cursor = ""
    while True:
        resp = client._request("/v4/product/info/stocks", {
            "filter": {"visibility": "ALL"},
            "limit": 1000,
            "cursor": cursor,
        })
        items = resp.get("items", [])
        all_items.extend(items)
        cursor = resp.get("cursor", "")
        if not cursor or not items:
            break
    logger.info(f"[store={store_id}] v4 stocks: 拉取 {len(all_items)} 个商品")

    upserted = 0
    for item in all_items:
        for s in item.get("stocks", []):
            sku_id = s.get("sku")
            if not sku_id:
                continue
            source = s.get("type", "fbo")
            s_data = {
                "store_id": store_id,
                "sku_id": int(sku_id),
                "source": source,
                "present": s.get("present", 0) or 0,
                "reserved": s.get("reserved", 0) or 0,
                "updated_at": now,
            }
            stmt = pg_insert(Stock).values(**s_data).on_conflict_do_update(
                index_elements=["store_id", "sku_id", "source"],
                set_={
                    "present": s_data["present"],
                    "reserved": s_data["reserved"],
                    "updated_at": now,
                },
            )
            db.execute(stmt)
            upserted += 1

    db.commit()
    logger.info(f"[store={store_id}] 库存同步完成 (v4): {upserted} 条")
    return {"stocks_upserted": upserted}
