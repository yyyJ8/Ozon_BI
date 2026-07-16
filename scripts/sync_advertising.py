"""
手动触发广告数据全量同步

  Step 1 (快速): 活动×天  GET /api/client/statistics/daily
    自动按30天窗口切分，覆盖任意时间段。无数据的窗口直接跳过。

  Step 2 (慢速): SKU×天   POST /api/client/statistics → poll → ZIP
    逐天请求异步报告，每天约1~2分钟。无数据的日期直接跳过。

用法:
  python scripts/sync_advertising.py                        # 默认 2026-04-01 ~ 今天
  python scripts/sync_advertising.py --from 2026-04-01      # 指定起始
  python scripts/sync_advertising.py --from 2026-06-01 --to 2026-07-15
  python scripts/sync_advertising.py --skip-sku             # 只跑活动级，跳过耗时的SKU明细
"""
import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

from app.clients.perf import get_perf_client
from app.database import SessionLocal
from app.services.advertising_sync import sync_advertising, sync_sku_advertising

DEFAULT_FROM = "2026-04-01"


def main():
    parser = argparse.ArgumentParser(description="广告数据全量同步")
    parser.add_argument("--from", dest="date_from", type=str,
                        default=DEFAULT_FROM,
                        help=f"起始日期 (默认 {DEFAULT_FROM})")
    parser.add_argument("--to", dest="date_to", type=str,
                        help="结束日期 (默认今天)")
    parser.add_argument("--skip-sku", action="store_true",
                        help="跳过 SKU 明细（仅活动级，速度快很多）")
    args = parser.parse_args()

    today = date.today()
    if args.date_to:
        end = datetime.strptime(args.date_to, "%Y-%m-%d").date()
    else:
        end = today
    start = datetime.strptime(args.date_from, "%Y-%m-%d").date()

    total_days = (end - start).days + 1
    logger.info(f"=== 广告数据全量同步: {start} ~ {end} ({total_days} 天) ===")
    logger.info("Step 1 活动×天 秒级，Step 2 SKU×天 约 1~2 分钟/天")

    client = get_perf_client()
    db = SessionLocal()

    try:
        # ── 1. 活动×天（GET 同步端点，自动按30天分片）──
        logger.info("─ Step 1/2: 活动级每日统计 ─")
        r1 = sync_advertising(
            db, client,
            date_from=start.isoformat(),
            date_to=end.isoformat(),
        )
        logger.info(f"  活动: {r1['campaigns_updated']} 个, "
                    f"日统计: {r1['daily_stats_inserted']} 新增, "
                    f"映射: {r1['sku_mappings_created']} 条, "
                    f"汇总: {r1['sku_summaries_updated']} 行")

        # ── 2. SKU×天（POST 异步报告，逐天请求）─────
        if args.skip_sku:
            logger.info("─ 跳过 SKU 明细 ─")
        else:
            logger.info(f"─ Step 2/2: SKU 明细 (逐天, ~{total_days} 天, "
                        f"约 {total_days}~{total_days * 2} 分钟) ─")
            r2 = sync_sku_advertising(
                db, client,
                date_from=start.isoformat(),
                date_to=end.isoformat(),
            )
            logger.info(f"  SKU明细: {r2['sku_inserted']} 新增, "
                        f"{r2['sku_updated']} 更新")

        logger.info("=== 广告数据全量同步完成 ===")

    except Exception as e:
        logger.error(f"同步异常: {e}")
        raise
    finally:
        client.close()
        db.close()


if __name__ == "__main__":
    main()
