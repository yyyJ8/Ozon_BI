"""最后检查：主表是否被重建/清空过 + 8-22 05:00 调度前后数据库会话"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

print("=== 1. 主表 created_at 分布（若被重建会显示新日期）===")
for r in c.execute(text("""
    SELECT created_at::date AS d, COUNT(*) FROM ozon.sku_management
    GROUP BY d ORDER BY d
""")):
    print(f"  {r[0]}: {r[1]} 条")

print("\n=== 2. 主表当前行数 + 绿标价覆盖 ===")
r = c.execute(text("""
    SELECT COUNT(*), COUNT(green_price_rub), COUNT(discount_pct)
    FROM ozon.sku_management
""")).fetchone()
print(f"  总={r[0]} 有绿标={r[1]} 有折扣={r[2]}")

print("\n=== 3. 8-22 05:00 前后是否有其他调度痕迹（8-21/8-22 编辑同步的行）===")
for r in c.execute(text("""
    SELECT store_id, record_date, synced_at::timestamp(0) AS s, COUNT(*) AS cnt,
           COUNT(green_price) AS has_green
    FROM ozon.sku_daily_snapshot
    WHERE record_date='2026-08-21'
    GROUP BY store_id, record_date, s ORDER BY s, store_id
""")):
    print(f"  店{r[0]} {r[1]} synced={r[2]} 行={r[3]} 有绿标={r[4]}")

print("\n=== 4. 当前数据库连接数（判断运行进程连接池）===")
for r in c.execute(text("""
    SELECT usename, application_name, client_addr, COUNT(*) AS cnt
    FROM pg_stat_activity WHERE datname=current_database() GROUP BY usename, application_name, client_addr
""")):
    print(f"  {r[0]} app={r[1]} addr={r[2]} 连接数={r[3]}")
c.close()
