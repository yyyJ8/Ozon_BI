"""补货提示服务 — 聚合数据并计算公式"""
import math
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, text

from app.database import SessionLocal
from app.models import (
    ReplenishmentConfig, Product, Stock,
    SkuDailySummary, SkuManagement,
)


def get_replenishment_data(store_id: int = 0) -> list[dict]:
    """获取所有 SKU 的补货提示数据（含公式计算结果）。

    以 ozon.products 为主表 LEFT JOIN 补货配置，因此**即使某商品没有配置
    安全/物流天数也会展示**（此时天数用默认值 5/45 兜底，configured=False）。

    Args:
        store_id: 店铺 ID，0 = 全部店铺

    Returns:
        补货行列表，每行包含输入数据、中间结果和最终建议
    """
    db = SessionLocal()
    try:
        today = date.today()

        # ── 1. 查询商品 + 关联配置/管理 ────────────────────────
        product_query = db.query(
            Product,
            ReplenishmentConfig,
            SkuManagement,
        ).outerjoin(
            ReplenishmentConfig,
            (Product.store_id == ReplenishmentConfig.store_id)
            & (Product.offer_id == ReplenishmentConfig.offer_id),
        ).outerjoin(
            SkuManagement,
            (Product.store_id == SkuManagement.store_id)
            & (Product.sku_id == SkuManagement.sku_id),
        )

        if store_id != 0:
            product_query = product_query.filter(Product.store_id == store_id)

        product_rows = product_query.all()

        if not product_rows:
            return []

        all_sku_ids = [p.sku_id for p, _, _ in product_rows]
        offer_to_sku = {
            p.offer_id: p.sku_id for p, _, _ in product_rows if p.offer_id
        }
        offer_ids = list(offer_to_sku.keys())

        # ── 2. 库存 ───────────────────────────────────────
        stock_query = (
            db.query(Stock.sku_id, func.coalesce(func.sum(Stock.present), 0))
            .filter(Stock.sku_id.in_(all_sku_ids))
        )
        if store_id != 0:
            stock_query = stock_query.filter(Stock.store_id == store_id)
        stock_map = {sku: int(s) for sku, s in stock_query.group_by(Stock.sku_id).all()}

        # ── 3. 销量（3/7/14/30天）: ordered - cancelled - client_return ──
        periods = {
            "sales_3d": (today - timedelta(days=3), today - timedelta(days=1)),
            "sales_7d": (today - timedelta(days=7), today - timedelta(days=1)),
            "sales_14d": (today - timedelta(days=14), today - timedelta(days=1)),
            "sales_30d": (today - timedelta(days=30), today - timedelta(days=1)),
        }

        sales_map = {sku: {k: 0 for k in periods} for sku in all_sku_ids}

        for key, (d_from, d_to) in periods.items():
            # ordered_units
            q_ordered = (
                db.query(SkuDailySummary.sku_id, func.coalesce(func.sum(SkuDailySummary.ordered_units), 0))
                .filter(
                    SkuDailySummary.sku_id.in_(all_sku_ids),
                    SkuDailySummary.record_date >= d_from,
                    SkuDailySummary.record_date <= d_to,
                )
            )
            if store_id != 0:
                q_ordered = q_ordered.filter(SkuDailySummary.store_id == store_id)
            ordered_map = {sku: int(cnt) for sku, cnt in q_ordered.group_by(SkuDailySummary.sku_id).all()}

            # cancelled_units
            q_cancelled = (
                db.query(SkuDailySummary.sku_id, func.coalesce(func.sum(SkuDailySummary.cancelled_units), 0))
                .filter(
                    SkuDailySummary.sku_id.in_(all_sku_ids),
                    SkuDailySummary.record_date >= d_from,
                    SkuDailySummary.record_date <= d_to,
                )
            )
            if store_id != 0:
                q_cancelled = q_cancelled.filter(SkuDailySummary.store_id == store_id)
            cancelled_map = {sku: int(cnt) for sku, cnt in q_cancelled.group_by(SkuDailySummary.sku_id).all()}

            # client_return_units (returns type='ClientReturn', 按 posting.created_at 归因)
            return_rows = db.execute(
                text("""
                    SELECT r.sku, COALESCE(SUM(r.quantity), 0) AS client_return
                    FROM ozon.returns r
                    JOIN ozon.postings p ON r.posting_number = p.posting_number AND r.store_id = p.store_id
                    WHERE r.type = 'ClientReturn'
                      AND p.created_at >= :d_from
                      AND p.created_at  < :d_to_excl
                      AND r.sku = ANY(:sku_ids)
                      AND r.store_id = :store_id
                    GROUP BY r.sku
                """),
                {
                    "d_from": d_from,
                    "d_to_excl": d_to + timedelta(days=1),
                    "sku_ids": all_sku_ids,
                    "store_id": store_id if store_id != 0 else 1,  # returns 目前只在 store 1
                },
            ).fetchall()
            client_return_map = {row[0]: int(row[1]) for row in return_rows}

            # 实际成交 = ordered - cancelled - client_return
            for sku in all_sku_ids:
                sales_map[sku][key] = max(
                    0,
                    ordered_map.get(sku, 0) - cancelled_map.get(sku, 0) - client_return_map.get(sku, 0),
                )

        # ── 4. 跨境在途（ozon_direct_shipment，按货号+渠道拆分）────
        # 口径：直发表 receiving_status='已收到'（货代已收货=已发运）且未上架
        #      （排除 cargo_shipments 中 cargo_status='已上架' 的申购单），
        #      按 货号 + logistics_provider 聚合 total_qty；
        #      货号匹配不到 products 的直接跳过（不做额外处理）。
        #      渠道: SDK/运盟/昆仑/超光速；未知渠道归入超光速(cgs)。
        channel_map: dict[int, dict[str, int]] = {}
        if offer_ids:
            listed_prs = db.execute(
                text("SELECT DISTINCT pr_no FROM ozon.cargo_shipments WHERE cargo_status = '已上架' AND pr_no IS NOT NULL")
            ).scalars().all() or [""]
            cross_rows = db.execute(
                text("""
                    SELECT d.sku, COALESCE(d.logistics_provider, '') AS provider, COALESCE(SUM(d.total_qty), 0) AS qty
                    FROM ozon.ozon_direct_shipment d
                    WHERE d.is_deleted = false
                      AND d.receiving_status = '已收到'
                      AND d.sku = ANY(:offer_ids)
                      AND NOT (d.pr_no = ANY(:listed_prs))
                    GROUP BY d.sku, d.logistics_provider
                """),
                {"offer_ids": offer_ids, "listed_prs": listed_prs},
            ).fetchall()
            for offer_id, provider, qty in cross_rows:
                sku = offer_to_sku.get(offer_id)
                if sku is None:
                    continue  # 货号匹配不到商品，跳过
                channel_map.setdefault(sku, {})[provider or ""] = int(qty or 0)

        # ── 5. 国内在途（ozon_direct_shipment，receiving_status 为空=国内仓备货）────
        # 口径：与跨境在途同源（直发表），receiving_status 为空（货代未确认收到、
        #       未进入跨境段）即国内在途；'订单取消' 不计；按货号聚合 total_qty；
        #       货号匹配不到 products 的跳过。
        domestic_map = {sku: 0 for sku in all_sku_ids}
        if offer_ids:
            dom_rows = db.execute(
                text("""
                    SELECT d.sku, COALESCE(SUM(d.total_qty), 0)
                    FROM ozon.ozon_direct_shipment d
                    WHERE d.is_deleted = false
                      AND d.receiving_status IS NULL
                      AND d.sku = ANY(:offer_ids)
                    GROUP BY d.sku
                """),
                {"offer_ids": offer_ids},
            ).fetchall()
            for offer_id, qty in dom_rows:
                sku = offer_to_sku.get(offer_id)
                if sku is not None:
                    domestic_map[sku] = int(qty)

        # ── 6. 组装结果 + 计算 ────────────────────────────
        results = []
        for prod, cfg, mgmt in product_rows:
            sku_id = prod.sku_id
            stock = stock_map.get(sku_id, 0)

            sales_3 = sales_map[sku_id]["sales_3d"]
            sales_7 = sales_map[sku_id]["sales_7d"]
            sales_14 = sales_map[sku_id]["sales_14d"]
            sales_30 = sales_map[sku_id]["sales_30d"]

            # 跨境在途（按渠道拆分）
            ch = channel_map.get(sku_id, {})
            sdk = ch.get("SDK", 0)
            yunmeng = ch.get("运盟", 0)
            kunlun = ch.get("昆仑", 0)
            cgs = ch.get("超光速", 0) + sum(
                v for k, v in ch.items() if k not in ("SDK", "运盟", "昆仑", "超光速")
            )
            cb_total = sdk + yunmeng + kunlun + cgs

            dom_in_transit = domestic_map.get(sku_id, 0)

            # 无配置时用默认值兜底，configured=False 便于前端标记"未配置"
            configured = cfg is not None
            safety = cfg.safety_days if (cfg and cfg.safety_days) else 5
            logistics = cfg.logistics_days if (cfg and cfg.logistics_days) else 45

            # 公式计算
            weighted_daily = _calc_weighted_daily(sales_3, sales_7, sales_14, sales_30)
            qty_raw = _calc_replenishment_qty(weighted_daily, stock, cb_total, dom_in_transit, safety, logistics)
            suggested = _calc_suggested(qty_raw)
            available_days = _calc_available_days(stock, cb_total, dom_in_transit, weighted_daily)
            alert_level = _calc_alert_level(available_days, safety, logistics)

            results.append({
                "store_id": prod.store_id,
                "sku_id": sku_id,
                "offer_id": prod.offer_id,
                "product_name": prod.name,
                "primary_image": prod.primary_image,
                "product_status": mgmt.product_status if mgmt else None,
                "sales_manager": mgmt.sales_manager if mgmt else None,
                # 输入数据
                "stock_present": stock,
                "sales_3d": sales_3,
                "sales_7d": sales_7,
                "sales_14d": sales_14,
                "sales_30d": sales_30,
                "cross_border_sdk": sdk,
                "cross_border_yunmeng": yunmeng,
                "cross_border_kunlun": kunlun,
                "cross_border_cgs": cgs,
                "domestic_in_transit": dom_in_transit,
                "safety_days": safety,
                "logistics_days": logistics,
                # 中间结果
                "weighted_daily_sales": round(weighted_daily, 4),
                "cross_border_total": cb_total,
                # 最终结果
                "replenishment_qty_raw": round(qty_raw, 2),
                "suggested_replenishment": suggested,
                "available_days": available_days,
                "alert_level": alert_level,
                # 是否已配置安全/物流天数
                "configured": configured,
            })

        return results

    finally:
        db.close()


