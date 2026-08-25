"""回填 8-22 / 8-23 快照绿标价（主表当前值，折扣按快照行当天售价计算）"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

DRY_RUN = "--apply" not in sys.argv
DATES = ("2026-08-22", "2026-08-23")
e = create_engine(settings.database_url)
c = e.connect()

for d in DATES:
    total = c.execute(text("SELECT COUNT(*) FROM ozon.sku_daily_snapshot WHERE record_date=:d"), {"d": d}).scalar()
    fillable = c.execute(text("""
        SELECT COUNT(*) FROM ozon.sku_daily_snapshot s
        JOIN ozon.sku_management m ON m.store_id=s.store_id AND m.sku_id=s.sku_id
        WHERE s.record_date=:d AND s.green_price IS NULL AND m.green_price_rub IS NOT NULL
    """), {"d": d}).scalar()
    print(f"{d}: 总={total}  可回填={fillable}")

if DRY_RUN:
    print("\n[dry-run] 未执行。加 --apply 执行。")
else:
    for d in DATES:
        r = c.execute(text("""
            UPDATE ozon.sku_daily_snapshot s
            SET green_price = m.green_price_rub,
                discount_pct = CASE
                    WHEN m.green_price_rub IS NOT NULL
                         AND s.marketing_seller_price IS NOT NULL
                         AND s.marketing_seller_price > 0
                    THEN ROUND((1 - m.green_price_rub / s.marketing_seller_price) * 100, 2)
                    ELSE NULL END
            FROM ozon.sku_management m
            WHERE m.store_id = s.store_id AND m.sku_id = s.sku_id
              AND s.record_date = :d
              AND s.green_price IS NULL
              AND m.green_price_rub IS NOT NULL
        """), {"d": d})
        print(f"[已执行] {d} 回填 {r.rowcount} 行")
    c.commit()

print("\n=== 验证 ===")
for r in c.execute(text("""
    SELECT record_date, COUNT(*) AS total, COUNT(green_price) AS has_green, COUNT(discount_pct) AS has_discount
    FROM ozon.sku_daily_snapshot WHERE record_date IN ('2026-08-22','2026-08-23')
    GROUP BY record_date ORDER BY record_date
""")):
    print(f"  {r[0]}: 总={r[1]}  有绿标={r[2]}  有折扣={r[3]}")

if not DRY_RUN:
    print("\n=== 8-23 抽样 ===")
    for r in c.execute(text("""
        SELECT store_id, sku_id, green_price, marketing_seller_price, discount_pct
        FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-23' AND green_price IS NOT NULL
        ORDER BY sku_id LIMIT 5
    """)):
        print(f"  店{r[0]} sku={r[1]} 绿标={r[2]} 售价={r[3]} 折扣={r[4]}%")
c.close()
