"""查 8-20 快照现状：哪些有值、哪些没有、行是什么时候生成的"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

print("=== 1. 8-20 快照行概览（按店铺）===")
for r in c.execute(text("""
    SELECT store_id, COUNT(*) AS total, COUNT(green_price) AS has_green,
           MIN(synced_at) AS first_sync, MAX(synced_at) AS last_sync
    FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-20'
    GROUP BY store_id ORDER BY store_id
""")):
    print(f"  店铺{r[0]}: 总={r[1]}  有绿标价={r[2]}  生成时间={r[3]} ~ {r[4]}")

print("\n=== 2. 8-20 有绿标价的行（这些是今天编辑过的 SKU？）===")
for r in c.execute(text("""
    SELECT s.store_id, s.sku_id, s.green_price, s.discount_pct, s.synced_at,
           m.updated_at AS mgmt_updated
    FROM ozon.sku_daily_snapshot s
    LEFT JOIN ozon.sku_management m ON m.store_id=s.store_id AND m.sku_id=s.sku_id
    WHERE s.record_date='2026-08-20' AND s.green_price IS NOT NULL
    ORDER BY s.synced_at
""")):
    print(f"  店{r[0]} sku={r[1]} 绿标={r[2]} 折扣={r[3]} 快照生成={r[4]} 主表更新={r[5]}")

print("\n=== 3. 各店最新归档日期（5:00 调度每天生成前一天）===")
for r in c.execute(text("""
    SELECT store_id, MAX(record_date) FROM ozon.sku_daily_snapshot GROUP BY store_id ORDER BY store_id
""")):
    print(f"  店铺{r[0]}: 最新归档日 = {r[1]}")

print("\n=== 4. 今天(8-20)各店主表被编辑过的 SKU 数 ===")
for r in c.execute(text("""
    SELECT store_id, COUNT(*) FROM ozon.sku_management
    WHERE updated_at::date = '2026-08-20' GROUP BY store_id ORDER BY store_id
""")):
    print(f"  店铺{r[0]}: {r[1]} 个")
c.close()
