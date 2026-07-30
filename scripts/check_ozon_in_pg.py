"""检查 PostgreSQL omsprod 中是否有 Ozon 数据"""
import psycopg2

conn = psycopg2.connect(
    host="pgm-7xvui1j4600t1u27-l2.pg.rds.aliyuncs.com",
    port=5432, user="readuser", password="Yy20251106!rus",
    dbname="omsprod", connect_timeout=10,
)
cur = conn.cursor()

# 表名含ozon
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name ILIKE '%ozon%'")
tables = [t[0] for t in cur.fetchall()]
print(f"表名含ozon: {tables if tables else '无'}")

# oms_store中Ozon店铺
cur.execute("SELECT id, name, platform FROM oms_store WHERE platform ILIKE '%ozon%' OR name ILIKE '%ozon%'")
stores = cur.fetchall()
print(f"oms_store中Ozon店铺: {stores if stores else '无'}")

# oms_seller_sku_eccang中ozon
cur.execute("SELECT COUNT(*) FROM oms_seller_sku_eccang WHERE store_code ILIKE '%ozon%'")
print(f"oms_seller_sku_eccang中ozon: {cur.fetchone()[0]} 条")

# oms_inventory中ozon marketplace
cur.execute("SELECT COUNT(*) FROM oms_inventory WHERE marketplace ILIKE '%ozon%'")
print(f"oms_inventory中ozon: {cur.fetchone()[0]} 条")

# purchase_plan_item中ozon platform
cur.execute("SELECT COUNT(*) FROM purchase_plan_item WHERE platform ILIKE '%ozon%'")
print(f"purchase_plan_item中ozon: {cur.fetchone()[0]} 条")

cur.close()
conn.close()

print("\n结论: PostgreSQL omsprod 中", "有" if tables or stores else "没有", "Ozon 专用表/店铺")
