"""提取 Ozon 平台的记录，重新生成有 Ozon 实际数据的 txt"""
import psycopg2
import pymysql
import json
import os
from datetime import datetime

OUTPUT_DIR = "scripts/output"
TXT_OUTPUT = f"{OUTPUT_DIR}/ozon_actual_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

PG_TABLES = [
    "purchase_plan", "purchase_plan_item",
    "purchase_order", "purchase_order_item",
    "first_leg_shipping_order", "first_leg_shipping_order_item",
]

MYSQL_TABLES = [
    "ods_ozon_product_f", "ods_ozon_product_stock_d",
    "ods_ozon_fbo_order_f", "ods_ozon_fbo_order_product_f",
    "ods_ozon_fbs_order_f", "ods_ozon_fbs_order_product_f",
]

lines = []

def log(msg=""):
    print(msg)
    lines.append(msg)

def fmt_val(v):
    if v is None: return "NULL"
    if isinstance(v, bytes):
        try: return v.decode('utf-8')
        except: return str(v)
    if isinstance(v, datetime): return v.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(v, (dict, list)):
        s = json.dumps(v, ensure_ascii=False)
        return s[:200] + "..." if len(s) > 200 else s
    s = str(v)
    return s[:200] + "..." if len(s) > 200 else s


def process_pg():
    log("=" * 100)
    log("PostgreSQL omsprod — 申购/采购/发货 6表 (Ozon平台)")
    log("=" * 100)

    conn = psycopg2.connect(
        host="pgm-7xvui1j4600t1u27-l2.pg.rds.aliyuncs.com",
        port=5432, user="readuser", password="Yy20251106!rus",
        dbname="omsprod", connect_timeout=10,
    )
    cur = conn.cursor()

    for table in PG_TABLES:
        log(f"\n{'─'*90}")
        log(f"【{table}】")
        log(f"{'─'*90}")

        # 不同表用不同条件取 Ozon 数据
        if table == "purchase_plan_item":
            cur.execute('SELECT * FROM public.purchase_plan_item WHERE platform = %s LIMIT 2', ("Ozon",))
        elif table == "purchase_order_item":
            cur.execute('SELECT * FROM public.purchase_order_item WHERE sale_platform = %s ORDER BY create_time DESC LIMIT 2', ("Ozon",))
        elif table == "purchase_order":
            cur.execute("""
                SELECT DISTINCT po.* FROM public.purchase_order po
                INNER JOIN public.purchase_order_item poi ON poi.po_no = po.po_no
                WHERE poi.sale_platform = 'Ozon'
                ORDER BY po.create_time DESC LIMIT 2
            """)
        elif table == "purchase_plan":
            # 通过 purchase_plan_item 关联，只要 status=4（已完成）的
            cur.execute("""
                SELECT DISTINCT pp.* FROM public.purchase_plan pp
                INNER JOIN public.purchase_plan_item ppi ON ppi.po_plan_no = pp.po_plan_no
                WHERE ppi.platform = 'Ozon' AND pp.status = '4'
                ORDER BY pp.create_time DESC LIMIT 2
            """)
        elif table == "first_leg_shipping_order":
            # 通过 first_leg_shipping_order_item.source_order_code
            cur.execute("""
                SELECT DISTINCT fso.* FROM public.first_leg_shipping_order fso
                INNER JOIN public.first_leg_shipping_order_item fsoi ON fsoi.shipping_order_code = fso.order_code
                INNER JOIN public.purchase_plan_item ppi ON ppi.po_plan_no = fsoi.source_order_code
                WHERE ppi.platform = 'Ozon'
                ORDER BY fso.create_time DESC LIMIT 2
            """)
        elif table == "first_leg_shipping_order_item":
            cur.execute("""
                SELECT fsoi.* FROM public.first_leg_shipping_order_item fsoi
                INNER JOIN public.purchase_plan_item ppi ON ppi.po_plan_no = fsoi.source_order_code
                WHERE ppi.platform = 'Ozon'
                ORDER BY fsoi.create_time DESC LIMIT 2
            """)

        col_names = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        # 取列注释
        col_comment_sql = f"""
            SELECT a.attname, pg_catalog.col_description(a.attrelid, a.attnum)
            FROM pg_catalog.pg_attribute a
            WHERE a.attrelid = '{table}'::regclass AND a.attnum > 0 AND NOT a.attisdropped
            ORDER BY a.attnum
        """
        try:
            cur.execute(col_comment_sql)
            comments = {r[0]: r[1] for r in cur.fetchall()}
        except:
            comments = {}

        for i, col in enumerate(col_names):
            comment = comments.get(col, "")
            comment_str = f"  -- {comment}" if comment else ""
            log(f"  {col}{comment_str}")
            for ri, row in enumerate(rows):
                val = fmt_val(row[i])
                log(f"    → 例{ri+1}: {val}")

    cur.close()
    conn.close()


def process_mysql():
    log(f"\n\n{'='*100}")
    log("MySQL db_warehouse — Ozon 6表")
    log("=" * 100)

    conn = pymysql.connect(
        host="223.84.201.140", port=9030,
        user="wangyilong", password="wAng0730lonG",
        charset='utf8mb4', connect_timeout=10,
    )
    cur = conn.cursor()

    for table in MYSQL_TABLES:
        log(f"\n{'─'*90}")
        log(f"【{table}】")
        log(f"{'─'*90}")

        try:
            cur.execute(f"SELECT * FROM db_warehouse.`{table}` LIMIT 2")
            col_names = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        except Exception as e:
            log(f"  ⚠️ 查询失败: {e}")
            continue

        for i, col in enumerate(col_names):
            log(f"  {col}")
            for ri, row in enumerate(rows):
                val = fmt_val(row[i])
                log(f"    → 例{ri+1}: {val}")

    cur.close()
    conn.close()


def main():
    process_pg()
    process_mysql()
    log(f"\n\n{'='*100}")
    log("✅ 完成")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(TXT_OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n📄 已保存: {TXT_OUTPUT}")


if __name__ == "__main__":
    main()
