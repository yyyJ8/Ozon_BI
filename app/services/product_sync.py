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

    # 4. v5 价格同步：获取 marketing_seller_price
    offer_ids = db.execute(
        text("SELECT offer_id FROM ozon.products WHERE store_id = :sid AND offer_id IS NOT NULL"),
        {"sid": store_id},
    ).fetchall()
    offer_list = [r[0] for r in offer_ids if r[0]]
    prices_updated = 0
    if offer_list:
        try:
            price_items = client.get_product_prices_v5(offer_list)
            for item in price_items:
                oid = item.get("offer_id")
                p = item.get("price") or {}
                msp = _parse_price(p.get("marketing_seller_price"))
                if oid and msp is not None:
                    db.execute(
                        text("UPDATE ozon.products SET marketing_seller_price = :msp, updated_at = :now WHERE store_id = :sid AND offer_id = :oid"),
                        {"msp": msp, "now": now, "sid": store_id, "oid": oid},
                    )
                    prices_updated += 1
            db.commit()
            logger.info(f"[store={store_id}] v5 促销价更新: {prices_updated} 商品")
        except Exception as e:
            logger.warning(f"[store={store_id}] v5 价格同步失败: {e}")
            db.rollback()
    return {"products_updated": products_updated, "stocks_upserted": stocks_upserted}


def sync_stocks_v4(db: Session, client: OzonClient, store_id: int) -> dict:
    """
    从 v4 专用库存接口拉取并更新 stocks 表。

    用 product_id 精确查询（而非 visibility=ALL 全量扫描），
    确保已归档/下架商品的库存也能被更新到 0。
    """
    logger.info(f"=== [store={store_id}] 开始同步库存 (v4) ===")
    now = datetime.now()

    # 先拉取该店铺所有 product_id，包括已归档的
    from app.models import Product
    all_product_ids = [row[0] for row in db.query(Product.product_id).filter(
        Product.store_id == store_id
    ).distinct().all()]

    if not all_product_ids:
        logger.warning(f"[store={store_id}] 无商品，跳过库存同步")
        return {"stocks_upserted": 0}

    # 分批查询（API 限制 1000 个 id / 请求）
    all_items: list[dict] = []
    batch_size = 1000
    for i in range(0, len(all_product_ids), batch_size):
        batch = all_product_ids[i:i + batch_size]
        resp = client._request("/v4/product/info/stocks", {
            "filter": {"product_id": batch},
            "limit": batch_size,
        })
        all_items.extend(resp.get("items", []))

    logger.info(f"[store={store_id}] v4 stocks: 查询 {len(all_product_ids)} 个商品, 返回 {len(all_items)} 条")

    upserted = 0
    seen_skus: set[tuple[int, str]] = set()
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
            seen_skus.add((int(sku_id), source))

    # API 可能不返回库存为 0 的已归档商品，对这些商品手动置 0
    for pid in all_product_ids:
        p = db.query(Product).filter(Product.product_id == pid, Product.store_id == store_id).first()
        if p and (p.sku_id, "fbo") not in seen_skus:
            s_data = {
                "store_id": store_id,
                "sku_id": p.sku_id,
                "source": "fbo",
                "present": 0,
                "reserved": 0,
                "updated_at": now,
            }
            stmt = pg_insert(Stock).values(**s_data).on_conflict_do_update(
                index_elements=["store_id", "sku_id", "source"],
                set_={"present": 0, "reserved": 0, "updated_at": now},
            )
            db.execute(stmt)
            upserted += 1

    db.commit()
    logger.info(f"[store={store_id}] 库存同步完成 (v4): {upserted} 条")
    return {"stocks_upserted": upserted}
