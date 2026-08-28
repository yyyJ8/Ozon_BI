"""
利润分析 API — 从 finance_transactions / postings / ad_sku_daily_stats 原始表直接聚合利润

与 sku_daily_summary 独立，用于验证和纠正现有数据。
日期归因: 有 posting_number → posting.created_at；无 → operation_date。

注意: 如需含采购成本的真实利润，请使用 real_profit.py（/real-profit/*），
它在本模块基础上 JOIN omsprod purchase_order_item 获取采购成本。
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.profit import (
    ProfitOverview,
    ProfitTrendItem,
    ProfitSkuItem,
    ProfitDailyItem,
)
from app.services.ad_spend_adjustment import apply_adjustments, load_active_adjustments

router = APIRouter(prefix="/profit", tags=["profit"])

STORE_ID = Query(default=1, description="店铺 ID，0=全部店铺")


def _to_float(val) -> float:
    if val is None:
        return 0.0
    return float(val)


def _parse_services_logistics(services) -> float:
    """从 services JSON 提取含 'Logistic' 条目的 price 合计"""
    if not services:
        return 0.0
    total = 0.0
    for svc in services:
        name = svc.get("name", "") if isinstance(svc, dict) else ""
        if "Logistic" in name or "logistic" in name:
            total += float(svc.get("price", 0) or 0)
    return total


def _build_posting_date_map(db: Session, store_id: int, date_from: date, date_to: date) -> dict[str, date]:
    """构建 posting_number → created_at.date 映射"""
    store_clause = "store_id = :store_id AND " if store_id != 0 else ""
    params = {"store_id": store_id, "date_from": date_from, "date_to_excl": date_to + timedelta(days=1)}

    rows = db.execute(text(f"""
        SELECT posting_number::text, created_at::date
        FROM ozon.postings
        WHERE {store_clause}created_at >= :date_from AND created_at < :date_to_excl
          AND posting_number IS NOT NULL
    """), params).fetchall()
    return {str(r[0]): r[1] for r in rows if r[0]}


def _ensure_posting_dates(db: Session, store_id: int, posting_numbers: set, date_map: dict[str, date]) -> dict[str, date]:
    """补充 date_map 中缺失的 posting_number（跨期归因）"""
    # 统一转为字符串，避免 DB varchar 与 int 类型不匹配
    str_keys = {str(k) for k in date_map.keys()}
    str_pns = {str(p) for p in posting_numbers}
    missing = str_pns - str_keys
    if not missing:
        return date_map

    store_clause = "store_id = :store_id AND " if store_id != 0 else ""
    pns_list = list(missing)
    rows = db.execute(text(f"""
        SELECT posting_number::text, created_at::date
        FROM ozon.postings
        WHERE {store_clause}posting_number::text = ANY(:pns)
    """), {"store_id": store_id, "pns": pns_list}).fetchall()

    result = dict(date_map)
    for r in rows:
        if r[0] and r[1]:
            result[str(r[0])] = r[1]
    return result


def _aggregate_profit(db: Session, store_id: int, date_from: date, date_to: date,
                      sku_id: Optional[int] = None) -> dict:
    """
    从原始表聚合利润数据，返回 dict:
      - daily: dict[(date, sku_id), {...cost_fields...}]
      - sku_map: dict[sku_id, {...}]
      - overview: dict with totals
    """
    store_clause = "ft.store_id = :store_id AND " if store_id != 0 else ""
    params: dict = {"store_id": store_id, "date_from": date_from, "date_to_excl": date_to + timedelta(days=1)}

    # ── 1. 构建 posting → date 映射 ──
    posting_date_map = _build_posting_date_map(db, store_id, date_from, date_to)

    # ── 2. 加载 finance_transactions ──
    # 2a: 按 operation_date 加载
    extra_where = "AND ft.sku_id = :sku_id" if sku_id else ""
    if sku_id:
        params["sku_id"] = sku_id

    txs_by_date = db.execute(text(f"""
        SELECT ft.operation_id, ft.operation_type, ft.operation_type_name, ft.type,
               ft.operation_date, ft.sku_id, ft.posting_number, ft.delivery_schema,
               ft.amount, ft.accruals_for_sale, ft.sale_commission,
               ft.delivery_charge, ft.return_delivery_charge, ft.services
        FROM ozon.finance_transactions ft
        WHERE {store_clause}ft.operation_date BETWEEN :date_from AND :date_to_excl - INTERVAL '1 day'
          AND ft.sku_id IS NOT NULL
          {extra_where}
    """), params).fetchall()

    # 2b: 按 posting_number 加载（覆盖跨期费用）
    existing_ids = {r[0] for r in txs_by_date}
    all_rows = list(txs_by_date)

    pns_in_range = set(posting_date_map.keys())
    if pns_in_range:
        txs_by_posting = db.execute(text(f"""
            SELECT ft.operation_id, ft.operation_type, ft.operation_type_name, ft.type,
                   ft.operation_date, ft.sku_id, ft.posting_number, ft.delivery_schema,
                   ft.amount, ft.accruals_for_sale, ft.sale_commission,
                   ft.delivery_charge, ft.return_delivery_charge, ft.services
            FROM ozon.finance_transactions ft
            WHERE {store_clause}ft.posting_number::text = ANY(:pns)
              AND ft.sku_id IS NOT NULL
              {extra_where}
        """), {**params, "pns": list(pns_in_range)}).fetchall()

        for r in txs_by_posting:
            if r[0] not in existing_ids:
                all_rows.append(r)
                existing_ids.add(r[0])

    # ── 3. 补充 posting_date_map ──
    all_posting_numbers = {str(r[5]) for r in all_rows if r[5]}  # r[5] = posting_number，统一转 str
    posting_date_map = _ensure_posting_dates(db, store_id, all_posting_numbers, posting_date_map)

    # ── 4. 按 (date, sku_id) 分类聚合 ──
    groups: dict[tuple, dict] = {}

    def _get_group(key: tuple) -> dict:
        if key not in groups:
            groups[key] = {
                "revenue": 0.0,
                "commissions": 0.0,
                "logistics_costs": 0.0,
                "storage_fees": 0.0,
                "advertising": 0.0,
                "promotion_costs": 0.0,
                "returns_amount": 0.0,
                "other_costs": 0.0,
            }
        return groups[key]

    for r in all_rows:
        op_id, op_type, op_name, op_class, op_date, r_sku_id, pn, schema, amt, accruals, commission, delivery, ret_delivery, services = r

        amt_f = _to_float(amt)
        sku = r_sku_id
        pn_str = str(pn) if pn else None

        # 日期归因
        if pn_str and pn_str in posting_date_map:
            attr_date = posting_date_map[pn_str]
        else:
            attr_date = op_date

        key = (attr_date, sku)
        g = _get_group(key)

        # Revenue: type='orders' 的 accruals_for_sale
        if op_class == 'orders':
            g["revenue"] += _to_float(accruals)

        # 分类费用（只处理费用，不处理收入）
        if op_type == "OperationAgentDeliveredToCustomer":
            g["commissions"] += _to_float(commission)
            if services:
                g["logistics_costs"] += _parse_services_logistics(services)
        elif op_type in ("OperationItemReturn", "ClientReturnAgentOperation"):
            g["returns_amount"] += amt_f
            if services:
                g["logistics_costs"] += _parse_services_logistics(services)
        elif op_type and "TemporaryStorage" in op_type:
            g["storage_fees"] += amt_f
        elif op_type == "OperationPromotionWithCostPerOrder":
            g["promotion_costs"] += amt_f
        else:
            if amt_f < 0:
                g["other_costs"] += amt_f

    # ── 5. 推广费 sku_id=NULL 的通过 posting 归因 ──
    promo_rows = db.execute(text(f"""
        SELECT ft.operation_id, ft.amount, ft.posting_number, ft.operation_date
        FROM ozon.finance_transactions ft
        WHERE {store_clause}ft.operation_type = 'OperationPromotionWithCostPerOrder'
          AND ft.operation_date BETWEEN :date_from AND :date_to_excl - INTERVAL '1 day'
    """), params).fetchall()

    if promo_rows:
        # 拿到 posting → skus 映射
        promo_pns = {str(r[2]) for r in promo_rows if r[2]}
        posting_skus: dict[str, list[int]] = {}
        if promo_pns:
            p_rows = db.execute(text(f"""
                SELECT posting_number::text, products
                FROM ozon.postings
                WHERE {'store_id = :store_id AND ' if store_id != 0 else ''}posting_number::text = ANY(:pns)
            """), {**params, "pns": list(promo_pns)}).fetchall()
            for p_row in p_rows:
                prods = p_row[1] or []
                skus = [prod.get("sku") for prod in prods if prod.get("sku")]
                if skus:
                    posting_skus[p_row[0]] = skus

        for pr in promo_rows:
            op_id, amt_f, pn, op_date = pr[0], _to_float(pr[1]), pr[2], pr[3]
            pn_str = str(pn) if pn else None
            if pn_str and pn_str in posting_skus:
                skus_list = posting_skus[pn_str]
                per_sku = amt_f / len(skus_list)
                attr_d = posting_date_map.get(pn_str, op_date)
                for sid in skus_list:
                    g = _get_group((attr_d, sid))
                    g["promotion_costs"] += per_sku
            else:
                # 无 posting → 按当日 revenue 占比分摊
                pass

        # 处理无可匹配 posting 的推广费：按当日 revenue 占比
        unmatched = [pr for pr in promo_rows if not pr[2] or str(pr[2]) not in posting_skus]
        if unmatched:
            daily_unmatched: dict[date, float] = {}
            for pr in unmatched:
                d = pr[3]
                daily_unmatched[d] = daily_unmatched.get(d, 0.0) + _to_float(pr[1])

            if daily_unmatched:
                # 按当日已有各组 revenue 占比分摊
                for d, total_promo in daily_unmatched.items():
                    day_groups = {k: v for k, v in groups.items() if k[0] == d and v["revenue"] > 0}
                    day_total_rev = sum(v["revenue"] for v in day_groups.values())
                    if day_total_rev > 0:
                        for k, v in day_groups.items():
                            share = v["revenue"] / day_total_rev
                            v["promotion_costs"] += total_promo * share

    # ── 6. 广告费 ──
    # 6a: SKU 级精确数据
    ad_rows = db.execute(text(f"""
        SELECT sku_id, stat_date, SUM(spend) AS total_spend
        FROM ozon.ad_sku_daily_stats
        WHERE {'store_id = :store_id AND ' if store_id != 0 else ''}stat_date BETWEEN :date_from AND :date_to_excl - INTERVAL '1 day'
          AND sku_id > 0
        GROUP BY sku_id, stat_date
    """), params).fetchall()

    for ad_row in ad_rows:
        sid, stat_date, spend = ad_row[0], ad_row[1], _to_float(ad_row[2])
        key = (stat_date, sid)
        g = _get_group(key)
        g["advertising"] -= spend  # 广告费为负

    # 6b 已移除: SEARCH_PROMO 按单付费统一走 promotion_costs
    # （OperationPromotionWithCostPerOrder，Finance API 实际结算口径 + posting 级归因），
    # 不再按 revenue 分摊进 advertising，避免同一笔钱重复计费。

    # 6c: 广告花费归因调整（A→B 转移规则，实时应用；store_id=0 跨店聚合时不应用）
    if store_id != 0:
        adjustments = load_active_adjustments(db, store_id)
        apply_adjustments(groups, adjustments, _get_group)

    # ── 7. 计算 net_profit, profit_margin ──
    for key, g in groups.items():
        costs = (g["commissions"] + g["logistics_costs"] + g["storage_fees"]
                 + g["advertising"] + g["promotion_costs"] + g["returns_amount"]
                 + g["other_costs"])
        g["total_costs"] = costs
        g["net_profit"] = g["revenue"] + costs  # costs 都是负数/0
        g["profit_margin"] = (g["net_profit"] / g["revenue"] * 100) if g["revenue"] > 0 else 0.0

    return {
        "groups": groups,
        "posting_date_map": posting_date_map,
    }


# ═══════════════════════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════════════════════


@router.get("/overview", response_model=ProfitOverview)
def profit_overview(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

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

    # ordered_units 从 postings 聚合
    store_clause = "p.store_id = :store_id AND " if store_id != 0 else ""
    units_params = {"store_id": store_id, "date_from": date_from, "date_to_excl": date_to + timedelta(days=1)}
    units_row = db.execute(text(f"""
        SELECT COALESCE(SUM((prod->>'quantity')::int), 0)
        FROM ozon.postings p,
             jsonb_array_elements(p.products) AS prod
        WHERE {store_clause}p.created_at >= :date_from AND p.created_at < :date_to_excl
    """), units_params).fetchone()
    ordered_units = int(units_row[0]) if units_row and units_row[0] else 0

    return ProfitOverview(
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
        ordered_units=ordered_units,
        sku_count=len(skus),
        day_count=len(days),
    )


@router.get("/trend", response_model=list[ProfitTrendItem])
def profit_trend(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    result = _aggregate_profit(db, store_id, date_from, date_to)
    groups = result["groups"]

    daily: dict[date, dict] = {}
    for (d, sid), g in groups.items():
        if d not in daily:
            daily[d] = {k: 0.0 for k in ["revenue", "commissions", "logistics_costs",
                                           "storage_fees", "advertising", "promotion_costs",
                                           "returns_amount", "other_costs"]}
        for k in daily[d]:
            daily[d][k] += g[k]

    result_list = []
    for d in sorted(daily.keys()):
        g = daily[d]
        total_costs = (g["commissions"] + g["logistics_costs"] + g["storage_fees"]
                       + g["advertising"] + g["promotion_costs"] + g["returns_amount"]
                       + g["other_costs"])
        net_profit = g["revenue"] + total_costs
        profit_margin = (net_profit / g["revenue"] * 100) if g["revenue"] > 0 else 0.0

        result_list.append(ProfitTrendItem(
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
        ))

    return result_list


@router.get("/sku-ranking", response_model=list[ProfitSkuItem])
def profit_sku_ranking(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

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

    # 批量获取 product 信息
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

    # ordered_units 从 postings 聚合
    store_clause2 = "p.store_id = :store_id AND " if store_id != 0 else ""
    units_rows = db.execute(text(f"""
        SELECT (prod->>'sku')::bigint AS sku_id, COALESCE(SUM((prod->>'quantity')::int), 0) AS qty
        FROM ozon.postings p,
             jsonb_array_elements(p.products) AS prod
        WHERE {store_clause2}p.created_at >= :date_from AND p.created_at < :date_to_excl
        GROUP BY (prod->>'sku')::bigint
    """), {"store_id": store_id, "date_from": date_from, "date_to_excl": date_to + timedelta(days=1)}).fetchall()

    units_map = {r[0]: r[1] for r in units_rows}

    result_list = []
    for sid, g in sku_data.items():
        total_costs = (g["commissions"] + g["logistics_costs"] + g["storage_fees"]
                       + g["advertising"] + g["promotion_costs"] + g["returns_amount"]
                       + g["other_costs"])
        net_profit = g["revenue"] + total_costs
        profit_margin = (net_profit / g["revenue"] * 100) if g["revenue"] > 0 else 0.0

        pinfo = prod_map.get(sid)
        result_list.append(ProfitSkuItem(
            sku_id=sid,
            offer_id=pinfo[1] if pinfo else None,
            name=pinfo[2] if pinfo else None,
            primary_image=pinfo[3] if pinfo else None,
            revenue=round(g["revenue"], 2),
            costs=round(abs(total_costs), 2),
            net_profit=round(net_profit, 2),
            profit_margin=round(profit_margin, 2),
            ordered_units=int(units_map.get(sid, 0)),
            commissions=round(abs(g["commissions"]), 2),
            logistics_costs=round(abs(g["logistics_costs"]), 2),
            storage_fees=round(abs(g["storage_fees"]), 2),
            advertising=round(abs(g["advertising"]), 2),
            promotion_costs=round(abs(g["promotion_costs"]), 2),
            returns_amount=round(abs(g["returns_amount"]), 2),
            other_costs=round(abs(g["other_costs"]), 2),
            stock_present=int(pinfo[4]) if pinfo else 0,
            stock_reserved=int(pinfo[5]) if pinfo else 0,
        ))

    # 按净利降序
    result_list.sort(key=lambda x: x.net_profit, reverse=True)
    return result_list


@router.get("/sku-daily", response_model=list[ProfitDailyItem])
def profit_sku_daily(
    sku_id: int = Query(...),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    """单个 SKU 的每日利润明细（下钻用）"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

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

    result_list = []
    for d in sorted(daily.keys()):
        g = daily[d]
        total_costs = (g["commissions"] + g["logistics_costs"] + g["storage_fees"]
                       + g["advertising"] + g["promotion_costs"] + g["returns_amount"]
                       + g["other_costs"])
        net_profit = g["revenue"] + total_costs
        profit_margin = (net_profit / g["revenue"] * 100) if g["revenue"] > 0 else 0.0

        result_list.append(ProfitDailyItem(
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
        ))

    return result_list
