"""
财务流水同步 — 从 Finance API 拉取交易明细，写入 finance_transactions
"""
from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.clients.ozon import OzonClient
from app.models import FinanceTransaction


def _parse_amount(val) -> Optional[float]:
    if val is None or val == "":
        return 0.0
    return float(val)


def _fmt_timestamp(dt_str: str) -> str:
    """将 '2026-06-14' 转为 RFC 3339（统一用当天起始时间）"""
    if "T" in dt_str:
        return dt_str
    return dt_str.split(" ")[0] + "T00:00:00Z"


def sync_finance(db: Session, client: OzonClient,
                 date_from: str, date_to: str,
                 batch_id: Optional[str] = None) -> dict:
    """
    同步财务流水
    注意: finance API 每次最多查 30 天范围
    """
    logger.info(f"=== 开始同步财务流水: {date_from} ~ {date_to} ===")

    if not batch_id:
        batch_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 用 RFC 3339 格式请求
    api_from = _fmt_timestamp(date_from)
    api_to = _fmt_timestamp(date_to)

    operations = client.get_all_finance(api_from, api_to)
    logger.info(f"finance 返回 {len(operations)} 条记录")

    inserted = 0
    skipped = 0

    for op in operations:
        items = op.get("items", [])
        first_item = items[0] if items else {}
        posting = op.get("posting", {})

        # 操作日期: API 返回 "2026-06-14 00:00:00" 格式
        op_date_str = op.get("operation_date", "")[:10]

        data = {
            "operation_id": op.get("operation_id"),
            "operation_type": op.get("operation_type", ""),
            "operation_type_name": op.get("operation_type_name"),
            "type": op.get("type"),
            "operation_date": op_date_str,
            "sku_id": first_item.get("sku"),
            "item_name": first_item.get("name"),
            "posting_number": posting.get("posting_number"),
            "delivery_schema": posting.get("delivery_schema"),
            "amount": _parse_amount(op.get("amount")),
            "accruals_for_sale": _parse_amount(op.get("accruals_for_sale")),
            "sale_commission": _parse_amount(op.get("sale_commission")),
            "delivery_charge": _parse_amount(op.get("delivery_charge")),
            "return_delivery_charge": _parse_amount(op.get("return_delivery_charge")),
            "services": op.get("services"),
            "items": items,
            "sync_batch_id": batch_id,
        }

        stmt = pg_insert(FinanceTransaction).values(**data).on_conflict_do_nothing(
            index_elements=["operation_id"],
        )
        result = db.execute(stmt)
        if result.rowcount:
            inserted += 1
        else:
            skipped += 1

    db.commit()
    logger.info(f"财务同步完成: {inserted} 新增, {skipped} 跳过(重复)")
    return {"finance_inserted": inserted, "finance_skipped": skipped}
