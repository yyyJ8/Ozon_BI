"""查询申购单号 PR260411011 在各表中的数据"""
import psycopg2

conn = psycopg2.connect(
    host="pgm-7xvui1j4600t1u27-l2.pg.rds.aliyuncs.com",
    port=5432, user="readuser", password="Yy20251106!rus",
    dbname="omsprod", connect_timeout=10,
)
cur = conn.cursor()

po_plan_no = "PR260411011"

# 1. purchase_plan
print("=" * 80)
print(f"【purchase_plan】申购单 {po_plan_no}")
print("=" * 80)
cur.execute(f"SELECT * FROM public.purchase_plan WHERE po_plan_no = %s", (po_plan_no,))
cols = [desc[0] for desc in cur.description]
rows = cur.fetchall()
if rows:
    for row in rows:
        for i, col in enumerate(cols):
            print(f"  {col}: {row[i]}")
else:
    print("  ❌ 没有找到")
print()

# 2. purchase_plan_item
print("=" * 80)
print(f"【purchase_plan_item】申购明细")
print("=" * 80)
cur.execute(f"SELECT * FROM public.purchase_plan_item WHERE po_plan_no = %s", (po_plan_no,))
cols = [desc[0] for desc in cur.description]
rows = cur.fetchall()
print(f"  共 {len(rows)} 行")
for i, row in enumerate(rows):
    print(f"\n  --- 第 {i+1} 行 ---")
    for j, col in enumerate(cols):
        print(f"  {col}: {row[j]}")
print()

# 3. purchase_order (via purchase_order_item.po_plan_no)
print("=" * 80)
print(f"【purchase_order → purchase_order_item】关联采购单")
print("=" * 80)
cur.execute("""
    SELECT DISTINCT po.*
    FROM public.purchase_order po
    INNER JOIN public.purchase_order_item poi ON poi.po_no = po.po_no
    WHERE poi.po_plan_no = %s
""", (po_plan_no,))
cols = [desc[0] for desc in cur.description]
rows = cur.fetchall()
if rows:
    for i, row in enumerate(rows):
        print(f"\n  --- 采购单 {i+1} ---")
        for j, col in enumerate(cols):
            print(f"  {col}: {row[j]}")
else:
    print("  ❌ 没有关联采购单（可能还没生成采购单或已取消）")
print()

# 4. first_leg_shipping_order (via source_order_code)
print("=" * 80)
print(f"【first_leg_shipping_order_item → shipping_order】关联发货单")
print("=" * 80)
cur.execute("""
    SELECT DISTINCT fso.*
    FROM public.first_leg_shipping_order fso
    INNER JOIN public.first_leg_shipping_order_item fsoi ON fsoi.shipping_order_code = fso.order_code
    WHERE fsoi.source_order_code = %s
""", (po_plan_no,))
rows = cur.fetchall()
if rows:
    cols = [desc[0] for desc in cur.description]
    for i, row in enumerate(rows):
        print(f"\n  --- 发货单 {i+1} ---")
        for j, col in enumerate(cols):
            print(f"  {col}: {row[j]}")
else:
    print("  ❌ 没有关联发货单")
print()

# 5. 平台相关字段汇总
print("=" * 80)
print(f"【平台类型字段汇总】")
print("=" * 80)
print()
print("  purchase_plan_item:")
print("    platform      — 平台 (Amazon/Shopee/Temu/eBay等)")
print("    marketplace   — 站点 (US/UK/DE/ID/AU等)")
print("    store_id      — 店铺ID (关联oms_store)")
print("    seller_sku    — 卖家SKU")
print()
print("  purchase_order_item:")
print("    sale_platform — 销售平台 (Amazon/Ebay)")
print("    marketplace_code — 市场代码 (US/UK/DE等)")
print("    sale_store_id — 销售店铺ID")
print()
print("  first_leg_shipping_order:")
print("    receiving_platform — 接收平台 (如Amazon)")
print("    destination_country_code — 目的国家 (US/DE)")
print("    store_id      — 店铺ID")
print()
print("  first_leg_shipping_order_item:")
print("    fnsku / asin  — Amazon FBA相关")
print("    warehouse_item_code — 海外仓条码")

cur.close()
conn.close()
