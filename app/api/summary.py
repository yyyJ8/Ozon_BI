"""看板数据 API"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, SkuDailySummary
from app.schemas.summary import SummaryItem, SummaryStats, DateRange

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("", response_model=list[SummaryItem])
def list_summary(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    sku_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """查询日汇总数据，支持按日期范围和 SKU 筛选"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=30)

    q = db.query(
        SkuDailySummary,
        Product.name,
        Product.primary_image,
        Product.offer_id,
    ).outerjoin(
        Product,
        SkuDailySummary.sku_id == Product.sku_id,
    ).filter(
        SkuDailySummary.record_date.between(date_from, date_to),
    )

    if sku_id:
        q = q.filter(SkuDailySummary.sku_id == sku_id)

    rows = q.order_by(
        SkuDailySummary.record_date.desc(),
        SkuDailySummary.sku_id,
    ).all()

    result = []
    for s, name, primary_image, offer_id in rows:
        result.append(SummaryItem(
            date=s.record_date,
            sku_id=s.sku_id,
            offer_id=offer_id or s.offer_id,
            name=name,
            primary_image=primary_image,
            stock_present=s.stock_present,
            stock_reserved=s.stock_reserved,
            ordered_units=s.ordered_units,
            revenue=s.revenue,
            returns_amount=s.returns_amount,
            commissions=s.commissions,
            logistics_costs=s.logistics_costs,
            storage_fees=s.storage_fees,
            advertising=s.advertising,
            other_costs=s.other_costs,
            net_profit=s.net_profit,
            profit_margin=s.profit_margin,
            data_quality=s.data_quality,
        ))
    return result


@router.get("/stats", response_model=SummaryStats)
def summary_stats(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    sku_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """看板顶部汇总卡数据"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=30)

    q = db.query(
        func.sum(SkuDailySummary.revenue).label("total_revenue"),
        func.sum(SkuDailySummary.net_profit).label("total_net_profit"),
        func.avg(SkuDailySummary.profit_margin).label("avg_profit_margin"),
        func.sum(SkuDailySummary.ordered_units).label("total_ordered_units"),
        func.sum(SkuDailySummary.commissions).label("total_commissions"),
        func.sum(SkuDailySummary.logistics_costs).label("total_logistics"),
        func.sum(SkuDailySummary.returns_amount).label("total_returns"),
        func.sum(SkuDailySummary.storage_fees).label("total_storage"),
        func.sum(SkuDailySummary.advertising).label("total_advertising"),
        func.sum(SkuDailySummary.other_costs).label("total_other_costs"),
        func.count(func.distinct(SkuDailySummary.record_date)).label("day_count"),
        func.count(func.distinct(SkuDailySummary.sku_id)).label("sku_count"),
    ).filter(
        SkuDailySummary.record_date.between(date_from, date_to),
    )

    if sku_id:
        q = q.filter(SkuDailySummary.sku_id == sku_id)

    row = q.first()
    stats = SummaryStats(
        total_revenue=Decimal(str(row.total_revenue or 0)),
        total_net_profit=Decimal(str(row.total_net_profit or 0)),
        avg_profit_margin=Decimal(str(row.avg_profit_margin or 0)),
        total_ordered_units=int(row.total_ordered_units or 0),
        total_commissions=Decimal(str(row.total_commissions or 0)),
        total_logistics=Decimal(str(row.total_logistics or 0)),
        total_returns=Decimal(str(row.total_returns or 0)),
        total_storage=Decimal(str(row.total_storage or 0)),
        total_advertising=Decimal(str(row.total_advertising or 0)),
        total_other_costs=Decimal(str(row.total_other_costs or 0)),
        day_count=int(row.day_count or 0),
        sku_count=int(row.sku_count or 0),
    )
    return stats


@router.get("/date-range", response_model=DateRange)
def summary_date_range(db: Session = Depends(get_db)):
    """数据可用日期范围（用于前端日期选择器限制）"""
    row = db.query(
        func.min(SkuDailySummary.record_date).label("min_date"),
        func.max(SkuDailySummary.record_date).label("max_date"),
    ).first()
    today = date.today()
    return DateRange(
        min_date=row.min_date or today,
        max_date=min(row.max_date or today, today),
    )
