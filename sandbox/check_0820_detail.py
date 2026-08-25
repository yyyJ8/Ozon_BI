"""查证：8-20 快照 NULL 行的主表对应情况 + 主表导入时间线"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

print("=== 1. 主表 sku_management 记录创建时间线（按店铺）===")
for r in c.execute(text("""
    SELECT store_id, COUNT(*) AS cnt,
           MIN(created_at) AS first_created, MAX(created_at) AS last_created,
           MIN(updated_at) AS first_updated, MAX(updated_at) AS last_updated
    FROM ozon.sku_management GROUP BY store_id ORDER BY store_id
""")):
    print(f"  店{r[0]}: {r[1]}条  created={r[2]}~{r[3]}  updated={r[4]}~{r[5]}")

print("\n=== 2. 8-20 快照 NULL 绿标价的行，主表现在是否有值 ===")
rows = c.execute(text("""
    SELECT s.store_id, COUNT(*) AS null_rows,
           COUNT(m.green_price_rub) AS mgmt_now_has,
           COUNT(*) - COUNT(m.green_price_rub) AS mgmt_now_null
    FROM ozon.sku_daily_snapshot s
    LEFT JOIN ozon.sku_management m ON m.store_id=s.store_id AND m.sku_id=s.sku_id
    WHERE s.record_date='2026-08-20' AND s.green_price IS NULL
    GROUP BY s.store_id ORDER BY s.store_id
""")).fetchall()
for r in rows:
    print(f"  店{r[0]}: 8-20空值行={r[1]}  主表现在有绿标价={r[2]}  主表现在仍无={r[3]}")

print("\n=== 3. 抽样：8-20 空值行对应的主表 updated_at（判断归档时是否有值）===")
for r in c.execute(text("""
    SELECT s.store_id, s.sku_id, m.green_price_rub AS mgmt_green, m.updated_at AS mgmt_updated, s.synced_at
    FROM ozon.sku_daily_snapshot s
    LEFT JOIN ozon.sku_management m ON m.store_id=s.store_id AND m.sku_id=s.sku_id
    WHERE s.record_date='2026-08-20' AND s.green_price IS NULL
    ORDER BY s.synced_at DESC, s.sku_id LIMIT 8
""")):
    print(f"  店{r[0]} sku={r[1]}  主表绿标={r[2]}  主表更新={r[3]}  快照生成={r[4]}")

print("\n=== 4. 8-20 快照全部行的 synced_at 分布 ===")
for r in c.execute(text("""
    SELECT synced_at::date AS d, COUNT(*) FROM ozon.sku_daily_snapshot
    WHERE record_date='2026-08-20' GROUP BY synced_at::date ORDER BY d
""")):
    print(f"  {r[0]}: {r[1]} 行")
c.close()
