"""用 8-17 快照的绿标价/折扣回填 8-18（先 dry-run，再执行）"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

DRY_RUN = "--apply" not in sys.argv

e = create_engine(settings.database_url)
c = e.connect()

# ── 1. 统计可回填范围 ──
total_18 = c.execute(text("SELECT COUNT(*) FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-18'")).scalar()
fillable = c.execute(text("""
    SELECT COUNT(*) FROM ozon.sku_daily_snapshot s18
    JOIN ozon.sku_daily_snapshot s17
      ON s17.store_id = s18.store_id AND s17.sku_id = s18.sku_id AND s17.record_date = '2026-08-17'
    WHERE s18.record_date = '2026-08-18'
      AND s17.green_price IS NOT NULL
      AND s18.green_price IS NULL
""")).scalar()
same_sku = c.execute(text("""
    SELECT COUNT(*) FROM (
        SELECT store_id, sku_id FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-18'
        EXCEPT
        SELECT store_id, sku_id FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-17'
    ) t
""")).scalar()
print(f"8-18 总行数: {total_18}")
print(f"8-17 有绿标价且 8-18 无值、可回填: {fillable} 行")
print(f"8-18 有但 8-17 没有的 SKU（无法回填）: {same_sku} 个")

if same_sku:
    print("  这些 SKU 无法回填:")
    for r in c.execute(text("""
        SELECT store_id, sku_id FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-18'
        EXCEPT
        SELECT store_id, sku_id FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-17'
    """)):
        print("   ", r)

if DRY_RUN:
    print("\n[dry-run] 未执行修改。确认无误后加 --apply 参数执行。")
else:
    result = c.execute(text("""
        UPDATE ozon.sku_daily_snapshot s18
        SET green_price  = s17.green_price,
            discount_pct = s17.discount_pct
        FROM ozon.sku_daily_snapshot s17
        WHERE s17.store_id = s18.store_id AND s17.sku_id = s18.sku_id
          AND s17.record_date = '2026-08-17'
          AND s18.record_date = '2026-08-18'
          AND s17.green_price IS NOT NULL
          AND s18.green_price IS NULL
    """))
    c.commit()
    print(f"\n[已执行] 回填 {result.rowcount} 行 (8-18 ← 8-17)")

# ── 验证 ──
print("\n=== 验证：8-18 回填后覆盖情况 ===")
r = c.execute(text("""
    SELECT record_date, COUNT(*) AS total, COUNT(green_price) AS has_green,
           COUNT(discount_pct) AS has_discount
    FROM ozon.sku_daily_snapshot WHERE record_date IN ('2026-08-17','2026-08-18')
    GROUP BY record_date ORDER BY record_date
""")).fetchall()
for row in r:
    print(f"  {row[0]}  总={row[1]}  有绿标价={row[2]}  有折扣={row[3]}")

if not DRY_RUN:
    print("\n=== 8-18 抽样（与 8-17 对比）===")
    for row in c.execute(text("""
        SELECT s18.store_id, s18.sku_id, s17.green_price AS g17, s18.green_price AS g18,
               s17.discount_pct AS d17, s18.discount_pct AS d18
        FROM ozon.sku_daily_snapshot s18
        JOIN ozon.sku_daily_snapshot s17
          ON s17.store_id = s18.store_id AND s17.sku_id = s18.sku_id AND s17.record_date = '2026-08-17'
        WHERE s18.record_date = '2026-08-18' AND s18.green_price IS NOT NULL
        ORDER BY s18.sku_id LIMIT 5
    """)):
        print(f"  store={row[0]} sku={row[1]}  8-17绿标={row[2]}/{row[4]}折扣  8-18绿标={row[3]}/{row[5]}折扣")
c.close()
