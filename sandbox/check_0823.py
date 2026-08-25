"""查 8-23 快照绿标价状态"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text
from app.config import settings

print(f"当前北京: {datetime.now()}")
print(f"当前莫斯科: {datetime.now(timezone(timedelta(hours=3)))}")

e = create_engine(settings.database_url)
c = e.connect()

print("\n=== 最近几天快照绿标价覆盖 ===")
for r in c.execute(text("""
    SELECT record_date, COUNT(*) AS total, COUNT(green_price) AS has_green,
           COUNT(*) - COUNT(green_price) AS null_green
    FROM ozon.sku_daily_snapshot
    WHERE record_date >= '2026-08-19'
    GROUP BY record_date ORDER BY record_date
""")):
    print(f"  {r[0]}  总={r[1]}  有绿标={r[2]}  缺失={r[3]}")

print("\n=== 8-23 快照 synced_at 分布 ===")
for r in c.execute(text("""
    SELECT synced_at::timestamp(0) AS s, COUNT(*) FROM ozon.sku_daily_snapshot
    WHERE record_date='2026-08-23' GROUP BY s ORDER BY s
""")):
    print(f"  {r[0]}: {r[1]} 行")

print("\n=== 8-23 缺失行 vs 主表现状 ===")
r = c.execute(text("""
    SELECT COUNT(*) AS null_rows,
           COUNT(m.green_price_rub) AS mgmt_has,
           COUNT(*) - COUNT(m.green_price_rub) AS mgmt_null
    FROM ozon.sku_daily_snapshot s
    LEFT JOIN ozon.sku_management m ON m.store_id=s.store_id AND m.sku_id=s.sku_id
    WHERE s.record_date='2026-08-23' AND s.green_price IS NULL
""")).fetchone()
print(f"  8-23缺失={r[0]}  主表有值={r[1]}  主表无值={r[2]}")
c.close()
