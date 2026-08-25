"""检查 8-19 快照行是否被创建（判断线上服务是否已加载新代码）"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()
rows = c.execute(text(
    "SELECT record_date, green_price, discount_pct, price, stock_present FROM ozon.sku_daily_snapshot "
    "WHERE store_id=1 AND sku_id=4734766594 ORDER BY record_date DESC LIMIT 3"
)).fetchall()
for r in rows:
    print(r)
if rows and str(rows[0][0]) == "2026-08-19":
    print("=> 8-19 行存在：线上服务已加载新代码（快照同步已生效）")
    # 清理：删除该测试行（值为 NULL 的空行，非历史数据）
    c.execute(text(
        "DELETE FROM ozon.sku_daily_snapshot WHERE store_id=1 AND sku_id=4734766594 "
        "AND record_date='2026-08-19' AND green_price IS NULL AND discount_pct IS NULL"
    ))
    c.commit()
    print("=> 已清理测试产生的 8-19 空行")
else:
    print("=> 8-19 行不存在：线上服务仍是旧代码，需要重启后端才生效")
c.close()
