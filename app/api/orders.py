"""订单分析 API — 以 ozon.postings 表为主体，LEFT JOIN returns/finance_transactions 补充上下文"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.orders import (
    OrderOverview,
    OrderTrendItem,
    OrderListItem,
    OrderListResponse,
    OrderDetail,
    OrderProduct,
    OrderReturn,
    OrderFinance,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def _date_params(date_from: date, date_to: date, **extra) -> dict:
    """构建日期范围参数"""
    return {"date_from": date_from, "date_to_excl": date_to + timedelta(days=1), **extra}


def _sku_filter_clause(sku_id: Optional[int], params: dict) -> str:
    """生成 SKU 筛选子句（JSONB EXISTS 注入）"""
    if not sku_id:
        return ""
    params["sku_id"] = sku_id
    return """AND EXISTS (
        SELECT 1 FROM jsonb_array_elements(p.products) AS prod
        WHERE (prod->>'sku')::bigint = :sku_id
    )"""


# ── 状态中文映射 ──────────────────────────────────────────
STATUS_LABELS: dict[str, str] = {
    "awaiting_deliver": "等待发货",
    "delivering": "配送中",
    "delivered": "已签收",
    "cancelled": "已取消",
}


@router.get("/overview", response_model=OrderOverview)
def orders_overview(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    sku_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """订单总览：总数、FBO/FBS、状态分布、取消率、平均每单件数"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    params = _date_params(date_from, date_to)
    sku_clause = _sku_filter_clause(sku_id, params)

    # 订单计数
    row = db.execute(text(f"""
        SELECT
            COUNT(*) AS total_orders,
            COUNT(*) FILTER (WHERE p.delivery_schema = 'FBO') AS fbo_count,
            COUNT(*) FILTER (WHERE p.delivery_schema = 'FBS') AS fbs_count,
            COUNT(*) FILTER (WHERE p.status = 'delivered') AS delivered_count,
            COUNT(*) FILTER (WHERE p.status = 'cancelled') AS cancelled_count,
            COUNT(*) FILTER (WHERE p.status NOT IN ('delivered', 'cancelled')) AS in_progress_count
        FROM ozon.postings p
        WHERE p.created_at >= :date_from
          AND p.created_at  < :date_to_excl
          {sku_clause}
    """), params).fetchone()

    total_orders = int(row[0]) if row and row[0] else 0
    fbo_count = int(row[1]) if row else 0
    fbs_count = int(row[2]) if row else 0
    delivered_count = int(row[3]) if row else 0
    cancelled_count = int(row[4]) if row else 0
    in_progress_count = int(row[5]) if row else 0
    cancellation_rate = round(cancelled_count / total_orders * 100, 2) if total_orders > 0 else 0.0

    # 总件数（JSONB 展开）
    # 如果有 sku_id，只统计该 SKU 的件数
    units_clause = ""
    if sku_id:
        units_clause = "AND (prod->>'sku')::bigint = :sku_id"
    units_row = db.execute(text(f"""
        SELECT COALESCE(SUM((prod->>'quantity')::int), 0)
        FROM ozon.postings p,
             jsonb_array_elements(p.products) AS prod
        WHERE p.created_at >= :date_from
          AND p.created_at  < :date_to_excl
          {units_clause}
    """), params).fetchone()
    total_ordered_units = int(units_row[0]) if units_row and units_row[0] else 0

    # 平均每单商品数
    avg_items_row = db.execute(text(f"""
        SELECT AVG(jsonb_array_length(p.products))
        FROM ozon.postings p
        WHERE p.created_at >= :date_from
          AND p.created_at  < :date_to_excl
          {sku_clause}
    """), params).fetchone()
    avg_items_per_order = round(float(avg_items_row[0]), 1) if avg_items_row and avg_items_row[0] else None

    return OrderOverview(
        total_orders=total_orders,
        fbo_count=fbo_count,
        fbs_count=fbs_count,
        delivered_count=delivered_count,
        cancelled_count=cancelled_count,
        in_progress_count=in_progress_count,
        total_ordered_units=total_ordered_units,
        cancellation_rate=cancellation_rate,
        avg_items_per_order=avg_items_per_order,
    )


