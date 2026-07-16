"""
一次性回填广告 SKU 日明细（历史数据）

原理: 逐天请求 Ozon Performance API 异步报告（dateFrom=dateTo=当天），
     解压 ZIP 后解析 SKU 级别数据，写入 ad_sku_daily_stats。

限制: POST /api/client/statistics 每批最多 10 个活动，同时只能 1 个活跃请求。
     约 3 批/天 × ~20s/批 ≈ 1 分钟/天。45 天历史 ≈ 45 分钟。

用法:
  cd d:/OzonSku
  python scripts/backfill_ad_sku.py                  # 默认最近 45 天
  python scripts/backfill_ad_sku.py --days 30        # 最近 30 天
  python scripts/backfill_ad_sku.py --from 2026-07-01 --to 2026-07-15  # 指定范围
"""
import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

from app.clients.perf import get_perf_client
from app.database import SessionLocal
from app.services.advertising_sync import sync_sku_advertising


def main():
    parser = argparse.ArgumentParser(description="回填广告 SKU 日明细")
    parser.add_argument("--days", type=int, default=45,
                        help="回填最近N天 (默认45)")
    parser.add_argument("--from", dest="date_from", type=str,
                        help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", type=str,
                        help="结束日期 YYYY-MM-DD")
    args = parser.parse_args()

    today = date.today()
    if args.date_to:
        end = datetime.strptime(args.date_to, "%Y-%m-%d").date()
    else:
        end = today

    if args.date_from:
        start = datetime.strptime(args.date_from, "%Y-%m-%d").date()
    else:
        start = end - timedelta(days=args.days - 1)

    day_count = (end - start).days + 1
    logger.info(f"=== 回填广告 SKU 明细: {start} ~ {end} ({day_count} 天) ===")
    logger.info(f"预计耗时: ~{day_count * 1} 分钟")

    client = get_perf_client()
    db = SessionLocal()

    try:
        result = sync_sku_advertising(
            db, client,
            date_from=start.isoformat(),
            date_to=end.isoformat(),
        )
        logger.info(f"回填完成: {result}")
    except Exception as e:
        logger.error(f"回填失败: {e}")
        raise
    finally:
        client.close()
        db.close()


if __name__ == "__main__":
    main()
