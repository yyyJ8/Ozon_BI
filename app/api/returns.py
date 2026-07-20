"""退货分析 API — 以 ozon.returns 表为主体，LEFT JOIN postings/products 补充上下文"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.returns import (
    ReturnsOverview,
    ReturnsTrendItem,
    SkuReturnStats,
    ReasonItem,
)

router = APIRouter(prefix="/returns", tags=["returns"])

# ── 中文原因映射 ──────────────────────────────────────────
REASON_CN_MAP: dict[str, str] = {
    # 取消退回 — Cancellation (10)
    "Покупатель отказался при вручении: товар не подошел": "拒收：商品不合适",
    "Покупатель отменил заказ: нашел дешевле": "取消：找到更便宜的",
    "Покупатель отменил заказ": "买家取消订单",
    "Покупатель не забрал заказ": "买家未取件",
    "Покупатель отменил заказ: не устроил срок доставки": "取消：不满配送时效",
    "Не удалось доставить заказ": "无法送达",
    "Покупатель отказался при вручении: недоволен качеством товара": "拒收：不满质量",
    "Покупатель отказался при вручении: в заказе не тот товар": "拒收：商品不符",
    "Покупатель отказался при вручении: неполная комплектация": "拒收：缺配件",
    "Покупатель отменил заказ: перенос сроков доставки": "取消：配送延期",
    # 签收后退货 — ClientReturn (7)
    "Покупатель передумал": "改变主意",
    "Упаковка и товар повреждены": "包装商品损坏",
    "Покупатель получил не те товары": "收到错误商品",
    "Товар в неполной комплектации": "缺配件",
    "Товар поврежден, но упаковка цела": "包装完好商品损坏",
    "Товар не работает / брак": "故障",
    "Товар поддельный": "假货",
}


def _translate_reason(russian: str) -> str:
    return REASON_CN_MAP.get(russian, russian)


def _date_params(date_from: date, date_to: date, **extra) -> dict:
    """构建日期范围参数"""
    return {"date_from": date_from, "date_to_excl": date_to + timedelta(days=1), **extra}


# ── 公共：returns 主体查询（LEFT JOIN postings）──────────
_RETURN_BASE = """
    FROM ozon.returns r
    LEFT JOIN ozon.postings p ON r.posting_number = p.posting_number
    WHERE r.returned_at >= :date_from
      AND r.returned_at  < :date_to_excl
"""


@router.get("/overview", response_model=ReturnsOverview)
def returns_overview(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    sku_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """退货总览：总数、type 分布、状态分布、退货率、平均处理天数"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    params = _date_params(date_from, date_to)
    sku_clause = "AND r.sku = :sku_id" if sku_id else ""
    if sku_id:
        params["sku_id"] = sku_id

    # 总数 + type 分布
    type_rows = db.execute(text(f"""
        SELECT r.type, COUNT(*) {_RETURN_BASE} {sku_clause} GROUP BY r.type
    """), params).fetchall()

    total = sum(int(c) for _, c in type_rows)
    cancellation_count = sum(int(c) for t, c in type_rows if t == "Cancellation")
    client_return_count = sum(int(c) for t, c in type_rows if t == "ClientReturn")

    # 状态分布
    status_rows = db.execute(text(f"""
        SELECT r.visual_status, COUNT(*) {_RETURN_BASE} {sku_clause}
        GROUP BY r.visual_status ORDER BY COUNT(*) DESC
    """), params).fetchall()
    by_status = {row[0]: int(row[1]) for row in status_rows}

    # 退货率 = 退货件数 / 送达件数（同期 posting delivered）
    delivered = 0
    if not sku_id:
        # 全量：直接 count postings 中 delivered 的 quantity
        del_row = db.execute(text("""
            SELECT COALESCE(SUM((prod->>'quantity')::int), 0)
            FROM ozon.postings,
                 jsonb_array_elements(products) AS prod
            WHERE created_at >= :date_from AND created_at < :date_to_excl
              AND status = 'delivered'
        """), params).fetchone()
        delivered = int(del_row[0]) if del_row and del_row[0] else 0
    else:
        del_row = db.execute(text("""
            SELECT COALESCE(SUM((prod->>'quantity')::int), 0)
            FROM ozon.postings,
                 jsonb_array_elements(products) AS prod
            WHERE created_at >= :date_from AND created_at < :date_to_excl
              AND status = 'delivered'
              AND (prod->>'sku')::bigint = :sku_id
        """), params).fetchone()
        delivered = int(del_row[0]) if del_row and del_row[0] else 0
    return_rate = round(total / delivered * 100, 2) if delivered > 0 else 0.0

    # 平均处理天数
    avg_days_row = db.execute(text(f"""
        SELECT AVG(EXTRACT(EPOCH FROM (r.finished_at - r.returned_at)) / 86400.0)
        {_RETURN_BASE} {sku_clause}
          AND r.finished_at IS NOT NULL AND r.returned_at IS NOT NULL
    """), params).fetchone()
    avg_days = round(float(avg_days_row[0]), 1) if avg_days_row and avg_days_row[0] else None

    return ReturnsOverview(
        total_returns=total,
        cancellation_count=cancellation_count,
        client_return_count=client_return_count,
        by_status=by_status,
        return_rate=return_rate,
        avg_processing_days=avg_days,
    )


