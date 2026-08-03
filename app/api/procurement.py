"""中台供应链 API — 申购计划 / 采购订单 / 头程发货"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database_oms import get_oms_pg
from app.schemas.procurement import (
    # 申购
    PlanOverview, PlanListItem, PlanListResponse, PlanItemDetail, PlanDetail,
    # 采购
    OrderOverview, OrderListItem, OrderListResponse, OrderItemDetail, OrderDetail,
    # 发货
    ShippingOverview, ShippingListItem, ShippingListResponse, ShippingItemDetail, ShippingDetail,
)

router = APIRouter(prefix="/procurement", tags=["procurement"])

# ═══════════════════════════════════════════════════════════════
# 状态映射
# ═══════════════════════════════════════════════════════════════

PLAN_STATUS_LABELS: dict[str, str] = {
    "0": "待提交", "1": "待审批", "2": "待创建采购单",
    "3": "部分创建采购订单", "4": "已创建采购订单",
    "5": "已作废", "6": "审批中",
}

PLAN_TYPE_LABELS: dict[str, str] = {
    "0": "平台仓备货", "1": "海外仓备货", "2": "计划备货", "3": "组合备货",
}

ORDER_STATUS_LABELS: dict[str, str] = {
    "0": "待提交", "1": "已提交", "2": "待审批",
    "3": "待入库", "4": "部分入库", "5": "异常",
    "6": "已作废", "7": "完结",
}

SHIPPING_STATUS_LABELS: dict[str, str] = {
    "1": "待推送到仓", "2": "待拣货", "3": "拣货完成,待装箱",
    "4": "装箱完成,待上传头程物流箱唛", "5": "待质检",
    "6": "待上传海外仓入库箱唛", "7": "待物流专员发货",
    "8": "待复核", "9": "已作废", "10": "复核完成,待发货",
    "11": "已发货", "12": "已到仓", "13": "部分到仓",
}

OZON_CLAUSE = {
    "plan": "AND ppi.platform = 'Ozon'",
    "order": "AND poi.sale_platform = 'Ozon'",
    "shipping": "AND ppi.platform = 'Ozon'",
}


def _date_clause(date_from: date | None, date_to: date | None, prefix: str = "t") -> tuple[str, dict]:
    """返回 (SQL 条件, 参数字典)"""
    if date_from is None:
        date_to = date_to or date.today()
        date_from = date_to - timedelta(days=90)
    elif date_to is None:
        date_to = date.today()
    params = {
        "date_from": date_from,
        "date_to_excl": date_to + timedelta(days=1),
    }
    clause = f"{prefix}.create_time >= %(date_from)s AND {prefix}.create_time < %(date_to_excl)s"
    return clause, params


def _fmt_val(v):
    """将数据库值转为 JSON-safe 格式"""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, Decimal):
        return str(v)
    return v


def _str(v):
    """将 bigint ID 或 Decimal 转为字符串（处理 Pydantic str | None 类型）"""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return str(v)
    return str(v)


# ═══════════════════════════════════════════════════════════════
# 申购计划 (purchase_plan)
# ═══════════════════════════════════════════════════════════════

@router.get("/plan/overview", response_model=PlanOverview)
def plan_overview(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    pg=Depends(get_oms_pg),
):
    dc, params = _date_clause(date_from, date_to, "pp")
    cur = pg.cursor()
    row = None
    try:
        cur.execute(f"""
            SELECT
                COUNT(DISTINCT pp.po_plan_no),
                COUNT(DISTINCT pp.po_plan_no) FILTER (WHERE pp.status = '0'),
                COUNT(DISTINCT pp.po_plan_no) FILTER (WHERE pp.status = '1'),
                COUNT(DISTINCT pp.po_plan_no) FILTER (WHERE pp.status = '2'),
                COUNT(DISTINCT pp.po_plan_no) FILTER (WHERE pp.status = '3'),
                COUNT(DISTINCT pp.po_plan_no) FILTER (WHERE pp.status = '4'),
                COUNT(DISTINCT pp.po_plan_no) FILTER (WHERE pp.status = '5'),
                COUNT(DISTINCT pp.po_plan_no) FILTER (WHERE pp.status = '6'),
                COALESCE(SUM(ppi.plan_qty), 0)
            FROM public.purchase_plan pp
            INNER JOIN public.purchase_plan_item ppi ON ppi.po_plan_no = pp.po_plan_no
            WHERE {dc} {OZON_CLAUSE['plan']}
        """, params)
        row = cur.fetchone()
    finally:
        cur.close()

    return PlanOverview(
        total=int(row[0]) if row else 0,
        status_0_pending_submit=int(row[1]) if row else 0,
        status_1_pending_approval=int(row[2]) if row else 0,
        status_2_pending_create_po=int(row[3]) if row else 0,
        status_3_partial_create=int(row[4]) if row else 0,
        status_4_created=int(row[5]) if row else 0,
        status_5_cancelled=int(row[6]) if row else 0,
        status_6_approving=int(row[7]) if row else 0,
        total_plan_qty=float(row[8]) if row and row[8] else 0.0,
    )


@router.get("/plan/list", response_model=PlanListResponse)
def plan_list(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    pg=Depends(get_oms_pg),
):
    dc, params = _date_clause(date_from, date_to, "pp")
    cur = pg.cursor()
    try:
        # count
        cur.execute(f"""
            SELECT COUNT(DISTINCT pp.po_plan_no)
            FROM public.purchase_plan pp
            INNER JOIN public.purchase_plan_item ppi ON ppi.po_plan_no = pp.po_plan_no
            WHERE {dc} {OZON_CLAUSE['plan']}
        """, params)
        total = int(cur.fetchone()[0])

        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size
        cur.execute(f"""
            SELECT DISTINCT ON (pp.po_plan_no)
                pp.po_plan_no, pp.status, pp.plan_type, pp.logistics_method,
                pp.stock_location_id, pp.location_id, pp.create_time, pp.memo,
                (SELECT COUNT(*) FROM public.purchase_plan_item ppi2 WHERE ppi2.po_plan_no = pp.po_plan_no),
                COALESCE((SELECT SUM(ppi2.plan_qty) FROM public.purchase_plan_item ppi2 WHERE ppi2.po_plan_no = pp.po_plan_no), 0),
                pp.return_reason
            FROM public.purchase_plan pp
            INNER JOIN public.purchase_plan_item ppi ON ppi.po_plan_no = pp.po_plan_no
            WHERE {dc} {OZON_CLAUSE['plan']}
            ORDER BY pp.po_plan_no, pp.create_time DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """, params)
        rows = cur.fetchall()
    finally:
        cur.close()

    items = [
        PlanListItem(
            po_plan_no=r[0],
            status=r[1],
            status_label=PLAN_STATUS_LABELS.get(r[1] or "", r[1] or ""),
            plan_type=r[2],
            plan_type_label=PLAN_TYPE_LABELS.get(r[2] or "", r[2] or ""),
            logistics_method=r[3],
            stock_location_id=_str(r[4]),
            location_id=_str(r[5]),
            create_time=_fmt_val(r[6]),
            memo=r[7],
            item_count=int(r[8]) if r[8] else 0,
            total_plan_qty=float(r[9]) if r[9] else 0.0,
            return_reason=r[10],
        )
        for r in rows
    ]
    return PlanListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/plan/{po_plan_no}", response_model=PlanDetail)
def plan_detail(po_plan_no: str, pg=Depends(get_oms_pg)):
    cur = pg.cursor()
    try:
        cur.execute("""
            SELECT po_plan_no, status, plan_type, logistics_method,
                   stock_location_id, location_id, create_time, update_time,
                   memo, return_reason, plan_source, is_urgent, is_new_product,
                   is_year_stock, is_group, combo_flag, wms_status, task_status,
                   shipping_status, cancel_reason, tax_free_flag
            FROM public.purchase_plan WHERE po_plan_no = %s
        """, (po_plan_no,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"申购单 {po_plan_no} 不存在")

        cur.execute("""
            SELECT row_id, item_id, seller_sku, plan_qty, already_qty,
                   created_shipping_plan_qty, expect_date, expect_delivery_date,
                   store_id, fn_sku, marketplace, new_flag, order_type, memo,
                   package_qty, wms_rec_qty, wms_check_qty, wms_onstock_qty,
                   direct_ship_arrival_qty, direct_ship_arrival_time,
                   main_sku_id, warehouse_item_code
            FROM public.purchase_plan_item
            WHERE po_plan_no = %s ORDER BY row_id
        """, (po_plan_no,))
        items = cur.fetchall()
    finally:
        cur.close()

    return PlanDetail(
        po_plan_no=row[0],
        status=row[1],
        status_label=PLAN_STATUS_LABELS.get(row[1] or "", row[1] or ""),
        plan_type=row[2],
        plan_type_label=PLAN_TYPE_LABELS.get(row[2] or "", row[2] or ""),
        logistics_method=row[3],
        stock_location_id=_str(row[4]),
        location_id=_str(row[5]),
        create_time=_fmt_val(row[6]),
        update_time=_fmt_val(row[7]),
        memo=row[8],
        return_reason=row[9],
        plan_source=row[10],
        is_urgent=row[11],
        is_new_product=row[12],
        is_year_stock=_str(row[13]),
        is_group=row[14],
        combo_flag=row[15],
        wms_status=row[16],
        task_status=row[17],
        shipping_status=row[18],
        cancel_reason=row[19],
        tax_free_flag=_str(row[20]),
        items=[
            PlanItemDetail(
                row_id=int(r[0]) if r[0] else 0,
                item_id=r[1], seller_sku=r[2],
                plan_qty=float(r[3]) if r[3] else 0.0,
                already_qty=float(r[4]) if r[4] else 0.0,
                created_shipping_plan_qty=float(r[5]) if r[5] else 0.0,
                expect_date=_fmt_val(r[6]), expect_delivery_date=_fmt_val(r[7]),
                store_id=_str(r[8]), fn_sku=r[9], marketplace=r[10], new_flag=r[11],
                order_type=r[12], memo=r[13],
                package_qty=float(r[14]) if r[14] else 0.0,
                wms_rec_qty=float(r[15]) if r[15] else 0.0,
                wms_check_qty=float(r[16]) if r[16] else 0.0,
                wms_onstock_qty=float(r[17]) if r[17] else 0.0,
                direct_ship_arrival_qty=float(r[18]) if r[18] else 0.0,
                direct_ship_arrival_time=_fmt_val(r[19]),
                main_sku_id=_str(r[20]), warehouse_item_code=r[21],
            )
            for r in items
        ],
    )


# ═══════════════════════════════════════════════════════════════
# 采购订单 (purchase_order)
# ═══════════════════════════════════════════════════════════════

@router.get("/order/overview", response_model=OrderOverview)
def order_overview(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    pg=Depends(get_oms_pg),
):
    dc, params = _date_clause(date_from, date_to, "po")
    cur = pg.cursor()
    row = None
    try:
        cur.execute(f"""
            SELECT
                COUNT(DISTINCT po.po_no),
                COUNT(DISTINCT po.po_no) FILTER (WHERE po.status = '0'),
                COUNT(DISTINCT po.po_no) FILTER (WHERE po.status = '1'),
                COUNT(DISTINCT po.po_no) FILTER (WHERE po.status = '2'),
                COUNT(DISTINCT po.po_no) FILTER (WHERE po.status = '3'),
                COUNT(DISTINCT po.po_no) FILTER (WHERE po.status = '4'),
                COUNT(DISTINCT po.po_no) FILTER (WHERE po.status = '5'),
                COUNT(DISTINCT po.po_no) FILTER (WHERE po.status = '6'),
                COUNT(DISTINCT po.po_no) FILTER (WHERE po.status = '7'),
                COALESCE(SUM(po.amount), 0)
            FROM public.purchase_order po
            INNER JOIN public.purchase_order_item poi ON poi.po_no = po.po_no
            WHERE {dc} {OZON_CLAUSE['order']}
        """, params)
        row = cur.fetchone()
    finally:
        cur.close()

    return OrderOverview(
        total=int(row[0]) if row else 0,
        status_0_pending_submit=int(row[1]) if row else 0,
        status_1_submitted=int(row[2]) if row else 0,
        status_2_pending_approval=int(row[3]) if row else 0,
        status_3_pending_receipt=int(row[4]) if row else 0,
        status_4_partial_receipt=int(row[5]) if row else 0,
        status_5_exception=int(row[6]) if row else 0,
        status_6_cancelled=int(row[7]) if row else 0,
        status_7_completed=int(row[8]) if row else 0,
        total_amount=float(row[9]) if row and row[9] else 0.0,
    )


@router.get("/order/list", response_model=OrderListResponse)
def order_list(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    pg=Depends(get_oms_pg),
):
    dc, params = _date_clause(date_from, date_to, "po")
    cur = pg.cursor()
    try:
        cur.execute(f"""
            SELECT COUNT(DISTINCT po.po_no)
            FROM public.purchase_order po
            INNER JOIN public.purchase_order_item poi ON poi.po_no = po.po_no
            WHERE {dc} {OZON_CLAUSE['order']}
        """, params)
        total = int(cur.fetchone()[0])

        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size
        cur.execute(f"""
            SELECT DISTINCT ON (po.po_no)
                po.po_no, po.status, po.vendor_id, po.amount, po.currency_code,
                po.create_time, po.receipt_date,
                (SELECT COUNT(*) FROM public.purchase_order_item poi2 WHERE poi2.po_no = po.po_no),
                COALESCE((SELECT SUM(poi2.qty) FROM public.purchase_order_item poi2 WHERE poi2.po_no = po.po_no), 0),
                po.memo, po.logistics_name, po.logistics_num
            FROM public.purchase_order po
            INNER JOIN public.purchase_order_item poi ON poi.po_no = po.po_no
            WHERE {dc} {OZON_CLAUSE['order']}
            ORDER BY po.po_no, po.create_time DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """, params)
        rows = cur.fetchall()
    finally:
        cur.close()

    items = [
        OrderListItem(
            po_no=r[0],
            status=r[1],
            status_label=ORDER_STATUS_LABELS.get(r[1] or "", r[1] or ""),
            vendor_id=_str(r[2]),
            amount=float(r[3]) if r[3] else 0.0,
            currency_code=r[4],
            create_time=_fmt_val(r[5]),
            receipt_date=_fmt_val(r[6]),
            item_count=int(r[7]) if r[7] else 0,
            total_qty=float(r[8]) if r[8] else 0.0,
            memo=r[9],
            logistics_name=r[10],
            logistics_num=r[11],
        )
        for r in rows
    ]
    return OrderListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/order/{po_no}", response_model=OrderDetail)
def order_detail(po_no: str, pg=Depends(get_oms_pg)):
    cur = pg.cursor()
    try:
        cur.execute("""
            SELECT po_no, status, vendor_id, location_id, subsidiary_id,
                   amount, untaxed_amount, tax_amount, currency_code,
                   create_time, update_time, receipt_date, trandate, memo,
                   sku_type, purchase_platform, logistics_name, logistics_num,
                   payment_status, is_year_stock, cancel_reason, tax_free_flag,
                   purchase_dept_type
            FROM public.purchase_order WHERE po_no = %s
        """, (po_no,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"采购单 {po_no} 不存在")

        cur.execute("""
            SELECT row_id, item_id, price, qty, untaxed_amount, tax_rate,
                   receipt_qty, return_qty, expect_receipt_date, expect_date,
                   po_plan_no, plan_row_id, memo, package_qty, marketplace_code,
                   sale_platform, main_sku_id, track_status, pending_shipment_qty,
                   accepted_time, check_date, already_listed_time
            FROM public.purchase_order_item
            WHERE po_no = %s ORDER BY row_id
        """, (po_no,))
        items = cur.fetchall()
    finally:
        cur.close()

    return OrderDetail(
        po_no=row[0],
        status=row[1],
        status_label=ORDER_STATUS_LABELS.get(row[1] or "", row[1] or ""),
        vendor_id=_str(row[2]), location_id=_str(row[3]), subsidiary_id=_str(row[4]),
        amount=float(row[5]) if row[5] else 0.0,
        untaxed_amount=float(row[6]) if row[6] else 0.0,
        tax_amount=float(row[7]) if row[7] else 0.0,
        currency_code=row[8],
        create_time=_fmt_val(row[9]), update_time=_fmt_val(row[10]),
        receipt_date=_fmt_val(row[11]), trandate=_fmt_val(row[12]),
        memo=row[13], sku_type=_str(row[14]), purchase_platform=_str(row[15]),
        logistics_name=row[16], logistics_num=row[17],
        payment_status=_str(row[18]), is_year_stock=_str(row[19]),
        cancel_reason=row[20], tax_free_flag=_str(row[21]),
        purchase_dept_type=_str(row[22]),
        items=[
            OrderItemDetail(
                row_id=int(r[0]) if r[0] else 0,
                item_id=r[1],
                price=float(r[2]) if r[2] else 0.0,
                qty=float(r[3]) if r[3] else 0.0,
                untaxed_amount=float(r[4]) if r[4] else 0.0,
                tax_rate=float(r[5]) if r[5] else 0.0,
                receipt_qty=float(r[6]) if r[6] else 0.0,
                return_qty=float(r[7]) if r[7] else 0.0,
                expect_receipt_date=_fmt_val(r[8]),
                expect_date=_fmt_val(r[9]),
                po_plan_no=r[10],
                plan_row_id=int(r[11]) if r[11] else 0,
                memo=r[12],
                package_qty=float(r[13]) if r[13] else 0.0,
                marketplace_code=r[14], sale_platform=r[15],
                main_sku_id=_str(r[16]), track_status=r[17],
                pending_shipment_qty=float(r[18]) if r[18] else 0.0,
                accepted_time=_fmt_val(r[19]),
                check_date=_fmt_val(r[20]),
                already_listed_time=_fmt_val(r[21]),
            )
            for r in items
        ],
    )


# ═══════════════════════════════════════════════════════════════
# 头程发货 (first_leg_shipping_order)
# ═══════════════════════════════════════════════════════════════

@router.get("/shipping/overview", response_model=ShippingOverview)
def shipping_overview(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    pg=Depends(get_oms_pg),
):
    dc, params = _date_clause(date_from, date_to, "fso")
    cur = pg.cursor()
    row = None
    try:
        cur.execute(f"""
            SELECT
                COUNT(DISTINCT fso.order_code),
                COUNT(DISTINCT fso.order_code) FILTER (WHERE fso.order_status = '1'),
                COUNT(DISTINCT fso.order_code) FILTER (WHERE fso.order_status = '2'),
                COUNT(DISTINCT fso.order_code) FILTER (WHERE fso.order_status IN ('3','4')),
                COUNT(DISTINCT fso.order_code) FILTER (WHERE fso.order_status IN ('7','8','10')),
                COUNT(DISTINCT fso.order_code) FILTER (WHERE fso.order_status = '11'),
                COUNT(DISTINCT fso.order_code) FILTER (WHERE fso.order_status IN ('12','13')),
                COUNT(DISTINCT fso.order_code) FILTER (WHERE fso.order_status = '9'),
                COALESCE(SUM(fsoi.final_shipping_num), 0)
            FROM public.first_leg_shipping_order fso
            INNER JOIN public.first_leg_shipping_order_item fsoi ON fsoi.shipping_order_code = fso.order_code
            INNER JOIN public.purchase_plan_item ppi ON ppi.po_plan_no = fsoi.source_order_code
            WHERE {dc} {OZON_CLAUSE['shipping']}
        """, params)
        row = cur.fetchone()
    finally:
        cur.close()

    return ShippingOverview(
        total=int(row[0]) if row else 0,
        status_1_pending_push=int(row[1]) if row else 0,
        status_2_pending_pick=int(row[2]) if row else 0,
        status_3_4_picked_packed=int(row[3]) if row else 0,
        status_7_8_10_pending_ship=int(row[4]) if row else 0,
        status_11_shipped=int(row[5]) if row else 0,
        status_12_13_arrived=int(row[6]) if row else 0,
        status_9_cancelled=int(row[7]) if row else 0,
        total_item_qty=float(row[8]) if row and row[8] else 0.0,
    )


@router.get("/shipping/list", response_model=ShippingListResponse)
def shipping_list(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    pg=Depends(get_oms_pg),
):
    dc, params = _date_clause(date_from, date_to, "fso")
    cur = pg.cursor()
    try:
        cur.execute(f"""
            SELECT COUNT(DISTINCT fso.order_code)
            FROM public.first_leg_shipping_order fso
            INNER JOIN public.first_leg_shipping_order_item fsoi ON fsoi.shipping_order_code = fso.order_code
            INNER JOIN public.purchase_plan_item ppi ON ppi.po_plan_no = fsoi.source_order_code
            WHERE {dc} {OZON_CLAUSE['shipping']}
        """, params)
        total = int(cur.fetchone()[0])

        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size
        cur.execute(f"""
            SELECT DISTINCT ON (fso.order_code)
                fso.order_code, fso.order_status, fso.channel_code,
                fso.shipping_warehouse_id, fso.destination_warehouse_id,
                fso.destination_country_code, fso.create_time,
                fso.shipping_time, fso.arrived_time,
                (SELECT COUNT(*) FROM public.first_leg_shipping_order_item fsoi2 WHERE fsoi2.shipping_order_code = fso.order_code),
                fso.plan_code, fso.logistics_order, fso.is_direct_ship, fso.remark
            FROM public.first_leg_shipping_order fso
            INNER JOIN public.first_leg_shipping_order_item fsoi ON fsoi.shipping_order_code = fso.order_code
            INNER JOIN public.purchase_plan_item ppi ON ppi.po_plan_no = fsoi.source_order_code
            WHERE {dc} {OZON_CLAUSE['shipping']}
            ORDER BY fso.order_code, fso.create_time DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """, params)
        rows = cur.fetchall()
    finally:
        cur.close()

    items = [
        ShippingListItem(
            order_code=r[0],
            order_status=r[1],
            status_label=SHIPPING_STATUS_LABELS.get(r[1] or "", r[1] or ""),
            channel_code=r[2],
            shipping_warehouse_id=_str(r[3]),
            destination_warehouse_id=_str(r[4]),
            destination_country_code=r[5],
            create_time=_fmt_val(r[6]),
            shipping_time=_fmt_val(r[7]),
            arrived_time=_fmt_val(r[8]),
            item_count=int(r[9]) if r[9] else 0,
            plan_code=r[10],
            logistics_order=r[11],
            is_direct_ship=r[12],
            remark=r[13],
        )
        for r in rows
    ]
    return ShippingListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/shipping/{order_code}", response_model=ShippingDetail)
def shipping_detail(order_code: str, pg=Depends(get_oms_pg)):
    cur = pg.cursor()
    try:
        cur.execute("""
            SELECT order_code, order_status, plan_code, plan_type, channel_code,
                   shipping_warehouse_id, destination_warehouse_id, destination_country_code,
                   receiving_platform, third_order_code, create_time, update_time,
                   shipping_time, arrived_time, shelving_time, logistics_order,
                   remark, merge_tag, package_type, is_agl, is_official_provider,
                   is_direct_ship, cancel_reason, tax_free_flag,
                   shipping_plan_time, ship_date, form_id
            FROM public.first_leg_shipping_order WHERE order_code = %s
        """, (order_code,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"发货单 {order_code} 不存在")

        cur.execute("""
            SELECT row_id, item_id, seller_sku, final_shipping_num, planed_shipping_num,
                   operation_shipping_num, package_qty, package_volume, package_weight,
                   source_order_code, source_order_type, po_no, store_id, fnsku,
                   material, main_sku_id, warehouse_item_code, inbound_putaway_qty,
                   qc_status
            FROM public.first_leg_shipping_order_item
            WHERE shipping_order_code = %s ORDER BY row_id
        """, (order_code,))
        items = cur.fetchall()
    finally:
        cur.close()

    return ShippingDetail(
        order_code=row[0],
        order_status=row[1],
        status_label=SHIPPING_STATUS_LABELS.get(row[1] or "", row[1] or ""),
        plan_code=row[2], plan_type=row[3], channel_code=row[4],
        shipping_warehouse_id=_str(row[5]), destination_warehouse_id=_str(row[6]),
        destination_country_code=row[7],
        receiving_platform=row[8], third_order_code=row[9],
        create_time=_fmt_val(row[10]), update_time=_fmt_val(row[11]),
        shipping_time=_fmt_val(row[12]), arrived_time=_fmt_val(row[13]),
        shelving_time=_fmt_val(row[14]), logistics_order=row[15],
        remark=row[16], merge_tag=row[17], package_type=row[18],
        is_agl=row[19], is_official_provider=row[20],
        is_direct_ship=row[21], cancel_reason=row[22], tax_free_flag=_str(row[23]),
        shipping_plan_time=_fmt_val(row[24]), ship_date=_fmt_val(row[25]),
        form_id=_str(row[26]),
        items=[
            ShippingItemDetail(
                row_id=int(r[0]) if r[0] else 0,
                item_id=r[1], seller_sku=r[2],
                final_shipping_num=float(r[3]) if r[3] else 0.0,
                planed_shipping_num=float(r[4]) if r[4] else 0.0,
                operation_shipping_num=float(r[5]) if r[5] else 0.0,
                package_qty=float(r[6]) if r[6] else 0.0,
                package_volume=_fmt_val(r[7]), package_weight=_fmt_val(r[8]),
                source_order_code=r[9], source_order_type=r[10],
                po_no=r[11], store_id=_str(r[12]), fnsku=r[13],
                material=r[14], main_sku_id=_str(r[15]),
                warehouse_item_code=r[16],
                inbound_putaway_qty=float(r[17]) if r[17] else 0.0,
                qc_status=r[18],
            )
            for r in items
        ],
    )
