import psycopg2
conn = psycopg2.connect(host="pgm-7xvui1j4600t1u27-l2.pg.rds.aliyuncs.com", port=5432, user="readuser", password="Yy20251106!rus", dbname="omsprod", connect_timeout=10)
cur = conn.cursor()

# 1. purchase_plan_item 里 platform='Ozon' 有多少
cur.execute("SELECT COUNT(*), COUNT(DISTINCT po_plan_no) FROM public.purchase_plan_item WHERE platform = 'Ozon'")
cnt, plans = cur.fetchone()
print(f"purchase_plan_item 中 platform=Ozon: {cnt} 条明细, {plans} 个申购单")

# 2. purchase_order_item 里 sale_platform='Ozon' 有多少
cur.execute("SELECT COUNT(*), COUNT(DISTINCT po_no) FROM public.purchase_order_item WHERE sale_platform = 'Ozon'")
cnt, pos = cur.fetchone()
print(f"purchase_order_item 中 sale_platform=Ozon: {cnt} 条明细, {pos} 个采购单")

# 3. md里purchase_plan那两条是不是真Ozon
for pn in ["PR2512080238", "PR2512080239"]:
    cur.execute("SELECT platform FROM public.purchase_plan_item WHERE po_plan_no = %s LIMIT 3", (pn,))
    platforms = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT status, po_plan_no FROM public.purchase_plan WHERE po_plan_no = %s", (pn,))
    plan = cur.fetchone()
    print(f"  {pn}: ppi.platform={platforms}, plan.status={plan[0] if plan else 'NOT FOUND'}")

# 4. 取两个正常状态的Ozon申购单看看
print("\n=== 状态正常的 Ozon 申购单（前10个） ===")
cur.execute("""
    SELECT DISTINCT pp.po_plan_no, pp.status, pp.memo
    FROM public.purchase_plan pp
    INNER JOIN public.purchase_plan_item ppi ON ppi.po_plan_no = pp.po_plan_no
    WHERE ppi.platform = 'Ozon' AND pp.status = '4'
    LIMIT 10
""")
for r in cur.fetchall():
    print(f"  {r[0]}  status={r[1]}  memo={str(r[2])[:60] if r[2] else ''}")

# 5. 确认purchase_plan表中近期的Ozon申购单
print("\n=== 2026年的Ozon申购单 examples ===")
cur.execute("""
    SELECT DISTINCT pp.po_plan_no, pp.status, pp.create_time
    FROM public.purchase_plan pp
    INNER JOIN public.purchase_plan_item ppi ON ppi.po_plan_no = pp.po_plan_no
    WHERE ppi.platform = 'Ozon' AND pp.create_time >= '2026-01-01'
    ORDER BY pp.create_time DESC
    LIMIT 10
""")
for r in cur.fetchall():
    print(f"  {r[0]}  status={r[1]}  {r[2]}")

cur.close()
conn.close()
