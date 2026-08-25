"""终极实验：完整复刻调度 INSERT...SELECT（测试日期，回滚），验证 JOIN 现状"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

TEST_DATE = "2099-01-01"  # 绝不会冲突的测试日期
e = create_engine(settings.database_url)
c = e.connect()
trans = c.begin()
try:
    # 完全复刻 scheduler.daily_snapshot 的 SQL
    c.execute(text("""
        INSERT INTO ozon.sku_daily_snapshot
            (store_id, sku_id, record_date, offer_id,
             price, old_price, marketing_seller_price, min_price,
             green_price, discount_pct,
             stock_present, stock_reserved, synced_at)
        SELECT
            p.store_id, p.sku_id, :today, p.offer_id,
            p.price, p.old_price, p.marketing_seller_price, p.min_price,
            m.green_price_rub, m.discount_pct,
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
    print("INSERT...SELECT 执行成功（店铺5）")

    rows = c.execute(text("""
        SELECT store_id, COUNT(*) AS total, COUNT(green_price) AS has_green,
               COUNT(discount_pct) AS has_discount
        FROM ozon.sku_daily_snapshot WHERE record_date=:d GROUP BY store_id
    """), {"d": TEST_DATE}).fetchall()
    for r in rows:
        print(f"  店{r[0]}: 总={r[1]}  有绿标价={r[2]}  有折扣={r[3]}")
    print("\n结论：当前代码 JOIN 主表 →", "✅ 正常拿到绿标价" if rows[0][2] == 15 else "❌ 仍拿不到")
finally:
    trans.rollback()
    c.close()
    print("（测试日期已回滚，未留数据）")
