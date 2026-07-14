"""
汇总构建服务 — 从 finance_transactions 聚合，更新 sku_daily_summary 的费用字段

聚合逻辑:
  commissions     ← sale_commission WHERE operation_type = 'OperationAgentDeliveredToCustomer'
  returns_amount  ← amount WHERE operation_type IN ('OperationItemReturn', 'ClientReturnAgentOperation')
  logistics_costs ← services[].price (where name contains Logistic)
                   仅从销售单（OperationAgentDeliveredToCustomer）提取，因为 amount 是净额不包含物流
                   其他类型的 amount 已含物流费，提取会重复计算
  storage_fees    ← amount WHERE operation_type LIKE '%TemporaryStorage%'
  advertising     ← amount WHERE operation_type = 'OperationMarketplaceCostPerClick'
  promotion_costs ← amount WHERE operation_type = 'OperationPromotionWithCostPerOrder'
  other_costs     ← 剩余所有负 amount（银行手续费、转运、包装、销毁等）

  net_profit    = revenue + commissions + returns + logistics + storage + advertising + promotion + other
  profit_margin = net_profit / revenue * 100
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.models import FinanceTransaction, SkuDailySummary


def _parse_amount(val) -> Decimal:
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def _get_logistics_from_services(services: Optional[list]) -> Decimal:
    """从 services JSONB 中提取物流费用（已在 API 中为负数）"""
    if not services:
        return Decimal("0")
    total = Decimal("0")
    for s in services:
        if "Logistic" in s.get("name", ""):
            total += _parse_amount(s.get("price"))
    return total


def build_summary(db: Session, start_date: date, end_date: date) -> dict:
    """
    按日期范围构建/更新 sku_daily_summary 的费用字段。
    保留 ordered_units 和 revenue（来自 analytics_sync）。
    """
    logger.info(f"=== 开始构建日汇总: {start_date} ~ {end_date} ===")

    # 1. 拉取有 SKU 关联的财务记录
    txs = db.query(FinanceTransaction).filter(
        FinanceTransaction.operation_date.between(start_date, end_date),
        FinanceTransaction.sku_id.isnot(None),
    ).all()
    logger.info(f"finance_records（有 SKU）: {len(txs)} 条")

    # 2. 按 (date, sku_id) 分组，逐条分类
    groups: dict[tuple, dict] = {}

    def _get(key):
        if key not in groups:
            groups[key] = {
                "commissions": Decimal("0"),
                "returns_amount": Decimal("0"),
                "logistics_costs": Decimal("0"),
                "storage_fees": Decimal("0"),
                "advertising": Decimal("0"),
                "promotion_costs": Decimal("0"),
                "other_costs": Decimal("0"),
            }
        return groups[key]

    for tx in txs:
        key = (tx.operation_date, tx.sku_id)
        g = _get(key)
        amt = _parse_amount(tx.amount)
        optype = tx.operation_type or ""

        if optype == "OperationAgentDeliveredToCustomer":
            # 销售单: amount 是已扣除费用的净收入（正数）
            # 费用藏在 sale_commission 和 services[] 中
            g["commissions"] += _parse_amount(tx.sale_commission)
            g["logistics_costs"] += _get_logistics_from_services(tx.services)

        elif optype in ("OperationItemReturn", "ClientReturnAgentOperation"):
            # 退货: amount 已含物流费，只记 amount，不从 services 重复提取
            g["returns_amount"] += amt

        elif "TemporaryStorage" in optype:
            g["storage_fees"] += amt

        elif optype == "OperationMarketplaceCostPerClick":
            g["advertising"] += amt

        elif optype == "OperationPromotionWithCostPerOrder":
            g["promotion_costs"] += amt

        else:
            # 其他: 银行手续费、交叉转运、包装、销毁、入仓溢缺等
            if amt < 0:
                g["other_costs"] += amt

    logger.info(f"分组聚合: {len(groups)} 个 (date, sku) 组合")

    # 3. 更新 sku_daily_summary
    updated = 0
    for (op_date, sku_id), vals in groups.items():
        summary = db.query(SkuDailySummary).filter(
            SkuDailySummary.record_date == op_date,
            SkuDailySummary.sku_id == sku_id,
        ).first()

        if not summary:
            summary = SkuDailySummary(
                record_date=op_date,
                sku_id=sku_id,
            )
            db.add(summary)

        # 更新费用字段
        summary.returns_amount = vals["returns_amount"]
        summary.commissions = vals["commissions"]
        summary.logistics_costs = vals["logistics_costs"]
        summary.storage_fees = vals["storage_fees"]
        summary.advertising = vals["advertising"]
        summary.other_costs = vals["other_costs"]

        # 净利润 = revenue + 所有费用（费用已经是负数）
        total_costs = (
            vals["commissions"]
            + vals["returns_amount"]
            + vals["logistics_costs"]
            + vals["storage_fees"]
            + vals["advertising"]
            + vals["promotion_costs"]
            + vals["other_costs"]
        )
        rev = _parse_amount(summary.revenue)
        summary.net_profit = rev + total_costs

        # 利润率
        if rev > 0:
            summary.profit_margin = (summary.net_profit / rev * 100).quantize(Decimal("0.01"))
        else:
            summary.profit_margin = Decimal("0")

        summary.data_quality = "complete"
        updated += 1

    db.commit()
    logger.info(f"汇总构建完成: 更新 {updated} 行")
    return {"summary_updated": updated}
