"""
真实利润分析 API — 基于 Ozon 平台 P&L + sku_management 的产品成本(¥)

数据来源:
  - Ozon 平台费用: profit.py _aggregate_profit() 实时聚合（finance_transactions）→ 平台毛利
  - 产品成本:      ozon.sku_management.product_cost_rmb（单件全成本 ¥，含采购成本+送仓费+头程×1.06）
  - 汇率:          ozon.sku_management.exchange_rate（本地），未填写的取默认值 13.0

真实净利 = 平台毛利 − 单件产品成本(¥) × 销量 × 汇率

⚠️ 关于偏差的说明:
  本模块的"真实净利"是把单件产品成本(¥) 按销量×汇率折算后，从平台毛利里扣掉得到的**近似值**。
  它用于**经营层面的快速参考**，与公司财务的实际结算口径（真实采购款、头程实付、
  实际换汇/收款手续费、税费、损耗、退货处理等）**可能存在偏差**，偏差是正常的。
  主要偏差来源:
    1. 产品成本 = 采购成本 + 送仓费 + 头程×1.06（含税估算），非实际采购/头程实付单。
    2. 汇率用固定值（默认 13.0，或 sku_management 里的汇率），非按结算日牌价。
    3. 销量用 postings 件数，与财务回款计入的件数日期口径略有出入。
  如需与公司财务对账，请以财务系统为准，本数字仅作经营参考。
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.profit import _aggregate_profit, _to_float
from app.schemas.profit import (
    RealProfitOverview,
    RealProfitSkuItem,
    RealProfitDailyItem,
)

router = APIRouter(prefix="/real-profit", tags=["real-profit"])

STORE_ID = Query(default=1, description="店铺 ID，0=全部店铺")
DEFAULT_EXCHANGE_RATE = 13.0


def _get_product_cost_rmb(db: Session, sku_ids: list[int]) -> dict[int, float]:
    """从本地 sku_management 读取单件产品成本（¥，含采购+送仓+头程）"""
    if not sku_ids:
        return {}

    rows = db.execute(text("""
        SELECT sku_id, product_cost_rmb
        FROM ozon.sku_management
        WHERE sku_id = ANY(:skus) AND product_cost_rmb IS NOT NULL
    """), {"skus": sku_ids}).fetchall()

    result = {}
    for r in rows:
        val = _to_float(r[1])
        if val > 0:
            result[int(r[0])] = val
    return result


def _get_exchange_rates(db: Session, sku_ids: list[int]) -> dict[int, float]:
    """从本地 sku_management 获取每个 SKU 的汇率，未填写的返回默认值 13.0"""
    if not sku_ids:
        return {}

    rows = db.execute(text("""
        SELECT sku_id, exchange_rate
        FROM ozon.sku_management
        WHERE sku_id = ANY(:skus) AND exchange_rate IS NOT NULL
    """), {"skus": sku_ids}).fetchall()

    rates = {}
    for r in rows:
        val = _to_float(r[1])
        if val > 0:
            rates[int(r[0])] = val

    for sid in sku_ids:
        if sid not in rates:
            rates[sid] = DEFAULT_EXCHANGE_RATE
    return rates


def _get_sku_ordered_units(db: Session, store_id: int, date_from: date, date_to: date) -> dict[int, int]:
    """按 SKU 聚合下单件数（postings.created_at 维度）"""
    store_clause = "p.store_id = :store_id AND " if store_id != 0 else ""
    params = {"store_id": store_id, "date_from": date_from, "date_to_excl": date_to + timedelta(days=1)}
    rows = db.execute(text(f"""
        SELECT (prod->>'sku')::bigint AS sku_id, COALESCE(SUM((prod->>'quantity')::int), 0) AS qty
        FROM ozon.postings p,
             jsonb_array_elements(p.products) AS prod
        WHERE {store_clause}p.created_at >= :date_from AND p.created_at < :date_to_excl
        GROUP BY (prod->>'sku')::bigint
    """), params).fetchall()
    return {r[0]: int(r[1] or 0) for r in rows}


# ═══════════════════════════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════════════════════════


@router.get("/overview", response_model=RealProfitOverview)
def real_profit_overview(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    """含产品成本的真实利润总览"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    # ── 1. Ozon 平台 P&L 聚合 ──
    result = _aggregate_profit(db, store_id, date_from, date_to)
    groups = result["groups"]

    total_revenue = 0.0
    total_commissions = 0.0
    total_logistics = 0.0
    total_storage = 0.0
    total_advertising = 0.0
    total_promotion = 0.0
    total_returns = 0.0
    total_other = 0.0
    skus = set()
    days = set()

    for (d, sid), g in groups.items():
        total_revenue += g["revenue"]
        total_commissions += g["commissions"]
        total_logistics += g["logistics_costs"]
        total_storage += g["storage_fees"]
        total_advertising += g["advertising"]
        total_promotion += g["promotion_costs"]
        total_returns += g["returns_amount"]
        total_other += g["other_costs"]
        skus.add(sid)
        days.add(d)

    total_costs = (total_commissions + total_logistics + total_storage
                   + total_advertising + total_promotion + total_returns + total_other)
    net_profit = total_revenue + total_costs
    profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    # ── 2. 产品成本(¥) + 汇率 ──
    sku_list = list(skus)
    units_map = _get_sku_ordered_units(db, store_id, date_from, date_to)
    total_units = sum(units_map.values())

    product_cost_map = _get_product_cost_rmb(db, sku_list)
    exchange_rates = _get_exchange_rates(db, sku_list)

    total_product_cost_rmb = 0.0
    total_product_cost_rub = 0.0
    sku_with_product_cost = 0

    for sid in sku_list:
        units = units_map.get(sid, 0)
        rate = exchange_rates.get(sid, DEFAULT_EXCHANGE_RATE)
        cost = product_cost_map.get(sid, 0.0)
        if cost > 0:
            total_product_cost_rmb += cost * units
            total_product_cost_rub += cost * units * rate
            sku_with_product_cost += 1

    real_net_profit = net_profit - total_product_cost_rub
    real_profit_margin = (real_net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    return RealProfitOverview(
        revenue=round(total_revenue, 2),
        net_profit=round(net_profit, 2),
        profit_margin=round(profit_margin, 2),
        total_costs=round(abs(total_costs), 2),
        total_commissions=round(abs(total_commissions), 2),
        total_logistics=round(abs(total_logistics), 2),
        total_storage=round(abs(total_storage), 2),
        total_advertising=round(abs(total_advertising), 2),
        total_promotion=round(abs(total_promotion), 2),
        total_returns=round(abs(total_returns), 2),
        total_other=round(abs(total_other), 2),
        ordered_units=total_units,
        sku_count=len(skus),
        day_count=len(days),
        total_product_cost_rmb=round(total_product_cost_rmb, 2),
        total_product_cost_rub=round(total_product_cost_rub, 2),
        sku_with_product_cost=sku_with_product_cost,
        real_net_profit=round(real_net_profit, 2),
        real_profit_margin=round(real_profit_margin, 2),
    )


@router.get("/sku-ranking", response_model=list[RealProfitSkuItem])
def real_profit_sku_ranking(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    """含产品成本的 SKU 利润排行"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    # ── 1. Ozon 平台 P&L 聚合 ──
    result = _aggregate_profit(db, store_id, date_from, date_to)
    groups = result["groups"]

    sku_data: dict[int, dict] = {}
    for (d, sid), g in groups.items():
        if sid not in sku_data:
            sku_data[sid] = {k: 0.0 for k in ["revenue", "commissions", "logistics_costs",
                                                "storage_fees", "advertising", "promotion_costs",
                                                "returns_amount", "other_costs"]}
        for k in sku_data[sid]:
            sku_data[sid][k] += g[k]

    if not sku_data:
        return []

    # ── 2. 产品信息 ──
    sku_ids = list(sku_data.keys())
    store_clause = "store_id = :store_id AND " if store_id != 0 else ""
    prod_rows = db.execute(text(f"""
        SELECT sku_id, offer_id, name, primary_image,
               COALESCE((SELECT SUM(present) FROM ozon.stocks WHERE store_id = p.store_id AND sku_id = p.sku_id), 0) AS stock_present,
               COALESCE((SELECT SUM(reserved) FROM ozon.stocks WHERE store_id = p.store_id AND sku_id = p.sku_id), 0) AS stock_reserved
        FROM ozon.products p
        WHERE {store_clause}sku_id = ANY(:skus)
    """), {"store_id": store_id, "skus": sku_ids}).fetchall()
    prod_map = {r[0]: r for r in prod_rows}

    # ── 3. 下单件数 + 产品成本(¥) + 汇率 ──
    units_map = _get_sku_ordered_units(db, store_id, date_from, date_to)
    product_cost_map = _get_product_cost_rmb(db, sku_ids)
    exchange_rates = _get_exchange_rates(db, sku_ids)

    # ── 4. 组装结果 ──
    result_list = []
    for sid, g in sku_data.items():
        total_costs = (g["commissions"] + g["logistics_costs"] + g["storage_fees"]
                       + g["advertising"] + g["promotion_costs"] + g["returns_amount"]
                       + g["other_costs"])
        net_profit = g["revenue"] + total_costs
        profit_margin = (net_profit / g["revenue"] * 100) if g["revenue"] > 0 else 0.0

        pinfo = prod_map.get(sid)
        units = units_map.get(sid, 0)
        rate = exchange_rates.get(sid, DEFAULT_EXCHANGE_RATE)

        # 产品成本(¥ 单件，含采购+送仓+头程)
        p_cost = product_cost_map.get(sid, 0.0)
        has_product_cost = p_cost > 0

        # 真实净利 = 平台净利 - 单件产品成本(¥) × 销量 × 汇率
        cogs_rub = p_cost * units * rate
        real_net = net_profit - cogs_rub
        real_margin = (real_net / g["revenue"] * 100) if g["revenue"] > 0 else 0.0

        result_list.append(RealProfitSkuItem(
            sku_id=sid,
            offer_id=pinfo[1] if pinfo else None,
            name=pinfo[2] if pinfo else None,
            primary_image=pinfo[3] if pinfo else None,
            revenue=round(g["revenue"], 2),
            costs=round(abs(total_costs), 2),
            net_profit=round(net_profit, 2),
            profit_margin=round(profit_margin, 2),
            ordered_units=units,
            commissions=round(abs(g["commissions"]), 2),
            logistics_costs=round(abs(g["logistics_costs"]), 2),
            storage_fees=round(abs(g["storage_fees"]), 2),
            advertising=round(abs(g["advertising"]), 2),
            promotion_costs=round(abs(g["promotion_costs"]), 2),
            returns_amount=round(abs(g["returns_amount"]), 2),
            other_costs=round(abs(g["other_costs"]), 2),
            stock_present=int(pinfo[4]) if pinfo else 0,
            stock_reserved=int(pinfo[5]) if pinfo else 0,
            product_cost_rmb=round(p_cost, 2),
            exchange_rate=round(rate, 4),
            has_product_cost=has_product_cost,
            real_net_profit=round(real_net, 2),
            real_profit_margin=round(real_margin, 2),
        ))

    result_list.sort(key=lambda x: x.real_net_profit, reverse=True)
    return result_list


@router.get("/sku-daily", response_model=list[RealProfitDailyItem])
def real_profit_sku_daily(
    sku_id: int = Query(...),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    """含产品成本的单 SKU 每日利润明细（成本按收入占比分摊到日）"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    # ── 1. Ozon 平台 P&L 聚合 ──
    result = _aggregate_profit(db, store_id, date_from, date_to, sku_id=sku_id)
    groups = result["groups"]

    daily: dict[date, dict] = {}
    for (d, sid), g in groups.items():
        if d not in daily:
            daily[d] = {k: 0.0 for k in ["revenue", "commissions", "logistics_costs",
                                           "storage_fees", "advertising", "promotion_costs",
                                           "returns_amount", "other_costs"]}
        for k in daily[d]:
            daily[d][k] += g[k]

    if not daily:
        return []

    total_revenue = sum(g["revenue"] for g in daily.values())

    # ── 2. 产品成本(¥) + 汇率 ──
    product_cost_map = _get_product_cost_rmb(db, [sku_id])
    exchange_rates = _get_exchange_rates(db, [sku_id])

    p_cost = product_cost_map.get(sku_id, 0.0)
    rate = exchange_rates.get(sku_id, DEFAULT_EXCHANGE_RATE)
    units = _get_sku_ordered_units(db, store_id, date_from, date_to).get(sku_id, 0)

    has_product_cost = p_cost > 0

    # 产品总成本（₽）= 单件成本 ¥ × 销量 × 汇率
    total_product_rub = p_cost * units * rate if has_product_cost else 0.0

    # ── 3. 组装结果（成本按收入占比分摊到日）──
    result_list = []
    for d in sorted(daily.keys()):
        g = daily[d]
        total_costs = (g["commissions"] + g["logistics_costs"] + g["storage_fees"]
                       + g["advertising"] + g["promotion_costs"] + g["returns_amount"]
                       + g["other_costs"])
        net_profit = g["revenue"] + total_costs
        profit_margin = (net_profit / g["revenue"] * 100) if g["revenue"] > 0 else 0.0

        # 按收入占比分摊产品成本
        share = g["revenue"] / total_revenue if total_revenue > 0 else 0.0
        daily_product = total_product_rub * share

        real_net = net_profit - daily_product
        real_margin = (real_net / g["revenue"] * 100) if g["revenue"] > 0 else 0.0

        result_list.append(RealProfitDailyItem(
            date=d,
            revenue=round(g["revenue"], 2),
            costs=round(abs(total_costs), 2),
            net_profit=round(net_profit, 2),
            profit_margin=round(profit_margin, 2),
            commissions=round(abs(g["commissions"]), 2),
            logistics_costs=round(abs(g["logistics_costs"]), 2),
            storage_fees=round(abs(g["storage_fees"]), 2),
            advertising=round(abs(g["advertising"]), 2),
            promotion_costs=round(abs(g["promotion_costs"]), 2),
            returns_amount=round(abs(g["returns_amount"]), 2),
            other_costs=round(abs(g["other_costs"]), 2),
            product_cost_rub=round(daily_product, 2),
            has_product_cost=has_product_cost,
            real_net_profit=round(real_net, 2),
            real_profit_margin=round(real_margin, 2),
        ))

    return result_list