@router.get("/trend", response_model=list[OrderTrendItem])
def orders_trend(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    sku_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """订单趋势：按下单日期 (p.created_at) × 状态分组"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    params = _date_params(date_from, date_to)
    sku_clause = _sku_filter_clause(sku_id, params)

    rows = db.execute(text(f"""
        SELECT
            p.created_at::date AS order_date,
            COUNT(*) AS ordered,
            COUNT(*) FILTER (WHERE p.status = 'awaiting_deliver') AS awaiting_deliver,
            COUNT(*) FILTER (WHERE p.status = 'delivering') AS delivering,
            COUNT(*) FILTER (WHERE p.status = 'delivered') AS delivered,
            COUNT(*) FILTER (WHERE p.status = 'cancelled') AS cancelled
        FROM ozon.postings p
        WHERE p.created_at >= :date_from
          AND p.created_at  < :date_to_excl
          {sku_clause}
        GROUP BY p.created_at::date
        ORDER BY order_date
    """), params).fetchall()

    return [
        OrderTrendItem(
            date=row[0],
            ordered=int(row[1]),
            awaiting_deliver=int(row[2]),
            delivering=int(row[3]),
            delivered=int(row[4]),
            cancelled=int(row[5]),
        )
        for row in rows
    ]


@router.get("/list", response_model=OrderListResponse)
def orders_list(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    status: Optional[str] = Query(default=None, description="过滤: awaiting_deliver / delivering / delivered / cancelled"),
    schema: Optional[str] = Query(default=None, description="过滤: FBO / FBS"),
    sku_id: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None, description="模糊搜索: SKU / 货号"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """订单列表 — 分页 + 筛选"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    params = _date_params(date_from, date_to)

    # 动态 WHERE 子句
    where_clauses = [
        "p.created_at >= :date_from",
        "p.created_at  < :date_to_excl",
    ]
    if status:
        params["status"] = status
        where_clauses.append("p.status = :status")
    if schema:
        params["schema"] = schema
        where_clauses.append("p.delivery_schema = :schema")
    if sku_id:
        params["sku_id"] = sku_id
        where_clauses.append("""EXISTS (
            SELECT 1 FROM jsonb_array_elements(p.products) AS prod
            WHERE (prod->>'sku')::bigint = :sku_id
        )""")
    if search:
        params["search"] = f"%{search}%"
        where_clauses.append("""EXISTS (
            SELECT 1 FROM jsonb_array_elements(p.products) AS prod
            WHERE (prod->>'sku')::text ILIKE :search
               OR prod->>'offer_id' ILIKE :search
        )""")

    where_sql = " AND ".join(where_clauses)

    # 计数
    total_row = db.execute(text(f"""
        SELECT COUNT(*) FROM ozon.postings p WHERE {where_sql}
    """), params).fetchone()
    total = int(total_row[0]) if total_row else 0

    # 分页查询
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    rows = db.execute(text(f"""
        SELECT
            p.posting_number,
            p.order_number,
            p.delivery_schema,
            p.status,
            p.created_at,
            COALESCE(p.delivered_at, (
                SELECT MIN(ft.operation_date)::timestamp
                FROM ozon.finance_transactions ft
                WHERE ft.posting_number = p.posting_number
                  AND ft.operation_type = 'OperationAgentDeliveredToCustomer'
            )) AS delivered_at,
            p.in_process_at,
            p.products->0->>'sku' AS sku,
            p.products->0->>'offer_id' AS offer_id,
            COALESCE(jsonb_array_length(p.products), 0) AS product_count,
            COALESCE(
                (SELECT SUM((prod->>'quantity')::int)
                 FROM jsonb_array_elements(p.products) AS prod), 0
            ) AS total_quantity,
            COALESCE(
                (SELECT SUM((prod->>'price')::numeric)
                 FROM jsonb_array_elements(p.products) AS prod), 0.0
            ) AS total_price
        FROM ozon.postings p
        WHERE {where_sql}
        ORDER BY p.created_at DESC
        LIMIT :limit OFFSET :offset
    """), params).fetchall()

    items = [
        OrderListItem(
            posting_number=row[0],
            order_number=row[1],
            delivery_schema=row[2],
            status=row[3],
            created_at=row[4],
            delivered_at=row[5],
            in_process_at=row[6],
            sku=int(row[7]) if row[7] else None,
            offer_id=row[8],
            product_count=int(row[9]) if row[9] else 0,
            total_quantity=int(row[10]) if row[10] else 0,
            total_price=float(row[11]) if row[11] else 0.0,
        )
        for row in rows
    ]

    return OrderListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{posting_number}", response_model=OrderDetail)
def order_detail(
    posting_number: str,
    db: Session = Depends(get_db),
):
    """订单详情 — 基本信息 + 商品清单 + 关联退货 + 财务流水"""
    # 1. Posting
    p = db.execute(text("""
        SELECT posting_number, order_number, delivery_schema, status,
               cancel_reason_id, created_at, in_process_at, delivered_at, products
        FROM ozon.postings
        WHERE posting_number = :pn
    """), {"pn": posting_number}).fetchone()

    if not p:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"订单 {posting_number} 不存在")

    # 解析 products JSON
    import json
    products_raw = p[8] if p[8] else []
    if isinstance(products_raw, str):
        products_raw = json.loads(products_raw)

    # 查商品图片
    sku_ids = [prod.get("sku") for prod in (products_raw or []) if prod.get("sku")]
    image_map: dict[int, str] = {}
    if sku_ids:
        img_rows = db.execute(text("""
            SELECT sku_id, primary_image FROM ozon.products WHERE sku_id = ANY(:skus)
        """), {"skus": sku_ids}).fetchall()
        image_map = {int(r[0]): r[1] for r in img_rows if r[1]}

    products = [
        OrderProduct(
            sku=prod.get("sku"),
            name=prod.get("name"),
            quantity=prod.get("quantity", 0) or 0,
            offer_id=prod.get("offer_id"),
            price=float(prod.get("price", 0) or 0),
            image=image_map.get(prod.get("sku")) if prod.get("sku") else None,
        )
        for prod in (products_raw or [])
    ]

    # 2. 关联退货
    returns_raw = db.execute(text("""
        SELECT id, sku, type, return_reason_name, quantity,
               visual_status, returned_at, finished_at
        FROM ozon.returns
        WHERE posting_number = :pn
        ORDER BY returned_at DESC
    """), {"pn": posting_number}).fetchall()

    returns = [
        OrderReturn(
            id=int(r[0]), sku=int(r[1]), type=r[2],
            return_reason_name=r[3], quantity=int(r[4]) if r[4] else 0,
            visual_status=r[5], returned_at=r[6], finished_at=r[7],
        )
        for r in returns_raw
    ]

    # 3. 财务流水
    finance_raw = db.execute(text("""
        SELECT operation_id, operation_type_name, type, operation_date,
               amount, accruals_for_sale, sale_commission,
               delivery_charge, return_delivery_charge
        FROM ozon.finance_transactions
        WHERE posting_number = :pn
        ORDER BY operation_date DESC
    """), {"pn": posting_number}).fetchall()

    finance = [
        OrderFinance(
            operation_id=int(f[0]), operation_type_name=f[1], type=f[2],
            operation_date=f[3],
            amount=float(f[4]) if f[4] else 0.0,
            accruals_for_sale=float(f[5]) if f[5] else 0.0,
            sale_commission=float(f[6]) if f[6] else 0.0,
            delivery_charge=float(f[7]) if f[7] else 0.0,
            return_delivery_charge=float(f[8]) if f[8] else 0.0,
        )
        for f in finance_raw
    ]

    return OrderDetail(
        posting_number=p[0],
        order_number=p[1],
        delivery_schema=p[2],
        status=p[3],
        cancel_reason_id=int(p[4]) if p[4] else 0,
        created_at=p[5],
        in_process_at=p[6],
        delivered_at=p[7],
        products=products,
        returns=returns,
        finance_transactions=finance,
    )
