"""验证前提：主表是否始终有绿标价/折扣；8-18 快照全 NULL 的成因"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

print("=== 1. 店铺5：products 数 vs sku_management 记录数 vs 有绿标价的记录数 ===")
r = c.execute(text("""
    SELECT
      (SELECT COUNT(*) FROM ozon.products WHERE store_id=5) AS products,
      (SELECT COUNT(*) FROM ozon.sku_management WHERE store_id=5) AS mgmt_rows,
      (SELECT COUNT(*) FROM ozon.sku_management WHERE store_id=5 AND green_price_rub IS NOT NULL) AS has_green,
      (SELECT COUNT(*) FROM ozon.sku_management WHERE store_id=5 AND discount_pct IS NOT NULL) AS has_discount
""")).fetchone()
print(f"  products={r[0]}  mgmt_rows={r[1]}  有绿标价={r[2]}  有折扣={r[3]}")

print("\n=== 2. 主表记录的时间分布（updated_at 最早/最晚）===")
r = c.execute(text("""
    SELECT MIN(updated_at), MAX(updated_at), COUNT(*) FROM ozon.sku_management WHERE store_id=5
""")).fetchone()
print(f"  最早更新={r[0]}  最晚更新={r[1]}  记录数={r[2]}")

print("\n=== 3. 8-18 快照行的生成情况（synced_at / offer_id 是否正常）===")
for r in c.execute(text("""
    SELECT record_date, MIN(synced_at) AS first_sync, MAX(synced_at) AS last_sync, COUNT(*) AS rows_cnt,
           COUNT(offer_id) AS has_offer, COUNT(green_price) AS has_green
    FROM ozon.sku_daily_snapshot WHERE store_id=5 AND record_date='2026-08-18'
    GROUP BY record_date
""")):
    print(f"  record_date={r[0]}  synced_at范围={r[1]}~{r[2]}  行数={r[3]}  有offer_id={r[4]}  有绿标价={r[5]}")

print("\n=== 4. 8-18 快照 vs 主表：同 SKU 主表值（现在）===")
rows = c.execute(text("""
    SELECT s.sku_id, s.green_price AS snap_green, m.green_price_rub AS mgmt_green,
           m.discount_pct AS mgmt_discount, m.updated_at
    FROM ozon.sku_daily_snapshot s
    LEFT JOIN ozon.sku_management m ON m.store_id=s.store_id AND m.sku_id=s.sku_id
    WHERE s.store_id=5 AND s.record_date='2026-08-18'
    ORDER BY s.sku_id LIMIT 15
""")).fetchall()
for r in rows:
    print(f"  sku={r[0]}  快照绿标价={r[1]}  主表绿标价={r[2]}  主表折扣={r[3]}  主表更新={r[4]}")

print("\n=== 5. 8-17 vs 8-18 vs 8-19 快照 synced_at（判断是否为调度生成）===")
for r in c.execute(text("""
    SELECT record_date, MIN(synced_at), MAX(synced_at), COUNT(*) FROM ozon.sku_daily_snapshot
    WHERE store_id=5 AND record_date IN ('2026-08-17','2026-08-18','2026-08-19')
    GROUP BY record_date ORDER BY record_date
""")):
    print(f"  {r[0]}  synced={r[1]}~{r[2]}  行数={r[3]}")
c.close()
