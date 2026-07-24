"""广告数据 API"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AdCampaign, AdDailyStats, AdCampaignSkuMap, AdSkuDailyStats, Product,
)
from app.schemas.advertising import (
    AdCampaignItem, AdDailyStatItem, AdSkuDailyItem, AdSkuDetailItem, AdSummary, AdTrendItem,
)

router = APIRouter(prefix="/advertising", tags=["advertising"])

STORE_ID = Query(default=1, description="店铺 ID，0=全部店铺")


def _by_store(model, store_id: int):
    """store_id=0 时不加店铺过滤，返回 TRUE"""
    from sqlalchemy import true
    return model.store_id == store_id if store_id != 0 else true()


# ── 1. 活动列表 ───────────────────────────────────────────

@router.get("/campaigns", response_model=list[AdCampaignItem])
def list_campaigns(
    campaign_type: Optional[str] = Query(default=None, description="活动类型过滤"),
    state: Optional[str] = Query(default=None, description="活动状态过滤"),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    """广告活动列表，含期间内汇总统计"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=30)

    stat_sub = (
        db.query(
            AdDailyStats.store_id,
            AdDailyStats.campaign_id,
            func.sum(AdDailyStats.spend).label("total_spend"),
            func.sum(AdDailyStats.orders_count).label("total_orders"),
            func.sum(AdDailyStats.orders_sum).label("total_orders_sum"),
            func.sum(AdDailyStats.impressions).label("total_impressions"),
            func.sum(AdDailyStats.clicks).label("total_clicks"),
        )
        .filter(
            _by_store(AdDailyStats, store_id),
            AdDailyStats.stat_date.between(date_from, date_to),
        )
        .group_by(AdDailyStats.store_id, AdDailyStats.campaign_id)
        .subquery()
    )

    q = db.query(
        AdCampaign,
        func.coalesce(stat_sub.c.total_spend, 0).label("total_spend"),
        func.coalesce(stat_sub.c.total_orders, 0).label("total_orders"),
        func.coalesce(stat_sub.c.total_orders_sum, 0).label("total_orders_sum"),
        func.coalesce(stat_sub.c.total_impressions, 0).label("total_impressions"),
        func.coalesce(stat_sub.c.total_clicks, 0).label("total_clicks"),
    ).outerjoin(
        stat_sub,
        (AdCampaign.campaign_id == stat_sub.c.campaign_id)
        & (AdCampaign.store_id == stat_sub.c.store_id),
    )
    if store_id != 0:
        q = q.filter(AdCampaign.store_id == store_id)

    if campaign_type:
        q = q.filter(AdCampaign.campaign_type == campaign_type)
    if state:
        q = q.filter(AdCampaign.state == state)

    rows = q.order_by(
        func.coalesce(stat_sub.c.total_spend, 0).desc(),
        AdCampaign.campaign_id,
    ).all()

    campaign_ids = [c.campaign_id for c, *_ in rows]
    mapping_map: dict[str, tuple] = {}
    if campaign_ids:
        mappings = db.query(AdCampaignSkuMap).filter(
            _by_store(AdCampaignSkuMap, store_id),
            AdCampaignSkuMap.campaign_id.in_(campaign_ids),
        ).all()
        for m in mappings:
            if m.campaign_id not in mapping_map:
                mapping_map[m.campaign_id] = (m.sku_id, m.offer_id)

    result = []
    for c, tspend, torders, tsum, timp, tclick in rows:
        msku, moffer = mapping_map.get(c.campaign_id, (None, None))
        result.append(AdCampaignItem(
            campaign_id=c.campaign_id,
            title=c.title,
            campaign_type=c.campaign_type,
            state=c.state,
            budget=c.budget,
            total_spend=Decimal(str(tspend or 0)),
            total_orders=int(torders or 0),
            total_orders_sum=Decimal(str(tsum or 0)),
            total_impressions=int(timp or 0),
            total_clicks=int(tclick or 0),
            mapped_sku_id=msku,
            mapped_offer_id=moffer,
        ))
    return result


# ── 2. 活动每日明细 ──────────────────────────────────────

