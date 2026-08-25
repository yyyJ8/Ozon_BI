"""全面检查绿标价问题：快照覆盖、主表一致性、数值合理性"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()

print("=== 1. 快照表各天绿标价覆盖（全部店铺）===")
print(f"{'日期':<12}{'总行':>6}{'有绿标':>7}{'缺失':>6}")
for r in c.execute(text("""
    SELECT record_date, COUNT(*), COUNT(green_price), COUNT(*)-COUNT(green_price)
    FROM ozon.sku_daily_snapshot GROUP BY record_date ORDER BY record_date
""")):
    print(f"{str(r[0]):<12}{r[1]:>6}{r[2]:>7}{r[3]:>6}")

print("\n=== 2. 主表有绿标价但最新快照没有（不一致 SKU）===")
for r in c.execute(text("""
    SELECT m.store_id, m.sku_id, m.green_price_rub, m.discount_pct, m.updated_at
    FROM ozon.sku_management m
    WHERE m.green_price_rub IS NOT NULL AND m.is_archived IS NOT TRUE
      AND NOT EXISTS (
        SELECT 1 FROM ozon.sku_daily_snapshot s
        WHERE s.store_id = m.store_id AND s.sku_id = m.sku_id
          AND s.record_date = (SELECT MAX(record_date) FROM ozon.sku_daily_snapshot
                               WHERE store_id = m.store_id AND sku_id = m.sku_id)
          AND s.green_price IS NOT NULL
      )
    ORDER BY m.store_id, m.sku_id
""")):
    print(f"  店{r[0]} sku={r[1]} 绿标={r[2]} 折扣={r[3]} 更新={r[4]}")

print("\n=== 3. 绿标价数值合理性（0/负数/超过售价）===")
for r in c.execute(text("""
    SELECT m.store_id, m.sku_id, m.green_price_rub, p.marketing_seller_price AS price
    FROM ozon.sku_management m
    JOIN ozon.products p ON p.store_id = m.store_id AND p.sku_id = m.sku_id
    WHERE m.green_price_rub IS NOT NULL
      AND (m.green_price_rub <= 0 OR p.marketing_seller_price IS NOT NULL AND m.green_price_rub > p.marketing_seller_price * 1.5)
    ORDER BY m.store_id, m.sku_id
""")):
    print(f"  店{r[0]} sku={r[1]} 绿标={r[2]} 售价={r[3]}")

print("\n=== 4. 主表绿标价为 NULL 的 SKU（永远缺绿标价）===")
for r in c.execute(text("""
    SELECT store_id, COUNT(*) FROM ozon.sku_management
    WHERE green_price_rub IS NULL AND is_archived IS NOT TRUE
    GROUP BY store_id ORDER BY store_id
""")):
    print(f"  店{r[0]}: {r[1]} 个")

print("\n=== 5. 折扣与绿标价/售价自洽性（折扣 ≠ (1-绿标/售价) 的偏差>1%）===")
for r in c.execute(text("""
    SELECT m.store_id, m.sku_id, m.green_price_rub, p.marketing_seller_price AS price,
           m.discount_pct,
           ROUND((1 - m.green_price_rub / NULLIF(p.marketing_seller_price,0)) * 100, 2) AS calc_discount,
           ROUND(m.discount_pct - (1 - m.green_price_rub / NULLIF(p.marketing_seller_price,0)) * 100, 2) AS diff
    FROM ozon.sku_management m
    JOIN ozon.products p ON p.store_id = m.store_id AND p.sku_id = m.sku_id
    WHERE m.green_price_rub IS NOT NULL AND m.discount_pct IS NOT NULL
      AND p.marketing_seller_price IS NOT NULL AND p.marketing_seller_price > 0
      AND ABS(m.discount_pct - (1 - m.green_price_rub / p.marketing_seller_price) * 100) > 1
    ORDER BY ABS(m.discount_pct - (1 - m.green_price_rub / p.marketing_seller_price) * 100) DESC
    LIMIT 15
""")):
    print(f"  店{r[0]} sku={r[1]} 绿标={r[2]} 售价={r[3]} 存折扣={r[4]}% 应算折扣={r[5]}% 偏差={r[6]}%")

print("\n=== 6. 最新归档日（确认 8-21 归档是否已生成/正常）===")
for r in c.execute(text("""
    SELECT store_id, MAX(record_date) AS latest,
           COUNT(*) FILTER (WHERE green_price IS NOT NULL) AS has_green
    FROM ozon.sku_daily_snapshot
    WHERE record_date = (SELECT MAX(record_date) FROM ozon.sku_daily_snapshot)
    GROUP BY store_id ORDER BY store_id
""")):
    print(f"  店{r[0]}: 最新归档={r[1]}  该日有绿标价={r[2]}")
c.close()
