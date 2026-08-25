"""对比快照表 8-17/8-18/8-19 的绿标价空值情况"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()
for d in ("2026-08-17", "2026-08-18", "2026-08-19"):
    total = c.execute(text(
        "SELECT COUNT(*) FROM ozon.sku_daily_snapshot WHERE record_date=:d"
    ), {"d": d}).scalar()
    null_gp = c.execute(text(
        "SELECT COUNT(*) FROM ozon.sku_daily_snapshot WHERE record_date=:d AND green_price IS NULL"
    ), {"d": d}).scalar()
    print(f"{d}: 总记录={total}, 绿标价NULL={null_gp}")
# 该SKU 8-18 行是否唯一异常
print("\n8-18 该SKU行:")
for r in c.execute(text(
    "SELECT store_id, sku_id, offer_id, green_price, discount_pct, marketing_seller_price "
    "FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-18' AND sku_id=5376335343"
)):
    print(" ", r)
c.close()