@router.get("/campaigns/{campaign_id}/daily", response_model=list[AdDailyStatItem])
def campaign_daily(
    campaign_id: str,
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    """某广告活动的每日维度数据"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=30)

    rows = db.query(AdDailyStats).filter(
        _by_store(AdDailyStats, store_id),
        AdDailyStats.campaign_id == campaign_id,
        AdDailyStats.stat_date.between(date_from, date_to),
    ).order_by(AdDailyStats.stat_date).all()

    return [
        AdDailyStatItem(
            stat_date=r.stat_date,
            impressions=r.impressions,
            clicks=r.clicks,
            spend=r.spend,
            orders_count=r.orders_count,
            orders_sum=r.orders_sum,
        )
        for r in rows
    ]


# ── 2.5. 每日趋势 ──────────────────────────────────────

@router.get("/trend", response_model=list[AdTrendItem])
def advertising_trend(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    campaign_type: Optional[str] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    """广告每日趋势：花费 / 展示 / 点击 / 订单 / 已归因花费"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=30)

    daily_rows = (
        db.query(
            AdDailyStats.stat_date,
            func.sum(AdDailyStats.spend).label("total_spend"),
            func.sum(AdDailyStats.impressions).label("total_impressions"),
            func.sum(AdDailyStats.clicks).label("total_clicks"),
            func.sum(AdDailyStats.orders_count).label("total_orders_count"),
            func.sum(AdDailyStats.orders_sum).label("total_orders_sum"),
        )
        .filter(
            _by_store(AdDailyStats, store_id),
            AdDailyStats.stat_date.between(date_from, date_to),
        )
    )
    if campaign_type:
        daily_rows = daily_rows.join(
            AdCampaign,
            (AdDailyStats.campaign_id == AdCampaign.campaign_id)
            & (AdDailyStats.store_id == AdCampaign.store_id),
        ).filter(AdCampaign.campaign_type == campaign_type)

    daily_rows = daily_rows.group_by(AdDailyStats.stat_date).order_by(AdDailyStats.stat_date).all()

    mapped_campaign_ids = db.query(
        AdCampaignSkuMap.campaign_id,
    ).filter(
        _by_store(AdCampaignSkuMap, store_id),
    ).distinct().subquery()

    mapped_rows = (
        db.query(
            AdDailyStats.stat_date,
            func.sum(AdDailyStats.spend).label("mapped_spend"),
        )
        .filter(
            _by_store(AdDailyStats, store_id),
            AdDailyStats.stat_date.between(date_from, date_to),
            AdDailyStats.campaign_id.in_(mapped_campaign_ids),
        )
        .group_by(AdDailyStats.stat_date)
        .all()
    )
    mapped_map = {
        r.stat_date: Decimal(str(r.mapped_spend or 0))
        for r in mapped_rows
    }

    return [
        AdTrendItem(
            date=r.stat_date,
            spend=Decimal(str(r.total_spend or 0)),
            impressions=int(r.total_impressions or 0),
            clicks=int(r.total_clicks or 0),
            orders_count=int(r.total_orders_count or 0),
            orders_sum=Decimal(str(r.total_orders_sum or 0)),
            mapped_spend=mapped_map.get(r.stat_date, Decimal("0")),
        )
        for r in daily_rows
    ]


# ── 3. SKU 广告费 ─────────────────────────────────────────

@router.get("/sku/{sku_id}", response_model=list[AdSkuDailyItem])
def sku_advertising(
    sku_id: int,
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    """某 SKU 的每日广告费用（通过活动映射聚合）"""
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=30)

    rows = (
        db.query(
            AdDailyStats.stat_date,
            func.sum(AdDailyStats.spend).label("total_spend"),
            func.count(func.distinct(AdDailyStats.campaign_id)).label("campaign_count"),
        )
        .join(
            AdCampaignSkuMap,
            (AdDailyStats.campaign_id == AdCampaignSkuMap.campaign_id)
            & (AdDailyStats.store_id == AdCampaignSkuMap.store_id),
        )
        .filter(
            _by_store(AdDailyStats, store_id),
            AdCampaignSkuMap.sku_id == sku_id,
            AdDailyStats.stat_date.between(date_from, date_to),
        )
        .group_by(AdDailyStats.stat_date)
        .order_by(AdDailyStats.stat_date)
        .all()
    )

    return [
        AdSkuDailyItem(
            stat_date=stat_date,
            spend=Decimal(str(total_spend or 0)),
            campaign_count=int(campaign_count or 0),
        )
        for stat_date, total_spend, campaign_count in rows
    ]


# ── 3.5. SKU 广告详情 ───────────────────────────────────

@router.get("/sku/{sku_id}/detail", response_model=list[AdSkuDetailItem])
def sku_ad_detail(
    sku_id: int,
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=30)

    q = db.query(AdSkuDailyStats).filter(
        AdSkuDailyStats.sku_id == sku_id,
        AdSkuDailyStats.stat_date.between(date_from, date_to),
    )
    if store_id != 0:
        q = q.filter(AdSkuDailyStats.store_id == store_id)
    rows = q.order_by(AdSkuDailyStats.stat_date.desc()).all()

    return [
        AdSkuDetailItem(
            stat_date=r.stat_date,
            campaign_id=r.campaign_id,
            sku_name=r.sku_name,
            sku_price=r.sku_price,
            impressions=r.impressions,
            clicks=r.clicks,
            ctr=r.ctr,
            add_to_cart=r.add_to_cart,
            avg_cpc=r.avg_cpc,
            spend=r.spend,
            sold_units=r.sold_units,
            sales_promotion=r.sales_promotion,
            drr_promotion=r.drr_promotion,
            drr_total=r.drr_total,
        )
        for r in rows
    ]


# ── 4. 广告总览 ───────────────────────────────────────────

@router.get("/summary", response_model=AdSummary)
def advertising_summary(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=30)

    agg = db.query(
        func.sum(AdDailyStats.spend).label("total_spend"),
        func.sum(AdDailyStats.orders_count).label("total_orders_count"),
        func.sum(AdDailyStats.orders_sum).label("total_orders_sum"),
        func.sum(AdDailyStats.impressions).label("total_impressions"),
        func.sum(AdDailyStats.clicks).label("total_clicks"),
    ).filter(
        _by_store(AdDailyStats, store_id),
        AdDailyStats.stat_date.between(date_from, date_to),
    ).first()

    type_rows = (
        db.query(
            AdCampaign.campaign_type,
            func.sum(AdDailyStats.spend).label("type_spend"),
            func.count(func.distinct(AdCampaign.campaign_id)).label("type_count"),
            func.sum(AdDailyStats.orders_sum).label("type_orders_sum"),
        )
        .join(
            AdCampaign,
            (AdDailyStats.campaign_id == AdCampaign.campaign_id)
            & (AdDailyStats.store_id == AdCampaign.store_id),
        )
        .filter(
            _by_store(AdDailyStats, store_id),
            AdDailyStats.stat_date.between(date_from, date_to),
        )
        .group_by(AdCampaign.campaign_type)
        .all()
    )

    by_type = {}
    for t, spend, cnt, osum in type_rows:
        by_type[t] = {
            "spend": float(spend or 0),
            "count": int(cnt or 0),
            "orders_sum": float(osum or 0),
        }

    mapped_campaign_ids = db.query(
        AdCampaignSkuMap.campaign_id,
    ).filter(
        _by_store(AdCampaignSkuMap, store_id),
    ).distinct().subquery()

    mapped = db.query(
        func.sum(AdDailyStats.spend),
    ).filter(
        _by_store(AdDailyStats, store_id),
        AdDailyStats.stat_date.between(date_from, date_to),
        AdDailyStats.campaign_id.in_(mapped_campaign_ids),
    ).scalar() or 0

    total_spend = float(agg.total_spend or 0)
    unmapped_spend = total_spend - float(mapped)

    active_campaign_ids = db.query(
        AdDailyStats.campaign_id,
    ).filter(
        _by_store(AdDailyStats, store_id),
        AdDailyStats.stat_date.between(date_from, date_to),
    ).distinct().subquery()

    campaign_count = db.query(
        func.count(active_campaign_ids.c.campaign_id),
    ).scalar() or 0

    active_count = (
        db.query(func.count(active_campaign_ids.c.campaign_id))
        .join(
            AdCampaign,
            active_campaign_ids.c.campaign_id == AdCampaign.campaign_id,
        )
        .filter(AdCampaign.state == "CAMPAIGN_STATE_RUNNING")
        .scalar() or 0
    )

    mapped_sku_count = (
        db.query(func.count(func.distinct(AdCampaignSkuMap.sku_id)))
        .filter(
            _by_store(AdCampaignSkuMap, store_id),
            AdCampaignSkuMap.campaign_id.in_(mapped_campaign_ids),
        )
        .scalar() or 0
    )

    return AdSummary(
        total_spend=Decimal(str(total_spend)),
        total_orders_count=int(agg.total_orders_count or 0),
        total_orders_sum=Decimal(str(agg.total_orders_sum or 0)),
        total_impressions=int(agg.total_impressions or 0),
        total_clicks=int(agg.total_clicks or 0),
        by_type=by_type,
        unmapped_spend=Decimal(str(unmapped_spend)),
        mapped_spend=Decimal(str(mapped)),
        campaign_count=int(campaign_count),
        active_campaign_count=int(active_count),
        mapped_sku_count=int(mapped_sku_count),
    )
