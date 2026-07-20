"""
退货数据同步 — 从 Returns API 拉取退货数据，写入 returns 表

策略:
  1. 按时间范围全量拉取（游标分页）
  2. 每次 UPSERT（以 id 为主键，状态变化时更新）

用途:
  1. 区分 Cancellation（未签收退回）vs ClientReturn（签收后退回）
  2. 退货原因归因 — return_reason_name → category 映射
  3. 退货时效分析 — returned_at → finished_at
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from loguru import logger
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.clients.ozon import OzonClient
from app.models import Return

# 终态：这些状态下的退货不会再变化
END_STATUSES = {"ReturnedToOzon", "ReceivedBySeller", "Utilized", "WriteOff"}


def _parse_dt(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        s = val.replace("Z", "+00:00")
        return datetime.fromisoformat(s).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _parse_price(val) -> Optional[Decimal]:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (ValueError, TypeError, ArithmeticError):
        return None


def _extract_return_row(r: dict) -> dict:
    """从 Ozon API 原始返回对象提取入库字段"""
    product = r.get("product") or {}
    logistic = r.get("logistic") or {}
    visual = r.get("visual") or {}
    visual_status_obj = visual.get("status") or {}

    visual_status = visual_status_obj.get("sys_name", "")
    status_changed_at = _parse_dt(visual.get("change_moment"))
    return_date = _parse_dt(logistic.get("return_date"))
    final_moment = _parse_dt(logistic.get("final_moment"))

    # 完结时间：优先取 final_moment，没有则用 status_changed_at（终态兜底）
    finished_at = None
    if visual_status in END_STATUSES:
        finished_at = final_moment or status_changed_at

    return {
        "id": r["id"],
        "posting_number": r.get("posting_number", ""),
        "sku": product.get("sku"),
        "type": r.get("type", ""),
        "return_reason_name": r.get("return_reason_name"),
        "quantity": product.get("quantity", 0) or 0,
        "price": _parse_price(product.get("price", {}).get("price")),
        "visual_status": visual_status,
        "status_changed_at": status_changed_at,
        "returned_at": return_date,
        "finished_at": finished_at,
        "schema": r.get("schema", "").capitalize(),
    }


def sync_returns(db: Session, client: OzonClient,
                 date_from: str, date_to: str,
                 batch_id: Optional[str] = None) -> dict:
    """
    同步退货数据: FBO + FBS，全量拉取指定时间范围
    """
    logger.info(f"=== 开始同步退货数据: {date_from} ~ {date_to} ===")

    if not batch_id:
        batch_id = f"returns_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    total_processed = 0

    for schema in ("FBO", "FBS"):
        try:
            logger.info(f"  拉取 {schema} 退货 ({date_from} ~ {date_to})...")
            returns_raw = client.get_all_returns(date_from, date_to, schema=schema)
            logger.info(f"  {schema}: {len(returns_raw)} 条")

            batch_processed = 0
            for r in returns_raw:
                data = _extract_return_row(r)
                if not data["sku"]:
                    continue  # 没有 SKU 的异常数据跳过

                stmt = pg_insert(Return).values(**data).on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "visual_status": data["visual_status"],
                        "status_changed_at": data["status_changed_at"],
                        "finished_at": data["finished_at"],
                        "synced_at": datetime.now(),
                    },
                )
                db.execute(stmt)
                batch_processed += 1

            db.commit()
            logger.info(f"    {schema}: {batch_processed} 条写入")
            total_processed += batch_processed

        except Exception as e:
            logger.error(f"  {schema} 退货同步失败: {e}")
            db.rollback()

    logger.info(f"退货同步完成: 合计 {total_processed} 条")
    return {
        "returns_processed": total_processed,
    }
