"""定位调度异常开始时间：8-19 快照 16 个 NULL 行的主表现状"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

print("=== 8-19 快照中 NULL 绿标价的行（8-20 05:00 调度插入）===")
for r in c.execute(text("""
    SELECT s.store_id, s.sku_id, s.synced_at, m.green_price_rub AS mgmt_green, m.updated_at
    FROM ozon.sku_daily_snapshot s
    LEFT JOIN ozon.sku_management m ON m.store_id=s.store_id AND m.sku_id=s.sku_id
    WHERE s.record_date='2026-08-19' AND s.green_price IS NULL
    ORDER BY s.store_id, s.sku_id
""")):
    print(f"  store={r[0]} sku={r[1]} synced={r[2]}  主表现在绿标={r[3]}  主表更新={r[4]}")

print("\n=== 8-19 快照 97 个有值行的 synced_at 分布（判断是否导入脚本直写）===")
for r in c.execute(text("""
    SELECT synced_at::timestamp(0) AS s, COUNT(*) FROM ozon.sku_daily_snapshot
    WHERE record_date='2026-08-19' AND green_price IS NOT NULL
    GROUP BY s ORDER BY s
""")):
    print(f"  {r[0]}: {r[1]} 行")
c.close()
