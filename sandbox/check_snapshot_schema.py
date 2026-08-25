"""只读检查：sku_daily_snapshot 表结构 + sku_management 表结构"""
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()
print("=== ozon.sku_daily_snapshot ===")
for r in c.execute(text(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_schema='ozon' AND table_name='sku_daily_snapshot' ORDER BY ordinal_position"
)):
    print(f"  {r[0]:<24} {r[1]}")
print("=== ozon.sku_management (财务相关) ===")
for r in c.execute(text(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_schema='ozon' AND table_name='sku_management' "
    "AND column_name IN ('green_price_rub','discount_pct','exchange_rate','store_id','sku_id') ORDER BY ordinal_position"
)):
    print(f"  {r[0]:<24} {r[1]}")
print("=== sku_daily_snapshot 最新记录 ===")
for r in c.execute(text(
    "SELECT store_id, sku_id, record_date, green_price, discount_pct, marketing_seller_price, stock_present "
    "FROM ozon.sku_daily_snapshot ORDER BY record_date DESC LIMIT 5"
)):
    print("  ", r)
c.close()
