"""按天统计快照表绿标价/折扣的数据覆盖（全部店铺）"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

print("=== 快照表按天统计（全部店铺）===")
print(f"{'日期':<12}{'总行数':>7}{'有绿标价':>9}{'无绿标价':>9}{'有折扣':>8}{'无折扣':>8}")
for r in c.execute(text("""
    SELECT record_date,
           COUNT(*) AS total,
           COUNT(green_price) AS has_green,
           COUNT(*) - COUNT(green_price) AS null_green,
           COUNT(discount_pct) AS has_discount,
           COUNT(*) - COUNT(discount_pct) AS null_discount
    FROM ozon.sku_daily_snapshot
    GROUP BY record_date ORDER BY record_date
""")):
    print(f"{str(r[0]):<12}{r[1]:>7}{r[2]:>9}{r[3]:>9}{r[4]:>8}{r[5]:>8}")

print("\n=== 主表绿标价维护情况（按店铺）===")
for r in c.execute(text("""
    SELECT store_id, COUNT(*) AS mgmt_rows,
           COUNT(green_price_rub) AS has_green,
           COUNT(*) - COUNT(green_price_rub) AS null_green
    FROM ozon.sku_management
    GROUP BY store_id ORDER BY store_id
""")):
    print(f"  店铺{r[0]}: 记录={r[1]}  有绿标价={r[2]}  无绿标价={r[3]}")
c.close()
