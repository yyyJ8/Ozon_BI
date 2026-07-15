"""
订单履约同步 — 从 Posting API 拉取订单履约数据，写入 postings

策略:
  1. 增量 — 从 list API 拉最近 N 天（新创建 / 状态变更的 posting）
  2. 补齐 — 从 finance_transactions 中取未入库的 posting_number，
           逐条调 get API 补全（financetx 里有 posting_number 但 postings 表没有的）

用途:
  1. 退货归因 — posting_number → created_at 找到原销售日期
  2. 漏斗分析 — delivered / cancelled 口径的成交统计
"""
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.clients.ozon import OzonClient
from app.models import Posting


def _parse_dt(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        s = val.replace("Z", "+00:00")
        return datetime.fromisoformat(s).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _parse_products(raw_products: Optional[list]) -> list[dict]:
    if not raw_products:
        return []
    return [
        {"sku": p.get("sku"), "name": p.get("name"),
         "quantity": p.get("quantity"), "offer_id": p.get("offer_id"),
         "price": p.get("price")}
        for p in raw_products
    ]


def _upsert_posting(db: Session, p: dict, delivery_schema: Optional[str] = None) -> bool:
    """插入或更新一条 posting，返回 True=新增, False=跳过"""
    posting_number = p.get("posting_number")
    if not posting_number:
        return False

    products = _parse_products(p.get("products"))
    data = {
        "posting_number": posting_number,
        "order_number": p.get("order_number"),
        "delivery_schema": p.get("delivery_schema") or delivery_schema,
        "status": p.get("status"),
        "cancel_reason_id": p.get("cancel_reason_id", 0) or 0,
        "created_at": _parse_dt(p.get("created_at")),
        "in_process_at": _parse_dt(p.get("in_process_at")),
        "delivered_at": _parse_dt(
            p.get("delivery_date")
            or p.get("fact_delivery_date")
            or (p.get("financial_data") or {}).get("delivery_date")
        ),
        "products": products if products else None,
    }

    stmt = pg_insert(Posting).values(**data).on_conflict_do_update(
        index_elements=["posting_number"],
        set_={
            "status": data["status"],
            "cancel_reason_id": data["cancel_reason_id"],
            "in_process_at": data["in_process_at"],
            "delivered_at": data["delivered_at"],
            "products": data["products"],
            "synced_at": datetime.now(),
        },
    )
    result = db.execute(stmt)
    return result.rowcount > 0


def sync_postings(db: Session, client: OzonClient,
                  date_from: str, date_to: str,
                  batch_id: Optional[str] = None) -> dict:
    """
    同步订单履约数据: 增量 list + 补齐 get
    """
    logger.info(f"=== 开始同步订单履约: {date_from} ~ {date_to} ===")

    if not batch_id:
        batch_id = f"posting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    list_inserted = 0
    list_updated = 0

    # ── Phase 1: 增量拉取 list API ──
    for schema in ("FBO", "FBS"):
        try:
            logger.info(f"  增量拉取 {schema} ({date_from} ~ {date_to})...")
            postings = client.get_all_postings(date_from, date_to, schema=schema)
            logger.info(f"  {schema}: {len(postings)} 条")
            for p in postings:
                if p.get("delivery_schema") is None:
                    p["delivery_schema"] = schema
                if _upsert_posting(db, p):
                    list_inserted += 1
                else:
                    list_updated += 1
            db.commit()
        except Exception as e:
            logger.warning(f"  {schema} list 拉取失败: {e}")

    # ── Phase 2: 从 finance_transactions 补齐缺失的 posting ──
    missing = db.execute(text("""
        SELECT DISTINCT ft.posting_number
        FROM ozon.finance_transactions ft
        WHERE ft.posting_number IS NOT NULL
          AND ft.posting_number NOT IN (SELECT posting_number FROM ozon.postings)
        LIMIT 200
    """)).fetchall()

    get_inserted = 0
    get_failed = 0

    if missing:
        logger.info(f"  补齐缺失 posting: {len(missing)} 个")
        for i, (pn,) in enumerate(missing):
            detail = client.get_posting_detail(pn)
            if detail:
                _upsert_posting(db, detail)
                get_inserted += 1
            else:
                get_failed += 1
            if (i + 1) % 50 == 0:
                db.commit()
                logger.info(f"    补齐进度: {i + 1}/{len(missing)}")
        db.commit()

    total = list_inserted + list_updated + get_inserted
    logger.info(
        f"订单履约同步完成: list={list_inserted}+{list_updated}, "
        f"补齐={get_inserted}(失败{get_failed}), 合计={total}"
    )
    return {
        "posting_list_inserted": list_inserted,
        "posting_list_updated": list_updated,
        "posting_get_inserted": get_inserted,
        "posting_get_failed": get_failed,
    }
