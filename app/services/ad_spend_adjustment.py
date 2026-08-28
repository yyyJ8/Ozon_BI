"""
广告花费归因调整 — 把 from_sku 的部分广告花费转移到 to_sku

场景: 给 SKU A 投广告，买家进 A 后买了关联的 SKU B，
      Ozon 报告把 spend 记在 A 头上 → A 花费虚高、B 花费虚低。
      本模块按 ad_spend_adjustments 规则，在利润计算时把 A 的花费
      按比例（ratio %）或固定金额（fixed_amount）拨给 B。

原则: 只存规则 + 计算时实时应用，不动 ad_sku_daily_stats 原始数据，
      规则随时可改、可停用、可回滚。
"""
from datetime import date
from decimal import Decimal
from typing import Callable

from loguru import logger
from sqlalchemy.orm import Session

from app.models import AdSpendAdjustment


def load_active_adjustments(db: Session, store_id: int) -> list[AdSpendAdjustment]:
    """加载某店铺全部启用的调整规则（当前计算仅支持全局规则，campaign_id 为空的）"""
    rules = db.query(AdSpendAdjustment).filter(
        AdSpendAdjustment.store_id == store_id,
        AdSpendAdjustment.is_active.is_(True),
    ).all()
    # 按活动维度（campaign_id 非空）的规则当前计算不支持，记录日志并跳过
    skipped = [r for r in rules if r.campaign_id]
    if skipped:
        logger.warning(f"广告归因调整: {len(skipped)} 条按活动维度规则暂不支持，跳过 "
                       f"(ids={[r.id for r in skipped]})")
    return [r for r in rules if not r.campaign_id]


def _transfer_amount(rule: AdSpendAdjustment, day_spend, day: date) -> float:
    """计算某天 from_sku 应转出的金额（advertising 为负数，返回正数转移额）"""
    if rule.date_from and day < rule.date_from:
        return 0.0
    if rule.date_to and day > rule.date_to:
        return 0.0
    if rule.ratio is not None:
        return abs(float(day_spend)) * float(rule.ratio) / 100.0
    if rule.fixed_amount is not None:
        return float(rule.fixed_amount)
    return 0.0


def _add_amount(current, delta: float):
    """类型感知增量：cost_service 用 Decimal，profit.py 用 float"""
    if isinstance(current, Decimal):
        return current + Decimal(str(delta))
    return current + delta


def apply_adjustments(
    groups: dict[tuple, dict],
    adjustments: list[AdSpendAdjustment],
    get_group: Callable[[tuple], dict],
) -> dict[int, float]:
    """
    就地修改 groups，按规则把 from_sku 每日广告花费的一部分转移到 to_sku。

    groups:    {(date, sku_id): {"advertising": 负数, ...}}
    get_group: 调用方的 _get_group(key)，to_sku 当天无组时自动创建完整结构
    返回:      {rule_id: 累计转移金额}（便于日志/前端）
    """
    applied: dict[int, float] = {}
    if not adjustments:
        return applied

    total_transferred = 0.0
    for rule in adjustments:
        rule_transferred = 0.0
        for (day, sku_id), g in list(groups.items()):
            if sku_id != rule.from_sku_id or g["advertising"] >= 0:
                continue
            transfer = _transfer_amount(rule, g["advertising"], day)
            if transfer <= 0:
                continue
            # 转出: from_sku 的广告费（负数）绝对值减小 → 加回 transfer
            g["advertising"] = _add_amount(g["advertising"], transfer)
            # 转入: to_sku 的广告费增加（负数绝对值增大）→ 减 transfer
            to_group = get_group((day, rule.to_sku_id))
            to_group["advertising"] = _add_amount(to_group["advertising"], -transfer)
            rule_transferred += transfer
            total_transferred += transfer

        if rule_transferred > 0:
            applied[rule.id] = rule_transferred
            logger.info(
                f"广告归因调整 rule#{rule.id}: {rule.from_sku_id} → {rule.to_sku_id} "
                f"累计转移 {rule_transferred:.2f} ₽"
            )

    if total_transferred > 0:
        logger.info(f"广告归因调整合计: {total_transferred:.2f} ₽")
    return applied
