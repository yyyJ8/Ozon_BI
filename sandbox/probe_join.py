"""排查 8-21 凌晨调度 JOIN 失败的数据库侧证据"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

print("=== 1. 主表 JOIN 不上 products 的孤儿记录（类型/值不匹配）===")
rows = c.execute(text("""
    SELECT m.store_id, m.sku_id, m.green_price_rub, m.updated_at
    FROM ozon.sku_management m
    LEFT JOIN ozon.products p ON p.store_id = m.store_id AND p.sku_id = m.sku_id
    WHERE p.sku_id IS NULL
""")).fetchall()
print(f"  孤儿记录数: {len(rows)}")
for r in rows[:10]:
    print(f"  store={r[0]} sku={r[1]} 绿标={r[2]} 更新={r[3]}")

print("\n=== 2. 字段类型对比（JOIN 条件列）===")
for r in c.execute(text("""
    SELECT table_name, column_name, data_type, udt_name
    FROM information_schema.columns
    WHERE table_schema='ozon' AND table_name IN ('products','sku_management','sku_daily_snapshot')
      AND column_name IN ('store_id','sku_id')
    ORDER BY table_name, column_name
""")):
    print(f"  {r[0]}.{r[1]}  {r[2]} ({r[3]})")

print("\n=== 3. 8-21 05:00 前后：各表活动（synced_at 分布）===")
for tbl, col in (("products", "synced_at"), ("stocks", "synced_at"), ("postings", "created_at")):
    try:
        rows = c.execute(text(
            f"SELECT {col}::date AS d, COUNT(*) FROM ozon.{tbl} "
            f"WHERE {col} >= '2026-08-20 22:00' AND {col} < '2026-08-21 08:00' "
            f"GROUP BY {col}::date ORDER BY d"
        )).fetchall()
        print(f"  {tbl}: {rows}")
    except Exception as ex:
        print(f"  {tbl}: 查询失败 {ex}")

print("\n=== 4. 8-20 快照各店行数与主表匹配（现在）===")
rows = c.execute(text("""
    SELECT s.store_id, COUNT(*) AS snap_rows,
           COUNT(m.sku_id) AS matched_mgmt,
           COUNT(m.green_price_rub) AS mgmt_has_green
    FROM ozon.sku_daily_snapshot s
    LEFT JOIN ozon.sku_management m ON m.store_id=s.store_id AND m.sku_id=s.sku_id
    WHERE s.record_date='2026-08-20' AND s.green_price IS NULL
    GROUP BY s.store_id ORDER BY s.store_id
""")).fetchall()
for r in rows:
    print(f"  店{r[0]}: 8-20空值行={r[1]}  匹配到主表={r[2]}  主表有绿标价={r[3]}")
c.close()
