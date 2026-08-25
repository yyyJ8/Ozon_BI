# -*- coding: utf-8 -*-
"""检查各店铺补货配置 / 商品 / 可匹配行数"""
import sys
sys.path.insert(0, r"D:\OzonSku")

from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    def q(sql, **p):
        return conn.execute(text(sql), p).fetchall()

    print("=== 1. 所有店铺 (stores) ===")
    for r in q("SELECT id, name, is_active FROM ozon.stores ORDER BY id"):
        print("   ", r)

    print()
    print("=== 2. replenishment_config 按店铺统计 ===")
    for r in q("SELECT store_id, COUNT(*) FROM ozon.replenishment_config GROUP BY store_id ORDER BY store_id"):
        print("   ", r)

    print()
    print("=== 3. products 按店铺统计 ===")
    for r in q("SELECT store_id, COUNT(*) FROM ozon.products GROUP BY store_id ORDER BY store_id"):
        print("   ", r)

    print()
    print("=== 4. replenishment_config 匹配到 products 的行数 (on store_id+offer_id) ===")
    rows = q("""
        SELECT cfg.store_id, COUNT(*)
        FROM ozon.replenishment_config cfg
        JOIN ozon.products p
          ON p.store_id = cfg.store_id AND p.offer_id = cfg.offer_id
        GROUP BY cfg.store_id
        ORDER BY cfg.store_id
    """)
    for r in rows:
        print("   ", r)

    print()
    print("=== 5. 未匹配到 product 的 config 行数 (store3/4/5重点) ===")
    rows = q("""
        SELECT cfg.store_id, COUNT(*) AS unmatched
        FROM ozon.replenishment_config cfg
        LEFT JOIN ozon.products p
          ON p.store_id = cfg.store_id AND p.offer_id = cfg.offer_id
        WHERE p.sku_id IS NULL
        GROUP BY cfg.store_id
        ORDER BY cfg.store_id
    """)
    for r in rows:
        print("   ", r)

    print()
    print("=== 6. stores 3/4/5 的 config 样本 (最多10行) ===")
    for r in q("""
        SELECT store_id, offer_id, product_name, safety_days, logistics_days
        FROM ozon.replenishment_config
        WHERE store_id IN (3,4,5)
        ORDER BY store_id, offer_id
        LIMIT 30
    """):
        print("   ", r)
