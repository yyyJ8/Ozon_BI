"""查 8-21 快照行的生成时间 + 调度输出文件线索"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

print("=== 8-21 快照行 synced_at 分布 ===")
for r in c.execute(text("""
    SELECT synced_at::timestamp(0) AS s, COUNT(*) FROM ozon.sku_daily_snapshot
    WHERE record_date='2026-08-21' GROUP BY s ORDER BY s
""")):
    print(f"  {r[0]}: {r[1]} 行")

print("\n=== 8-21 行其他字段（offer_id/价格 是否正常）===")
r = c.execute(text("""
    SELECT COUNT(*) AS total, COUNT(offer_id) AS has_offer, COUNT(marketing_seller_price) AS has_price,
           COUNT(green_price) AS has_green
    FROM ozon.sku_daily_snapshot WHERE record_date='2026-08-21'
""")).fetchone()
print(f"  总={r[0]} 有offer={r[1]} 有售价={r[2]} 有绿标={r[3]}")

print("\n=== 8-20 vs 8-21 行数对比（店铺5）===")
for r in c.execute(text("""
    SELECT record_date, COUNT(*) FROM ozon.sku_daily_snapshot
    WHERE store_id=5 AND record_date IN ('2026-08-20','2026-08-21') GROUP BY record_date ORDER BY record_date
""")):
    print(f"  {r[0]}: {r[1]} 行")

print("\n=== 主表最新 updated_at（确认主表数据未变）===")
r = c.execute(text("SELECT MAX(updated_at) FROM ozon.sku_management")).scalar()
print(f"  主表最晚更新: {r}")
c.close()
