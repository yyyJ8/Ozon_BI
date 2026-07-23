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
    ReturnDetailItem,
)

router = APIRouter(prefix="/returns", tags=["returns"])

REASON_CN_MAP: dict[str, str] = {
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
    "Покупатель передумал": "改变主意",
    "Упаковка и товар повреждены": "包装商品损坏",
    "Покупатель получил не те товары": "收到错误商品",
    "Товар в неполной комплектации": "缺配件",
    "Товар поврежден, но упаковка цела": "包装完好商品损坏",
    "Товар не работает / брак": "故障",
    "Товар поддельный": "假货",
}

STORE_ID = Query(default=1, description="店铺 ID")


def _translate_reason(russian: str) -> str:
    return REASON_CN_MAP.get(russian, russian)


def _date_params(date_from: date, date_to: date, **extra) -> dict:
    return {"date_from": date_from, "date_to_excl": date_to + timedelta(days=1), **extra}


# Cohort base: FROM/JOIN/WHERE shared by most returns endpoints
_COHORT_BASE = """
    FROM ozon.returns r
    LEFT JOIN ozon.postings p ON r.posting_number = p.posting_number AND r.store_id = p.store_id
    WHERE r.store_id = :store_id
      AND p.created_at >= :date_from
      AND p.created_at  < :date_to_excl
"""


@router.get("/overview", response_model=ReturnsOverview)
def returns_overview(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    sku_id: Optional[int] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    params = _date_params(date_from, date_to, store_id=store_id)
    sku_clause = "AND r.sku = :sku_id" if sku_id else ""
    if sku_id:
        params["sku_id"] = sku_id

    type_rows = db.execute(text(f"""
        SELECT r.type, COUNT(*) {_COHORT_BASE} {sku_clause} GROUP BY r.type
    """), params).fetchall()

    total = sum(int(c) for _, c in type_rows)
    cancellation_count = sum(int(c) for t, c in type_rows if t == "Cancellation")
    client_return_count = sum(int(c) for t, c in type_rows if t == "ClientReturn")

    status_rows = db.execute(text(f"""
        SELECT r.visual_status, COUNT(*) {_COHORT_BASE} {sku_clause}
        GROUP BY r.visual_status ORDER BY COUNT(*) DESC
    """), params).fetchall()
    by_status = {row[0]: int(row[1]) for row in status_rows}

    ordered = 0
    if not sku_id:
        ordered_row = db.execute(text("""
            SELECT COALESCE(SUM((prod->>'quantity')::int), 0)
            FROM ozon.postings,
                 jsonb_array_elements(products) AS prod
            WHERE store_id = :store_id
              AND created_at >= :date_from AND created_at < :date_to_excl
        """), params).fetchone()
        ordered = int(ordered_row[0]) if ordered_row and ordered_row[0] else 0
    else:
        ordered_row = db.execute(text("""
            SELECT COALESCE(SUM((prod->>'quantity')::int), 0)
            FROM ozon.postings,
                 jsonb_array_elements(products) AS prod
            WHERE store_id = :store_id
              AND created_at >= :date_from AND created_at < :date_to_excl
              AND (prod->>'sku')::bigint = :sku_id
        """), params).fetchone()
        ordered = int(ordered_row[0]) if ordered_row and ordered_row[0] else 0
    return_rate = round(total / ordered * 100, 2) if ordered > 0 else 0.0

    avg_days_row = db.execute(text(f"""
        SELECT AVG(EXTRACT(EPOCH FROM (r.finished_at - r.returned_at)) / 86400.0)
        {_COHORT_BASE} {sku_clause}
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
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    params = _date_params(date_from, date_to, store_id=store_id)
    sku_clause = "AND r.sku = :sku_id" if sku_id else ""
    if sku_id:
        params["sku_id"] = sku_id

    rows = db.execute(text(f"""
        SELECT
            p.created_at::date AS order_date,
            r.type,
            COUNT(*)
        {_COHORT_BASE}
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
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    params = _date_params(date_from, date_to, store_id=store_id)

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
            LEFT JOIN ozon.postings p ON r.posting_number = p.posting_number AND r.store_id = p.store_id
            WHERE r.store_id = :store_id
              AND p.created_at >= :date_from
              AND p.created_at  < :date_to_excl
            GROUP BY r.sku
        ),
        sku_ordered AS (
            SELECT
                (prod->>'sku')::bigint AS sku_id,
                COALESCE(SUM((prod->>'quantity')::int), 0) AS ordered_units
            FROM ozon.postings,
                 jsonb_array_elements(products) AS prod
            WHERE store_id = :store_id
              AND created_at >= :date_from AND created_at < :date_to_excl
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
        LEFT JOIN ozon.products pr ON sr.sku = pr.sku_id AND pr.store_id = :store_id
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


@router.get("/details", response_model=list[ReturnDetailItem])
def returns_details(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    sku_id: int = Query(...),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    params = _date_params(date_from, date_to, store_id=store_id, sku_id=sku_id)

    rows = db.execute(text(f"""
        SELECT
            r.id,
            r.posting_number,
            r.sku,
            pr.name,
            pr.offer_id,
            pr.primary_image,
            r.type,
            r.return_reason_name,
            r.quantity,
            r.price,
            r.visual_status,
            r.schema,
            r.returned_at,
            r.finished_at,
            r.status_changed_at,
            EXTRACT(EPOCH FROM (r.finished_at - r.returned_at)) / 86400.0 AS processing_days
        FROM ozon.returns r
        LEFT JOIN ozon.postings p ON r.posting_number = p.posting_number AND r.store_id = p.store_id
        LEFT JOIN ozon.products pr ON r.sku = pr.sku_id AND r.store_id = pr.store_id
        WHERE r.store_id = :store_id
          AND p.created_at >= :date_from
          AND p.created_at  < :date_to_excl
          AND r.sku = :sku_id
        ORDER BY r.returned_at DESC
        LIMIT :limit OFFSET :offset
    """), {**params, "limit": limit, "offset": offset}).fetchall()

    result = []
    for row in rows:
        result.append(ReturnDetailItem(
            id=int(row[0]),
            posting_number=row[1],
            sku=int(row[2]),
            product_name=row[3],
            offer_id=row[4],
            primary_image=row[5],
            type=row[6],
            return_reason_name=row[7],
            reason_cn=_translate_reason(row[7]) if row[7] else None,
            quantity=int(row[8]) if row[8] else 0,
            price=float(row[9]) if row[9] else None,
            visual_status=row[10],
            delivery_schema=row[11],
            returned_at=row[12],
            finished_at=row[13],
            status_changed_at=row[14],
            processing_days=round(float(row[15]), 1) if row[15] else None,
        ))
    return result


@router.get("/reasons", response_model=list[ReasonItem])
def returns_reasons(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    type: Optional[str] = Query(default=None, description="过滤: Cancellation / ClientReturn"),
    sku_id: Optional[int] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    params = _date_params(date_from, date_to, store_id=store_id)
    type_clause = "AND r.type = :rtype" if type else ""
    if type:
        params["rtype"] = type
    sku_clause = "AND r.sku = :sku_id" if sku_id else ""
    if sku_id:
        params["sku_id"] = sku_id

    rows = db.execute(text(f"""
        SELECT r.return_reason_name, r.type, COUNT(*)
        {_COHORT_BASE} {type_clause} {sku_clause}
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
