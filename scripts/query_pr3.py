import psycopg2
conn = psycopg2.connect(host="pgm-7xvui1j4600t1u27-l2.pg.rds.aliyuncs.com", port=5432, user="readuser", password="Yy20251106!rus", dbname="omsprod", connect_timeout=10)
cur = conn.cursor()
po = "PR2604110119"

def print_table(title, rows, cols):
    print(f"\n{'='*80}")
    print(f"【{title}】共 {len(rows)} 条")
    print("="*80)
    if not rows:
        print("  (无数据)")
        return
    for ri, row in enumerate(rows):
        print(f"\n  --- 第 {ri+1} 条 ---")
        for i, c in enumerate(cols):
            print(f"  {c}: {row[i]}")

# 1. purchase_plan
cur.execute("SELECT * FROM public.purchase_plan WHERE po_plan_no = %s", (po,))
cols = [d[0] for d in cur.description]
rows = cur.fetchall()
print_table("purchase_plan", rows, cols)

# 2. purchase_plan_item
cur.execute("SELECT * FROM public.purchase_plan_item WHERE po_plan_no = %s", (po,))
cols = [d[0] for d in cur.description]
rows = cur.fetchall()
print_table("purchase_plan_item", rows, cols)

# 3. purchase_order + purchase_order_item
cur.execute("SELECT poi.* FROM public.purchase_order_item poi WHERE poi.po_plan_no = %s", (po,))
cols = [d[0] for d in cur.description]
rows = cur.fetchall()
print_table("purchase_order_item", rows, cols)

# 4. first_leg_shipping_order_item
cur.execute("SELECT * FROM public.first_leg_shipping_order_item WHERE source_order_code = %s", (po,))
cols = [d[0] for d in cur.description]
rows = cur.fetchall()
print_table("first_leg_shipping_order_item", rows, cols)

cur.close()
conn.close()
