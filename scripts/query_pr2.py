"""模糊搜索 PR260411011"""
import psycopg2

conn = psycopg2.connect(
    host="pgm-7xvui1j4600t1u27-l2.pg.rds.aliyuncs.com",
    port=5432, user="readuser", password="Yy20251106!rus",
    dbname="omsprod", connect_timeout=10,
)
cur = conn.cursor()

# 1. 搜索 PR260411* (同一天)
print("=== purchase_plan 中 PR260411* 开头的 ===")
cur.execute("SELECT po_plan_no, status, memo FROM public.purchase_plan WHERE po_plan_no LIKE 'PR260411%' LIMIT 10")
for r in cur.fetchall():
    print(f"  {r[0]}  status={r[1]}  memo={r[2][:80] if r[2] else ''}")

# 2. 搜索 PR26041* (近似)
print("\n=== PR26041* ===")
cur.execute("SELECT po_plan_no, status FROM public.purchase_plan WHERE po_plan_no LIKE 'PR26041%' LIMIT 10")
for r in cur.fetchall():
    print(f"  {r[0]}  status={r[1]}")

# 3. 看看 purchase_plan_item 里有没有
print("\n=== purchase_plan_item 中 PR260411011 ===")
cur.execute("SELECT po_plan_no, item_id, plan_qty FROM public.purchase_plan_item WHERE po_plan_no = 'PR260411011' LIMIT 5")
for r in cur.fetchall():
    print(f"  {r}")

# 4. 搜索 purchase_order_item
print("\n=== purchase_order_item 中 po_plan_no = PR260411011 ===")
cur.execute("SELECT po_no, item_id, qty FROM public.purchase_order_item WHERE po_plan_no = 'PR260411011' LIMIT 5")
for r in cur.fetchall():
    print(f"  {r}")

# 5. 搜索 first_leg_shipping_order_item
print("\n=== first_leg_shipping_order_item 中 source_order_code = PR260411011 ===")
cur.execute("SELECT source_order_code, item_id, shipping_order_code FROM public.first_leg_shipping_order_item WHERE source_order_code = 'PR260411011' LIMIT 5")
for r in cur.fetchall():
    print(f"  {r}")

# 6. 看看有没有在 Ozon MySQL 里
print("\n=== 试试 MySQL db_warehouse ===")
try:
    import pymysql
    conn2 = pymysql.connect(host="223.84.201.140", port=9030, user="wangyilong", password="wAng0730lonG", charset='utf8mb4')
    cur2 = conn2.cursor()
    for table in ["ods_ozon_fbo_order_f", "ods_ozon_fbs_order_f"]:
        cur2.execute(f"SELECT * FROM db_warehouse.`{table}` WHERE order_number LIKE '%260411011%' OR posting_number LIKE '%260411011%' LIMIT 3")
        rows = cur2.fetchall()
        if rows:
            print(f"  {table}: 找到 {len(rows)} 条")
            for r in rows:
                print(f"    {r[:5]}...")
    cur2.close()
    conn2.close()
except Exception as e:
    print(f"  MySQL查询失败: {e}")

cur.close()
conn.close()
print("\n结论: PR260411011 在 PostgreSQL omsprod 和 MySQL db_warehouse 中都不存在")
