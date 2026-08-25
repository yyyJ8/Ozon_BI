"""模拟新调度 SQL：折扣按 1-绿标/售价 实时计算（测试日期，回滚）"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

TEST_DATE = "2099-01-02"
e = create_engine(settings.database_url)
c = e.connect()
trans = c.begin()
try:
    c.execute(text("""
        INSERT INTO ozon.sku_daily_snapshot
            (store_id, sku_id, record_date, offer_id,
             price, old_price, marketing_seller_price, min_price,
             green_price, discount_pct,
             stock_present, stock_reserved, synced_at)
        SELECT
            p.store_id, p.sku_id, :today, p.offer_id,
            p.price, p.old_price, p.marketing_seller_price, p.min_price,
            m.green_price_rub,
            CASE
                WHEN m.green_price_rub IS NOT NULL
                     AND p.marketing_seller_price IS NOT NULL
                     AND p.marketing_seller_price > 0
                THEN ROUND((1 - m.green_price_rub / p.marketing_seller_price) * 100, 2)
                ELSE NULL
            END,
            COALESCE(s.present, 0), COALESCE(s.reserved, 0), now()
        FROM ozon.products p
        LEFT JOIN (
            SELECT store_id, sku_id, SUM(present) AS present, SUM(reserved) AS reserved
            FROM ozon.stocks GROUP BY store_id, sku_id
        ) s ON p.store_id = s.store_id AND p.sku_id = s.sku_id
        LEFT JOIN ozon.sku_management m ON p.store_id = m.store_id AND p.sku_id = m.sku_id
        WHERE p.store_id = :sid
        ON CONFLICT (store_id, sku_id, record_date) DO NOTHING
    """), {"today": TEST_DATE, "sid": 5})

    print("=== 模拟结果（店铺5）===")
    for r in c.execute(text("""
        SELECT s.sku_id, s.green_price, s.marketing_seller_price, s.discount_pct,
               ROUND((1 - s.green_price / NULLIF(s.marketing_seller_price,0)) * 100, 2) AS calc
        FROM ozon.sku_daily_snapshot s WHERE s.record_date=:d AND s.green_price IS NOT NULL
        ORDER BY s.sku_id
    """), {"d": TEST_DATE}):
        ok = "✓" if r[3] == r[4] else "✗"
        print(f"  sku={r[0]} 绿标={r[1]} 售价={r[2]} 快照折扣={r[3]} 手算={r[4]} {ok}")
    bad = c.execute(text("""
        SELECT COUNT(*) FROM ozon.sku_daily_snapshot WHERE record_date=:d AND green_price IS NOT NULL
        AND ABS(discount_pct - (1 - green_price / NULLIF(marketing_seller_price,0)) * 100) > 0.01
    """), {"d": TEST_DATE}).scalar()
    print(f"\n不一致行数: {bad}")
finally:
    trans.rollback()
    c.close()
    print("（测试日期已回滚）")
