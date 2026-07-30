"""
提取 PostgreSQL omsprod 和 MySQL db_warehouse 中目标表的字段+实际数据
"""
import psycopg2
import pymysql
import json
from datetime import datetime

OUTPUT_DIR = "scripts/output"
OUTPUT_FILE = f"{OUTPUT_DIR}/all_tables_with_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

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
    """格式化值为可读字符串"""
    if v is None:
        return "NULL"
    if isinstance(v, bytes):
        try:
            return v.decode('utf-8')
        except:
            return str(v)
    if isinstance(v, datetime):
        return v.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(v, (dict, list)):
        s = json.dumps(v, ensure_ascii=False)
        return s[:200] + "..." if len(s) > 200 else s
    s = str(v)
    return s[:200] + "..." if len(s) > 200 else s


def process_pg():
    log("=" * 100)
    log("PostgreSQL omsprod — 申购/采购/发货 6表")
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

        # 取2条数据
        cur.execute(f'SELECT * FROM public."{table}" LIMIT 2')
        col_names = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        # 取列注释
        cur.execute("""
            SELECT a.attname, pg_catalog.col_description(a.attrelid, a.attnum)
            FROM pg_catalog.pg_attribute a
            WHERE a.attrelid = %s::regclass AND a.attnum > 0 AND NOT a.attisdropped
            ORDER BY a.attnum
        """, (table,))
        comments = {r[0]: r[1] for r in cur.fetchall()}

        for i, col in enumerate(col_names):
            comment = comments.get(col, "")
            comment_str = f"  -- {comment}" if comment else ""

            if len(rows) == 0:
                log(f"  {col}{comment_str}")
                log(f"    → (空表，无数据)")
            elif len(rows) == 1:
                val1 = fmt_val(rows[0][i])
                log(f"  {col}{comment_str}")
                log(f"    → [{val1}]")
            else:
                val1 = fmt_val(rows[0][i])
                val2 = fmt_val(rows[1][i])
                log(f"  {col}{comment_str}")
                log(f"    → 例1: {val1}")
                log(f"    → 例2: {val2}")

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
            if len(rows) == 0:
                log(f"  {col}")
                log(f"    → (空表，无数据)")
            elif len(rows) == 1:
                val1 = fmt_val(rows[0][i])
                log(f"  {col}")
                log(f"    → [{val1}]")
            else:
                val1 = fmt_val(rows[0][i])
                val2 = fmt_val(rows[1][i])
                log(f"  {col}")
                log(f"    → 例1: {val1}")
                log(f"    → 例2: {val2}")

    cur.close()
    conn.close()


def main():
    process_pg()
    process_mysql()
    log(f"\n\n{'='*100}")
    log("✅ 完成")

    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n📄 已保存: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
