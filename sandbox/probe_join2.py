"""修正版：8-20 空行与主表匹配 + 8-21 凌晨各表活动"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

print("=== products 表的时间列 ===")
for r in c.execute(text("""
    SELECT column_name FROM information_schema.columns
    WHERE table_schema='ozon' AND table_name='products'
      AND (column_name LIKE '%time%' OR column_name LIKE '%sync%' OR column_name LIKE '%update%')
""")):
    print(f"  {r[0]}")

print("\n=== 8-20 快照空值行与主表匹配（现在）===")
for r in c.execute(text("""
    SELECT s.store_id, COUNT(*) AS snap_rows,
           COUNT(m.sku_id) AS matched_mgmt,
           COUNT(m.green_price_rub) AS mgmt_has_green
    FROM ozon.sku_daily_snapshot s
    LEFT JOIN ozon.sku_management m ON m.store_id=s.store_id AND m.sku_id=s.sku_id
    WHERE s.record_date='2026-08-20' AND s.green_price IS NULL
    GROUP BY s.store_id ORDER BY s.store_id
""")):
    print(f"  店{r[0]}: 8-20空值行={r[1]}  匹配到主表={r[2]}  主表有绿标价={r[3]}")

print("\n=== 8-21 05:00 前后 stocks 活动 ===")
for r in c.execute(text("""
    SELECT synced_at::timestamp(0) AS s, COUNT(*) FROM ozon.stocks
    WHERE synced_at >= '2026-08-20 22:00' AND synced_at < '2026-08-21 08:00'
    GROUP BY s ORDER BY s LIMIT 10
""")):
    print(f"  {r[0]}: {r[1]} 行")

print("\n=== 8-21 05:00 前后 postings 活动 ===")
for r in c.execute(text("""
    SELECT created_at::date AS d, COUNT(*) FROM ozon.postings
    WHERE created_at >= '2026-08-20 22:00' AND created_at < '2026-08-21 08:00'
    GROUP BY d ORDER BY d
""")):
    print(f"  {r[0]}: {r[1]} 行")

print("\n=== 8-20 快照 107 个 NULL 行的 synced_at 精确值（前3/后3）===")
for r in c.execute(text("""
    SELECT store_id, synced_at::timestamp(3) FROM ozon.sku_daily_snapshot
    WHERE record_date='2026-08-20' AND green_price IS NULL
    ORDER BY synced_at, store_id LIMIT 3
""")):
    print(f"  {r[0]} {r[1]}")
for r in c.execute(text("""
    SELECT store_id, synced_at::timestamp(3) FROM ozon.sku_daily_snapshot
    WHERE record_date='2026-08-20' AND green_price IS NULL
    ORDER BY synced_at DESC, store_id LIMIT 3
""")):
    print(f"  {r[0]} {r[1]}")
c.close()