@router.get("/trend", response_model=list[ReturnsTrendItem])
def returns_trend(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    sku_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """退货趋势：按下单日期 (p.created_at) × type 分组 — 展示各日期创建的订单最终发生了多少退货"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    params = _date_params(date_from, date_to)
    sku_clause = "AND r.sku = :sku_id" if sku_id else ""
    if sku_id:
        params["sku_id"] = sku_id

    rows = db.execute(text(f"""
        SELECT
            p.created_at::date AS order_date,
            r.type,
            COUNT(*)
        FROM ozon.returns r
        LEFT JOIN ozon.postings p ON r.posting_number = p.posting_number
        WHERE p.created_at >= :date_from
          AND p.created_at  < :date_to_excl
          {sku_clause}
        GROUP BY p.created_at::date, r.type
        ORDER BY order_date
    """), params).fetchall()

    date_map: dict[date, dict] = {}
    for order_date, rtype, cnt in rows:
        if order_date not in date_map:
            date_map[order_date] = {"cancellation": 0, "client_return": 0}
        if rtype == "Cancellation":
            date_map[order_date]["cancellation"] = int(cnt)
        elif rtype == "ClientReturn":
            date_map[order_date]["client_return"] = int(cnt)

    return [
        ReturnsTrendItem(
            date=d,
            cancellation=v["cancellation"],
            client_return=v["client_return"],
            total=v["cancellation"] + v["client_return"],
        )
        for d, v in sorted(date_map.items())
    ]


@router.get("/sku-stats", response_model=list[SkuReturnStats])
def sku_return_stats(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
):
    """SKU 维度退货明细"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    params = _date_params(date_from, date_to)

    rows = db.execute(text(f"""
        WITH sku_returns AS (
            SELECT
                r.sku,
                COUNT(*)                                                    AS total_returns,
                COUNT(*) FILTER (WHERE r.type = 'Cancellation')             AS cancellation_count,
                COUNT(*) FILTER (WHERE r.type = 'ClientReturn')             AS client_return_count,
                COUNT(*) FILTER (WHERE r.schema = 'Fbo')                    AS fbo_count,
                COUNT(*) FILTER (WHERE r.schema = 'Fbs')                    AS fbs_count,
                COUNT(*) FILTER (WHERE r.finished_at IS NOT NULL)           AS completed_count,
                COUNT(*) FILTER (WHERE r.finished_at IS NULL)               AS pending_count,
                COALESCE(SUM(r.price), 0)                                   AS total_return_price,
                AVG(EXTRACT(EPOCH FROM (r.finished_at - r.returned_at)) / 86400.0)
                    FILTER (WHERE r.finished_at IS NOT NULL AND r.returned_at IS NOT NULL) AS avg_days,
                MODE() WITHIN GROUP (ORDER BY r.return_reason_name)         AS main_reason
            FROM ozon.returns r
            LEFT JOIN ozon.postings p ON r.posting_number = p.posting_number
            WHERE p.created_at >= :date_from
              AND p.created_at  < :date_to_excl
            GROUP BY r.sku
        ),
        sku_ordered AS (
            SELECT
                (prod->>'sku')::bigint AS sku_id,
                COALESCE(SUM((prod->>'quantity')::int), 0) AS ordered_units
            FROM ozon.postings,
                 jsonb_array_elements(products) AS prod
            WHERE created_at >= :date_from AND created_at < :date_to_excl
            GROUP BY (prod->>'sku')::bigint
        )
        SELECT
            sr.sku,
            pr.name,
            pr.offer_id,
            pr.primary_image,
            sr.total_returns,
            sr.cancellation_count,
            sr.client_return_count,
            sr.fbo_count,
            sr.fbs_count,
            sr.completed_count,
            sr.pending_count,
            sr.total_return_price,
            COALESCE(so.ordered_units, 0) AS ordered_units,
            sr.avg_days,
            sr.main_reason
        FROM sku_returns sr
        LEFT JOIN ozon.products pr ON sr.sku = pr.sku_id
        LEFT JOIN sku_ordered so ON sr.sku = so.sku_id
        ORDER BY sr.total_returns DESC
    """), params).fetchall()

    result = []
    for row in rows:
        ordered = int(row[12]) if row[12] else 0
        total_ret = int(row[4])
        return_rate = round(total_ret / ordered * 100, 2) if ordered > 0 else 0.0
        result.append(SkuReturnStats(
            sku_id=int(row[0]),
            name=row[1],
            offer_id=row[2],
            primary_image=row[3],
            total_returns=total_ret,
            cancellation_count=int(row[5]),
            client_return_count=int(row[6]),
            fbo_count=int(row[7]),
            fbs_count=int(row[8]),
            completed_count=int(row[9]),
            pending_count=int(row[10]),
            total_return_price=float(row[11]) if row[11] else 0.0,
            ordered_units=ordered,
            return_rate=return_rate,
            avg_processing_days=round(float(row[13]), 1) if row[13] else None,
            main_reason=_translate_reason(row[14]) if row[14] else None,
        ))
    return result


@router.get("/reasons", response_model=list[ReasonItem])
def returns_reasons(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    type: Optional[str] = Query(default=None, description="过滤: Cancellation / ClientReturn"),
    db: Session = Depends(get_db),
):
    """退货原因分布"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    params = _date_params(date_from, date_to)
    type_clause = "AND r.type = :rtype" if type else ""
    if type:
        params["rtype"] = type

    rows = db.execute(text(f"""
        SELECT r.return_reason_name, r.type, COUNT(*)
        {_RETURN_BASE} {type_clause}
        GROUP BY r.return_reason_name, r.type
        ORDER BY COUNT(*) DESC
    """), params).fetchall()

    return [
        ReasonItem(
            reason_name=row[0] or "(未填写)",
            reason_cn=_translate_reason(row[0]) if row[0] else "未填写",
            type=row[1],
            count=int(row[2]),
        )
        for row in rows
    ]
