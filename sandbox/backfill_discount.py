"""历史回填：快照折扣按各自当天 1-绿标/售价 重算；主表折扣按当前售价重算"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

DRY_RUN = "--apply" not in sys.argv
e = create_engine(settings.database_url)
c = e.connect()

# ── 统计 ──
snap_rows = c.execute(text("""
    SELECT COUNT(*) FROM ozon.sku_daily_snapshot
    WHERE green_price IS NOT NULL
      AND (discount_pct IS NULL
           OR ABS(discount_pct - (1 - green_price / NULLIF(marketing_seller_price,0)) * 100) > 0.01)
""")).scalar()
mgmt_rows = c.execute(text("""
    SELECT COUNT(*) FROM ozon.sku_management m
    JOIN ozon.products p ON p.store_id = m.store_id AND p.sku_id = m.sku_id
    WHERE m.green_price_rub IS NOT NULL
      AND (m.discount_pct IS NULL
           OR ABS(m.discount_pct - (1 - m.green_price_rub / NULLIF(p.marketing_seller_price,0)) * 100) > 0.01)
""")).scalar()
print(f"快照表需重算行: {snap_rows}")
print(f"主表需重算行: {mgmt_rows}")

if DRY_RUN:
    print("\n[dry-run] 未执行。加 --apply 执行。")
else:
    r1 = c.execute(text("""
        UPDATE ozon.sku_daily_snapshot
        SET discount_pct = CASE
                WHEN green_price IS NOT NULL AND marketing_seller_price IS NOT NULL AND marketing_seller_price > 0
                THEN ROUND((1 - green_price / marketing_seller_price) * 100, 2)
                ELSE NULL END
        WHERE green_price IS NOT NULL
    """))
    r2 = c.execute(text("""
        UPDATE ozon.sku_management m
        SET discount_pct = CASE
                WHEN m.green_price_rub IS NOT NULL AND p.marketing_seller_price IS NOT NULL AND p.marketing_seller_price > 0
                THEN ROUND((1 - m.green_price_rub / p.marketing_seller_price) * 100, 2)
                ELSE NULL END
        FROM ozon.products p
        WHERE p.store_id = m.store_id AND p.sku_id = m.sku_id
          AND m.green_price_rub IS NOT NULL
    """))
    c.commit()
    print(f"\n[已执行] 快照表更新 {r1.rowcount} 行，主表更新 {r2.rowcount} 行")

# ── 验证 ──
print("\n=== 验证：重算后不一致行数 ===")
snap_bad = c.execute(text("""
    SELECT COUNT(*) FROM ozon.sku_daily_snapshot
    WHERE green_price IS NOT NULL
      AND ABS(discount_pct - (1 - green_price / NULLIF(marketing_seller_price,0)) * 100) > 0.01
""")).scalar()
mgmt_bad = c.execute(text("""
    SELECT COUNT(*) FROM ozon.sku_management m
    JOIN ozon.products p ON p.store_id = m.store_id AND p.sku_id = m.sku_id
    WHERE m.green_price_rub IS NOT NULL
      AND ABS(m.discount_pct - (1 - m.green_price_rub / NULLIF(p.marketing_seller_price,0)) * 100) > 0.01
""")).scalar()
print(f"快照表剩余不一致: {snap_bad}")
print(f"主表剩余不一致: {mgmt_bad}")

if not DRY_RUN:
    print("\n=== 抽样（SKU 5376335343 各天）===")
    for r in c.execute(text("""
        SELECT record_date, green_price, marketing_seller_price, discount_pct
        FROM ozon.sku_daily_snapshot
        WHERE sku_id=5376335343 AND store_id=5 AND green_price IS NOT NULL
        ORDER BY record_date DESC LIMIT 5
    """)):
        print(f"  {r[0]} 绿标={r[1]} 售价={r[2]} 折扣={r[3]}%")
c.close()
