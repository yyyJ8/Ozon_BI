"""补货提示服务 — 聚合数据并计算公式"""
import math
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, text

from app.database import SessionLocal
from app.models import (
    ReplenishmentConfig, Product, Stock,
    SkuDailySummary, CargoShipment, SkuManagement,
)


def get_replenishment_data(store_id: int = 0) -> list[dict]:
    """获取所有 SKU 的补货提示数据（含公式计算结果）。

    Args:
        store_id: 店铺 ID，0 = 全部店铺

    Returns:
        补货行列表，每行包含输入数据、中间结果和最终建议
    """
    db = SessionLocal()
    try:
        today = date.today()

        # ── 1. 查询配置 + 关联产品 ────────────────────────
        config_query = db.query(
            ReplenishmentConfig,
            Product,
            SkuManagement,
        ).outerjoin(
            Product,
            (ReplenishmentConfig.store_id == Product.store_id)
            & (ReplenishmentConfig.offer_id == Product.offer_id),
        ).outerjoin(
            SkuManagement,
            (Product.store_id == SkuManagement.store_id)
            & (Product.sku_id == SkuManagement.sku_id),
        )

        if store_id != 0:
            config_query = config_query.filter(ReplenishmentConfig.store_id == store_id)

        config_rows = config_query.all()

        if not config_rows:
            return []

        # 构建 sku_id 列表
        sku_store_map = {}  # sku_id -> store_id
        offer_image_map = {}  # sku_id -> primary_image
        offer_name_map = {}  # sku_id -> product_name from products
        mgmt_status_map = {}  # sku_id -> product_status
        mgmt_manager_map = {}  # sku_id -> sales_manager

        valid_rows = []
        for cfg, prod, mgmt in config_rows:
            if prod is None:
                continue
            sku_id = prod.sku_id
            st_id = cfg.store_id
            sku_store_map[sku_id] = st_id
            offer_image_map[sku_id] = prod.primary_image
            offer_name_map[sku_id] = prod.name
            mgmt_status_map[sku_id] = mgmt.product_status if mgmt else None
            mgmt_manager_map[sku_id] = mgmt.sales_manager if mgmt else None
            valid_rows.append((cfg, prod))

        if not valid_rows:
            return []

        all_sku_ids = list(sku_store_map.keys())

        # ── 2. 库存 ───────────────────────────────────────
        stock_rows = (
            db.query(Stock.sku_id, func.coalesce(func.sum(Stock.present), 0))
            .filter(Stock.sku_id.in_(all_sku_ids))
        )
        if store_id != 0:
            stock_rows = stock_rows.filter(Stock.store_id == store_id)
        stock_map = {sku: int(s) for sku, s in stock_rows.group_by(Stock.sku_id).all()}

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
                sales_map[sku][key] = max(0, ordered_map.get(sku, 0) - cancelled_map.get(sku, 0) - client_return_map.get(sku, 0))

        # ── 4. 跨境在途（cargo_shipments，状态=跨境在途）────
        cross_border_map = {sku: 0 for sku in all_sku_ids}
        cargo_rows = (
            db.query(CargoShipment.sku, func.coalesce(func.sum(CargoShipment.replenishment_qty), 0))
            .filter(
                CargoShipment.sku.in_([p.offer_id for _, p in valid_rows]),
                CargoShipment.cargo_status == "跨境在途",
            )
        )
        if store_id != 0:
            # cargo_shipments 不分 store，按 SKU 聚合
            pass
        for sku_offer_id, qty in cargo_rows.group_by(CargoShipment.sku).all():
            # 找到对应的 sku_id
            for cfg, prod in valid_rows:
                if prod.offer_id == sku_offer_id:
                    cross_border_map[prod.sku_id] = int(qty)
                    break

        # ── 5. 国内在途（omsprod purchase_order_item）────
        domestic_map = _get_domestic_in_transit(all_sku_ids)

        # ── 6. 组装结果 + 计算 ────────────────────────────
        results = []
        for cfg, prod in valid_rows:
            sku_id = prod.sku_id
            stock = stock_map.get(sku_id, 0)

            sales_3 = sales_map[sku_id]["sales_3d"]
            sales_7 = sales_map[sku_id]["sales_7d"]
            sales_14 = sales_map[sku_id]["sales_14d"]
            sales_30 = sales_map[sku_id]["sales_30d"]

            cb_total = cross_border_map.get(sku_id, 0)
            dom_in_transit = domestic_map.get(sku_id, 0)
            safety = cfg.safety_days or 5
            logistics = cfg.logistics_days or 45

            # 公式计算
            weighted_daily = _calc_weighted_daily(sales_3, sales_7, sales_14, sales_30)
            qty_raw = _calc_replenishment_qty(weighted_daily, stock, cb_total, dom_in_transit, safety, logistics)
            suggested = _calc_suggested(qty_raw)
            available_days = _calc_available_days(stock, cb_total, dom_in_transit, weighted_daily)
            alert_level = _calc_alert_level(available_days, safety, logistics)

            results.append({
                "store_id": cfg.store_id,
                "sku_id": sku_id,
                "offer_id": cfg.offer_id,
                "product_name": offer_name_map.get(sku_id) or cfg.product_name,
                "primary_image": offer_image_map.get(sku_id),
                "product_status": mgmt_status_map.get(sku_id),
                "sales_manager": mgmt_manager_map.get(sku_id),
                # 输入数据
                "stock_present": stock,
                "sales_3d": sales_3,
                "sales_7d": sales_7,
                "sales_14d": sales_14,
                "sales_30d": sales_30,
                "cross_border_sdk": 0,  # cargo_shipments 目前归入 cgs 渠道
                "cross_border_yunmeng": 0,
                "cross_border_kunlun": 0,
                "cross_border_cgs": cb_total,
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


def _get_domestic_in_transit(sku_ids: list[int]) -> dict[int, int]:
    """从 omsprod 获取国内在途（采购未完结数量）"""
    result = {sku: 0 for sku in sku_ids}
    try:
        from app.database_oms import oms_pg_ctx
        with oms_pg_ctx() as conn:
            cur = conn.cursor()
            # 查询未完结的采购订单行: qty - receipt_qty
            cur.execute("""
                SELECT poi.item_id, SUM(poi.qty - COALESCE(poi.receipt_qty, 0)) AS in_transit
                FROM purchase_order_item poi
                WHERE poi.item_id IS NOT NULL
                  AND poi.qty > COALESCE(poi.receipt_qty, 0)
                GROUP BY poi.item_id
            """)
            rows = cur.fetchall()
            cur.close()

        # item_id 在 omsprod 中可能对应 products.offer_id
        # 需要映射 offer_id → sku_id
        if rows:
            db = SessionLocal()
            try:
                offer_ids = [r[0] for r in rows]
                prod_map = dict(
                    db.query(Product.offer_id, Product.sku_id)
                    .filter(Product.offer_id.in_(offer_ids))
                    .all()
                )
                for offer_id, qty in rows:
                    sku_id = prod_map.get(offer_id)
                    if sku_id and sku_id in result:
                        result[sku_id] = int(qty)
            finally:
                db.close()
    except Exception:
        pass  # omsprod 不可用时兜底为 0

    return result
