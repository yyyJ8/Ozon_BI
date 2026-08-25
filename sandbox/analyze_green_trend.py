"""分析快照表绿标价的数据现状（支撑趋势展示问题结论）"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

SKU = 5376335343

print("=== 1. 该 SKU 快照表最近 14 天（绿标价/折扣/售价）===")
for r in c.execute(text(
    "SELECT record_date, marketing_seller_price, green_price, discount_pct "
    "FROM ozon.sku_daily_snapshot WHERE sku_id=:s ORDER BY record_date DESC LIMIT 14"
), {"s": SKU}):
    print(f"  {r[0]}  售价={r[1]}  绿标价={r[2]}  折扣={r[3]}")

print("\n=== 2. 全店(5)快照表绿标价缺失统计（近7天）===")
for r in c.execute(text(
    "SELECT record_date, COUNT(*) AS total, "
    "COUNT(green_price) AS has_green, COUNT(*) - COUNT(green_price) AS null_green "
    "FROM ozon.sku_daily_snapshot WHERE store_id=5 AND record_date >= '2026-08-14' "
    "GROUP BY record_date ORDER BY record_date"
)):
    print(f"  {r[0]}  总={r[1]}  有绿标价={r[2]}  缺失={r[3]}")

print("\n=== 3. 该 SKU 主表 vs 快照表 最新值对比 ===")
m = c.execute(text(
    "SELECT green_price_rub, discount_pct, updated_at FROM ozon.sku_management "
    "WHERE store_id=5 AND sku_id=:s"
), {"s": SKU}).fetchone()
print(f"  sku_management: 绿标价={m[0]}  折扣={m[1]}  更新={m[2]}")
snap_latest = c.execute(text(
    "SELECT record_date, green_price FROM ozon.sku_daily_snapshot "
    "WHERE store_id=5 AND sku_id=:s ORDER BY record_date DESC LIMIT 1"
), {"s": SKU}).fetchone()
print(f"  快照最新: {snap_latest}")

print("\n=== 4. 有多少 SKU 主表有绿标价但快照最新记录没有 ===")
for r in c.execute(text(
    "SELECT COUNT(*) FROM ozon.sku_management m "
    "WHERE m.store_id=5 AND m.green_price_rub IS NOT NULL AND m.is_archived IS NOT TRUE "
    "AND NOT EXISTS (SELECT 1 FROM ozon.sku_daily_snapshot s "
    "  WHERE s.store_id=m.store_id AND s.sku_id=m.sku_id "
    "  AND s.record_date=(SELECT MAX(record_date) FROM ozon.sku_daily_snapshot s2 "
    "    WHERE s2.store_id=m.store_id AND s2.sku_id=m.sku_id) AND s.green_price IS NOT NULL)"
)):
    print(f"  主表有绿标价但最新快照无绿标价的 SKU 数: {r[0]}")
c.close()
