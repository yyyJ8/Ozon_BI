"""回填 8-20 快照：用主表 sku_management 当前的绿标价/折扣（先 dry-run）"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

DRY_RUN = "--apply" not in sys.argv
e = create_engine(settings.database_url)
c = e.connect()

# 统计可回填行数（主表有绿标价 & 快照 8-20 该行 NULL）
fillable = c.execute(text("""
    SELECT COUNT(*) FROM ozon.sku_daily_snapshot s
    JOIN ozon.sku_management m ON m.store_id = s.store_id AND m.sku_id = s.sku_id
    WHERE s.record_date = '2026-08-20' AND s.green_price IS NULL
      AND m.green_price_rub IS NOT NULL
""")).scalar()
total_20 = c.execute(text("SELECT COUNT(*) FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-20'")).scalar()
already = c.execute(text("SELECT COUNT(*) FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-20' AND green_price IS NOT NULL")).scalar()
print(f"8-20 总行数={total_20}  已有绿标价={already}  本次可回填（主表有值）={fillable}  回填后仍空={total_20 - already - fillable}")

if DRY_RUN:
    print("\n[dry-run] 未执行。加 --apply 执行。")
else:
    result = c.execute(text("""
        UPDATE ozon.sku_daily_snapshot s
        SET green_price  = m.green_price_rub,
            discount_pct = m.discount_pct
        FROM ozon.sku_management m
        WHERE m.store_id = s.store_id AND m.sku_id = s.sku_id
          AND s.record_date = '2026-08-20'
          AND s.green_price IS NULL
          AND m.green_price_rub IS NOT NULL
    """))
    c.commit()
    print(f"\n[已执行] 回填 {result.rowcount} 行 (8-20 ← 主表当前绿标价)")

# 验证
r = c.execute(text("""
    SELECT record_date, COUNT(*) AS total, COUNT(green_price) AS has_green, COUNT(discount_pct) AS has_discount
    FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-20' GROUP BY record_date
""")).fetchone()
print(f"\n=== 验证 8-20: 总={r[1]} 有绿标价={r[2]} 有折扣={r[3]} ===")
if not DRY_RUN:
    print("\n=== 抽样 ===")
    for row in c.execute(text("""
        SELECT s.store_id, s.sku_id, s.green_price, s.discount_pct
        FROM ozon.sku_daily_snapshot s
        WHERE s.record_date='2026-08-20' AND s.green_price IS NOT NULL
        ORDER BY s.sku_id LIMIT 5
    """)):
        print(f"  店{row[0]} sku={row[1]} 绿标={row[2]} 折扣={row[3]}")
c.close()
