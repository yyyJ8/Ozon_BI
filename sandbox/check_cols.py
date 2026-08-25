"""验证 8-21 行各列完整性"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()
r = c.execute(text("""
    SELECT COUNT(*) AS total, COUNT(offer_id) AS offer, COUNT(price) AS price,
           COUNT(stock_present) AS stock, COUNT(green_price) AS green, COUNT(discount_pct) AS discount
    FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-21'
""")).fetchone()
print(f"8-21行: 总={r[0]} offer={r[1]} price={r[2]} stock={r[3]} green={r[4]} discount={r[5]}")
c.close()