# ── 公式函数 ──────────────────────────────────────────────

def _calc_weighted_daily(s3: int, s7: int, s14: int, s30: int) -> float:
    """加权日销量 = 3天/3*0.2 + 7天/7*0.3 + 14天/14*0.3 + 30天/30*0.2"""
    return (
        (s3 / 3 * 0.2 if s3 else 0)
        + (s7 / 7 * 0.3 if s7 else 0)
        + (s14 / 14 * 0.3 if s14 else 0)
        + (s30 / 30 * 0.2 if s30 else 0)
    )


def _calc_replenishment_qty(
    weighted_daily: float,
    stock: int,
    cross_border: int,
    domestic: int,
    safety_days: int,
    logistics_days: int,
) -> float:
    """补货数量 = 加权日销量 × (安全天数 + 物流天数) - 库存 - 跨境在途 - 国内在途"""
    return weighted_daily * (safety_days + logistics_days) - stock - cross_border - domestic


def _calc_suggested(qty_raw: float) -> str:
    """建议补货 = IF(qty<=0, '♥☺♥', CEILING(qty, 1))"""
    if qty_raw <= 0:
        return "♥☺♥"
    return str(math.ceil(qty_raw))


def _calc_available_days(stock: int, cross_border: int, domestic: int, weighted_daily: float) -> float | None:
    """可售天数 = (库存 + 跨境在途 + 国内在途) / 加权日销量"""
    if weighted_daily <= 0:
        return None  # 无销量，可理解为无限
    return round((stock + cross_border + domestic) / weighted_daily, 1)


def _calc_alert_level(available_days: float | None, safety_days: int, logistics_days: int) -> str:
    """预警等级: emergency / warning / normal"""
    if available_days is None:
        return "normal"  # 无销量=无风险
    if available_days <= safety_days:
        return "emergency"
    if available_days <= safety_days + logistics_days:
        return "warning"
    return "normal"
