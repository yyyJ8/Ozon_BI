"""查询 SKU 41634-Y07U0003-OB01 的绿标价相关信息"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

print("=== 1. products 基本信息 ===")
rows = c.execute(text("""
    SELECT store_id, sku_id, offer_id, name, marketing_seller_price, price, old_price, min_price
    FROM ozon.products
    WHERE offer_id = '41634-Y07U0003-OB01'
""")).fetchall()
for r in rows:
    print(" ", r)
skus = [r[1] for r in rows]

if skus:
    print("\n=== 2. sku_management 绿标价/折扣 ===")
    for r in c.execute(text(
        "SELECT store_id, sku_id, green_price_rub, discount_pct, exchange_rate, updated_at "
        "FROM ozon.sku_management WHERE sku_id IN :skus"
    ).bindparams(skus=tuple(skus))):
        print(" ", r)

    print("\n=== 3. sku_daily_snapshot 最近7天快照（绿标价/折扣/售价）===")
    for r in c.execute(text(
        "SELECT store_id, sku_id, record_date, price, marketing_seller_price, green_price, discount_pct "
        "FROM ozon.sku_daily_snapshot WHERE sku_id IN :skus ORDER BY record_date DESC LIMIT 7"
    ).bindparams(skus=tuple(skus))):
        print(" ", r)

    print("\n=== 4. 各店汇总（sku_daily_summary 是否有该SKU）===")
    try:
        for r in c.execute(text(
            "SELECT store_id, sku_id, record_date, revenue, ordered_units FROM ozon.sku_daily_summary "
            "WHERE sku_id IN :skus ORDER BY record_date DESC LIMIT 5"
        ).bindparams(skus=tuple(skus))):
            print(" ", r)
    except Exception as ex:
        print("  查询失败:", ex)
c.close()
