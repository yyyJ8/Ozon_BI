"""
回填广告 SKU 日明细（历史数据）— 支持多店铺 + 限额断点续传

原理: 逐天请求 Ozon Performance API 异步报告（dateFrom=dateTo=当天），
     解压 ZIP 后解析 SKU 级别数据，写入 ad_sku_daily_stats。

限制: 每个店铺每天有异步报告请求限额，触发 429 后自动保存断点，
     明天重新运行即可从断点继续。

用法:
  python scripts/backfill_ad_sku.py --store-id 2                  # 回填最近 45 天
  python scripts/backfill_ad_sku.py --store-id 2 --days 30        # 最近 30 天
  python scripts/backfill_ad_sku.py --store-id 2 --from 2026-07-01 --to 2026-07-20
  python scripts/backfill_ad_sku.py --store-id 2 --resume          # 从上次断点继续
"""
import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

from app.clients.perf import get_perf_client
from app.database import SessionLocal
from app.models import Store

CHECKPOINT_DIR = Path(__file__).resolve().parent.parent / ".checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)


def _checkpoint_path(store_id: int) -> Path:
    return CHECKPOINT_DIR / f"ad_sku_backfill_store{store_id}.json"


def load_checkpoint(store_id: int) -> date | None:
    """读取上次断点日期，返回下一天（从那里继续）"""
    cp = _checkpoint_path(store_id)
    if cp.exists():
        data = json.loads(cp.read_text())
        next_date = date.fromisoformat(data["next_date"])
        logger.info(f"读取断点: 从 {next_date} 继续 (已完成到 {data['last_done']}, "
                    f"剩余 {data['remaining_days']} 天)")
        return next_date
    return None


def save_checkpoint(store_id: int, last_done: date, remaining: int,
                    error: str = "", end_date: date = None):
    """保存断点：记录已完成的最后一天和剩余天数"""
    cp = _checkpoint_path(store_id)
    data = {
        "store_id": store_id,
        "last_done": last_done.isoformat(),
        "next_date": (last_done + timedelta(days=1)).isoformat(),
        "remaining_days": remaining,
        "end_date": end_date.isoformat() if end_date else None,
        "error": error,
        "saved_at": datetime.now().isoformat(),
    }
    cp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    logger.info(f"断点已保存: {last_done} 完成, 剩余 {remaining} 天 → {cp}")


def clear_checkpoint(store_id: int):
    cp = _checkpoint_path(store_id)
    if cp.exists():
        cp.unlink()
        logger.info("断点已清除（全部完成）")


def sync_one_day(db, client, store_id: int, day: date) -> bool:
    """同步单天 SKU 广告明细，返回 True=成功"""
    from app.services.advertising_sync import sync_sku_advertising
    day_str = day.isoformat()
    try:
        result = sync_sku_advertising(
            db, client,
            date_from=day_str,
            date_to=day_str,
            store_id=store_id,
        )
        cnt = result.get("sku_inserted", 0) + result.get("sku_updated", 0)
        logger.info(f"  {day_str}: {cnt} 行")
        return True
    except Exception as e:
        msg = str(e)
        if "429" in msg or "Too Many" in msg:
            logger.warning(f"  {day_str}: 429 限额 → 停止")
            raise  # 抛出给外层处理断点
        elif "400" in msg:
            logger.info(f"  {day_str}: 无数据，跳过")
            return True  # 400 不是限额，继续
        else:
            logger.error(f"  {day_str}: 失败 → {msg}")
            return False


def main():
    parser = argparse.ArgumentParser(description="回填广告 SKU 日明细（多店铺+断点续传）")
    parser.add_argument("--store-id", type=int, required=True, help="店铺 ID")
    parser.add_argument("--days", type=int, default=45, help="回填最近N天 (默认45)")
    parser.add_argument("--from", dest="date_from", type=str, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", type=str, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--resume", action="store_true", help="从断点继续")
    args = parser.parse_args()

    # ── 1. 查店铺凭证 ──
    db = SessionLocal()
    store = db.query(Store).filter_by(id=args.store_id).first()
    if not store:
        logger.error(f"店铺 {args.store_id} 不存在")
        sys.exit(1)
    if not store.perf_client_id or not store.perf_client_secret:
        logger.error(f"店铺 {args.store_id} ({store.name}) 未配置广告 API")
        sys.exit(1)

    logger.info(f"店铺: {store.id} - {store.name}")

    # ── 2. 确定日期范围 ──
    today = date.today()

    if args.resume:
        start = load_checkpoint(args.store_id)
        if start is None:
            logger.error("没有断点记录，请用 --from/--days 指定范围")
            sys.exit(1)
        end = today - timedelta(days=1)  # 最多到昨天
    else:
        if args.date_to:
            end = min(datetime.strptime(args.date_to, "%Y-%m-%d").date(), today - timedelta(days=1))
        else:
            end = today - timedelta(days=1)  # 默认到昨天（今天的数据还没生成）

        if args.date_from:
            start = datetime.strptime(args.date_from, "%Y-%m-%d").date()
        else:
            start = end - timedelta(days=args.days - 1)

    day_count = (end - start).days + 1
    if day_count <= 0:
        logger.info("日期范围为空，无需同步")
        sys.exit(0)

    logger.info(f"=== 回填广告 SKU 明细: {start} ~ {end} ({day_count} 天) ===")

    client = get_perf_client(store.perf_client_id, store.perf_client_secret)

    success = 0
    skipped = 0
    cur = start
    try:
        while cur <= end:
            time.sleep(2)  # 请求间隔，缓解限流
            if sync_one_day(db, client, args.store_id, cur):
                success += 1
            else:
                skipped += 1
            cur += timedelta(days=1)
    except Exception as e:
        # 429 → 保存断点
        remaining = (end - cur).days + 1
        save_checkpoint(args.store_id, cur - timedelta(days=1), remaining,
                        error=str(e), end_date=end)
        logger.warning(f"遇到限额，已处理 {success} 天，剩余 {remaining} 天。"
                       f"明天运行: python scripts/backfill_ad_sku.py --store-id {args.store_id} --resume")
    else:
        clear_checkpoint(args.store_id)
        logger.info(f"全部完成: {success} 天成功, {skipped} 天跳过")

    client.close()
    db.close()


if __name__ == "__main__":
    main()
