"""
同步编排 — 按顺序执行所有同步步骤
"""
from datetime import date, datetime, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.clients.ozon import OzonClient
from app.models import SyncLog
from app.services.product_sync import sync_products
from app.services.analytics_sync import sync_analytics
from app.services.finance_sync import sync_finance
from app.services.posting_sync import sync_postings
from app.services.returns_sync import sync_returns
from app.services.summary_service import build_summary


def _log_sync(db: Session, sync_type: str, status: str,
              records: int = 0, error: Optional[str] = None,
              date_from: Optional[date] = None, date_to: Optional[date] = None,
              batch_id: Optional[str] = None):
    """写入同步日志"""
    log = SyncLog(
        sync_type=sync_type,
        status=status,
        started_at=datetime.now(),
        completed_at=datetime.now() if status != "running" else None,
        records_processed=records,
        date_from=date_from,
        date_to=date_to,
        error_message=error,
        batch_id=batch_id,
    )
    db.add(log)
    db.commit()


def run_full_sync(db: Session, client: OzonClient,
                  days_back: int = 500) -> dict:
    """
    全量同步: 按顺序 商品 → 分析 → 财务 → 汇总
    默认拉取 ~1.5 年数据（500天），覆盖所有历史
    """
    batch_id = f"full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    today = date.today()
    start_date = today - timedelta(days=days_back)
    results = {}

    # ── 1. 商品同步 ──
    try:
        _log_sync(db, "products", "running", batch_id=batch_id)
        pr = sync_products(db, client)
        results["products"] = pr
        _log_sync(db, "products", "success",
                  records=pr["products_updated"], batch_id=batch_id)
    except Exception as e:
        logger.error(f"商品同步失败: {e}")
        _log_sync(db, "products", "failed", error=str(e), batch_id=batch_id)
        results["products"] = {"error": str(e)}
        return results  # 商品失败则中断

    # ── 2. 销售分析同步 ──
    try:
        _log_sync(db, "analytics", "running", batch_id=batch_id)
        ar = sync_analytics(db, client,
                            date_from=start_date.isoformat(),
                            date_to=today.isoformat())
        results["analytics"] = ar
        _log_sync(db, "analytics", "success",
                  records=ar["analytics_updated"], batch_id=batch_id)
    except Exception as e:
        logger.error(f"分析同步失败: {e}")
        _log_sync(db, "analytics", "failed", error=str(e), batch_id=batch_id)
        results["analytics"] = {"error": str(e)}

    # ── 3. 财务流水同步 ──
    try:
        _log_sync(db, "finance", "running", batch_id=batch_id)
        fr = sync_finance(db, client,
                          date_from=start_date.isoformat(),
                          date_to=today.isoformat(),
                          batch_id=batch_id)
        results["finance"] = fr
        _log_sync(db, "finance", "success",
                  records=fr["finance_inserted"], batch_id=batch_id)
    except Exception as e:
        logger.error(f"财务同步失败: {e}")
        _log_sync(db, "finance", "failed", error=str(e), batch_id=batch_id)
        results["finance"] = {"error": str(e)}

    # ── 4. 订单履约同步（增量: 最近30天到昨天 + 补齐缺失）──
    try:
        yesterday = today - timedelta(days=1)
        _log_sync(db, "postings", "running", batch_id=batch_id)
        pr = sync_postings(db, client,
                          date_from=(yesterday - timedelta(days=30)).isoformat(),
                          date_to=yesterday.isoformat())
        results["postings"] = pr
        _log_sync(db, "postings", "success",
                  records=pr.get("posting_list_inserted", 0) + pr.get("posting_get_inserted", 0),
                  batch_id=batch_id)
    except Exception as e:
        logger.error(f"订单履约同步失败: {e}")
        _log_sync(db, "postings", "failed", error=str(e), batch_id=batch_id)
        results["postings"] = {"error": str(e)}

    # ── 4.5. 退货数据同步（最近 90 天，退货状态变化周期较长）──
    try:
        _log_sync(db, "returns", "running", batch_id=batch_id)
        rr = sync_returns(db, client,
                          date_from=(yesterday - timedelta(days=90)).isoformat(),
                          date_to=yesterday.isoformat())
        results["returns"] = rr
        _log_sync(db, "returns", "success",
                  records=rr.get("returns_processed", 0), batch_id=batch_id)
    except Exception as e:
        logger.error(f"退货同步失败: {e}")
        _log_sync(db, "returns", "failed", error=str(e), batch_id=batch_id)
        results["returns"] = {"error": str(e)}

    # ── 5. 广告数据同步 ──
    from app.clients.perf import get_perf_client
    from app.services.advertising_sync import sync_advertising, sync_sku_advertising
    perf_client = get_perf_client()

    try:
        _log_sync(db, "advertising", "running", batch_id=batch_id)
        ar = sync_advertising(db, perf_client,
                              date_from=start_date.isoformat(),
                              date_to=today.isoformat(),
                              batch_id=batch_id)
        results["advertising"] = ar
        _log_sync(db, "advertising", "success",
                  records=ar.get("daily_stats_inserted", 0), batch_id=batch_id)
    except Exception as e:
        logger.error(f"广告同步失败: {e}")
        _log_sync(db, "advertising", "failed", error=str(e), batch_id=batch_id)
        results["advertising"] = {"error": str(e)}

    # ── 5.5. 广告 SKU 明细同步（仅最近N天，异步报告较慢）──
    try:
        _log_sync(db, "ad_sku_daily", "running", batch_id=batch_id)
        from app.config import settings
        sku_days = getattr(settings, 'ad_sync_days', 3)
        sku_from = (today - timedelta(days=sku_days)).isoformat()
        sr = sync_sku_advertising(db, perf_client,
                                  date_from=sku_from,
                                  date_to=today.isoformat())
        results["ad_sku_daily"] = sr
        _log_sync(db, "ad_sku_daily", "success",
                  records=sr.get("sku_inserted", 0), batch_id=batch_id)
    except Exception as e:
        logger.error(f"广告 SKU 明细同步失败: {e}")
        _log_sync(db, "ad_sku_daily", "failed", error=str(e), batch_id=batch_id)
        results["ad_sku_daily"] = {"error": str(e)}

    # ── 6. 构建汇总 ──
    try:
        _log_sync(db, "summary", "running", batch_id=batch_id)
        sr = build_summary(db, start_date, today)
        results["summary"] = sr
        _log_sync(db, "summary", "success",
                  records=sr["summary_updated"], batch_id=batch_id)
    except Exception as e:
        logger.error(f"汇总构建失败: {e}")
        _log_sync(db, "summary", "failed", error=str(e), batch_id=batch_id)
        results["summary"] = {"error": str(e)}

    return results
