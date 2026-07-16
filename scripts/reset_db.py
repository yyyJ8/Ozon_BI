"""
清空重建 ozon schema 的 5 张表（带字段注释）

运行: python scripts/reset_db.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from sqlalchemy import inspect, text

from app.database import Base, engine
from app.models import (
    Product, Stock, SkuDailySummary, FinanceTransaction, SyncLog,
    AdCampaign, AdDailyStats, AdCampaignSkuMap, AdSkuDailyStats, Posting,
)


def reset_tables():
    logger.info("=== 清空重建 ozon 表 ===")

    # 1. 删除所有表（先删有外键依赖的，CASCADE 兜底）
    with engine.connect() as conn:
        conn.execute(text("""
            DROP TABLE IF EXISTS ozon.ad_sku_daily_stats CASCADE;
            DROP TABLE IF EXISTS ozon.ad_campaign_sku_map CASCADE;
            DROP TABLE IF EXISTS ozon.ad_daily_stats CASCADE;
            DROP TABLE IF EXISTS ozon.ad_campaigns CASCADE;
            DROP TABLE IF EXISTS ozon.stocks CASCADE;
            DROP TABLE IF EXISTS ozon.sku_daily_summary CASCADE;
            DROP TABLE IF EXISTS ozon.finance_transactions CASCADE;
            DROP TABLE IF EXISTS ozon.postings CASCADE;
            DROP TABLE IF EXISTS ozon.sync_log CASCADE;
            DROP TABLE IF EXISTS ozon.products CASCADE;
        """))
        conn.commit()
    logger.info("已删除所有旧表")

    # 2. 重新建表（comment 参数会自动生成 COMMENT ON COLUMN）
    Base.metadata.create_all(bind=engine)
    logger.info("已重建所有表（含字段注释）")

    # 3. 验证表结构
    inspector = inspect(engine)
    tables = [
        "products", "stocks", "sku_daily_summary", "finance_transactions",
        "postings", "sync_log",
        "ad_campaigns", "ad_daily_stats", "ad_campaign_sku_map", "ad_sku_daily_stats",
    ]
    for tname in tables:
        columns = inspector.get_columns(tname, schema="ozon")
        print(f"\n--- {tname} ({len(columns)} 字段) ---")
        for col in columns:
            pk = "PK" if col.get("primary_key") else ""
            comment = col.get("comment", "")
            print(f"  {col['name']:30s} {str(col['type']):25s} {pk}  # {comment}")


if __name__ == "__main__":
    reset_tables()
