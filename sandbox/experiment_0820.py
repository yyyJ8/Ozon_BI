"""决定性实验：模拟调度 SQL 能否 JOIN 到主表绿标价 + 8-20 空行其他字段"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

print("=== 1. 模拟调度 SQL（现在执行，JOIN 主表）===")
rows = c.execute(text("""
    SELECT p.store_id, p.sku_id, p.offer_id, p.marketing_seller_price,
           m.green_price_rub, m.discount_pct
    FROM ozon.products p
    LEFT JOIN ozon.sku_management m ON p.store_id = m.store_id AND p.sku_id = m.sku_id
    WHERE p.store_id = 5
    ORDER BY p.sku_id LIMIT 5
""")).fetchall()
for r in rows:
    print(f"  store={r[0]} sku={r[1]} offer={r[2]} 售价={r[3]} 主表绿标={r[4]} 主表折扣={r[5]}")

print("\n=== 2. 8-20 快照 NULL 行的其他字段是否正常 ===")
rows = c.execute(text("""
    SELECT store_id, sku_id, offer_id, marketing_seller_price, stock_present, green_price, discount_pct
    FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-20' AND green_price IS NULL
    ORDER BY store_id, sku_id LIMIT 6
""")).fetchall()
for r in rows:
    print(f"  store={r[0]} sku={r[1]} offer={r[2]} 售价={r[3]} 库存={r[4]} 绿标={r[5]} 折扣={r[6]}")

print("\n=== 3. 8-20 空值行的 offer_id 数量（JOIN products 是否成功）===")
r = c.execute(text("""
    SELECT COUNT(*) AS total, COUNT(offer_id) AS has_offer, COUNT(marketing_seller_price) AS has_price
    FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-20' AND green_price IS NULL
""")).fetchone()
print(f"  总={r[0]} 有offer_id={r[1]} 有售价={r[2]}")

print("\n=== 4. 主表是否存在 store_id=0 或店铺不匹配的情况（调度可能用错 store）===")
for r in c.execute(text("SELECT store_id, COUNT(*) FROM ozon.sku_management GROUP BY store_id ORDER BY store_id")):
    print(f"  store={r[0]}: {r[1]} 条")

print("\n=== 5. 8-19 快照（正常）对照：同样模拟 ===")
rows = c.execute(text("""
    SELECT store_id, sku_id, green_price, discount_pct FROM ozon.sku_daily_snapshot
    WHERE record_date='2026-08-19' ORDER BY sku_id LIMIT 3
""")).fetchall()
for r in rows:
    print(f"  store={r[0]} sku={r[1]} 绿标={r[2]} 折扣={r[3]}")
c.close()
