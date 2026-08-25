"""确认测试数据未残留"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()
rows = c.execute(text(
    "SELECT record_date, green_price, discount_pct FROM ozon.sku_daily_snapshot "
    "WHERE store_id=1 AND sku_id=4734766594 ORDER BY record_date DESC LIMIT 3"
)).fetchall()
print("快照最新3条:", rows)
mg = c.execute(text(
    "SELECT green_price_rub, discount_pct FROM ozon.sku_management "
    "WHERE store_id=1 AND sku_id=4734766594"
)).fetchall()
print("sku_management:", mg)
# 断言：不存在 1234.56 的残留
assert all(r[1] != 1234.56 for r in rows), "存在测试残留数据!"
assert all(r[0] != 1234.56 for r in mg), "存在测试残留数据!"
print("✅ 无测试数据残留")
c.close()
