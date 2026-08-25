"""排查 SKU 5376335343 绿标价回退原因"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

print("=== 1. 该 SKU 在哪些店铺存在（products）===")
for r in c.execute(text(
    "SELECT store_id, sku_id, offer_id FROM ozon.products WHERE sku_id=5376335343"
)):
    print(" ", r)

print("\n=== 2. sku_management 该 SKU 全部店铺记录 ===")
for r in c.execute(text(
    "SELECT store_id, sku_id, green_price_rub, discount_pct, updated_at "
    "FROM ozon.sku_management WHERE sku_id=5376335343 ORDER BY store_id"
)):
    print(" ", r)

print("\n=== 3. 快照表最近5天 ===")
for r in c.execute(text(
    "SELECT store_id, record_date, green_price, discount_pct, marketing_seller_price, synced_at "
    "FROM ozon.sku_daily_snapshot WHERE sku_id=5376335343 ORDER BY record_date DESC LIMIT 5"
)):
    print(" ", r)

print("\n=== 4. 各店铺快照最新日期（判断调度是否正常）===")
for r in c.execute(text(
    "SELECT store_id, MAX(record_date) AS latest FROM ozon.sku_daily_snapshot GROUP BY store_id ORDER BY store_id"
)):
    print(" ", r)

print("\n=== 5. 店铺列表 ===")
for r in c.execute(text("SELECT id, name, is_active FROM ozon.stores ORDER BY id")):
    print(" ", r)
c.close()
