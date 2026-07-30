"""
查看 PostgreSQL 数据库中有哪些表和数据
结果自动保存到 scripts/output/ 目录
用法：python scripts/check_db_tables.py
"""
import psycopg2
import getpass
import os
from datetime import datetime

# ============================================
# 👇 在这里填写连接信息
# ============================================
HOST = "pgm-7xvui1j4600t1u27-l2.pg.rds.aliyuncs.com"
PORT = 5432
USER = "readuser"
PASSWORD = "Yy20251106!rus"
DATABASE = "postgres"
# ============================================

# 输出目录和文件
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"db_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

lines = []  # 收集所有输出，最后写入文件


def log(msg=""):
    """同时输出到控制台并保存到文件"""
    print(msg)
    lines.append(msg)


def main():
    host = HOST or input("主机地址 (HOST): ").strip()
    port = PORT or int(input("端口: ").strip() or "5432")
    user = USER or input("用户名 (USER): ").strip()
    password = PASSWORD or getpass.getpass("密码: ").strip()
    database = input(f"数据库名 (默认: {DATABASE}): ").strip() or DATABASE

    if not all([host, user, password]):
        log("❌ 主机地址、用户名、密码不能为空")
        return

    url = f"postgresql://{user}:******@{host}:{port}/{database}"
    log(f"\n🔗 正在连接 {url} ...")

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=database,
            connect_timeout=10,
        )
        cur = conn.cursor()

        cur.execute("SELECT datname FROM pg_database WHERE datname NOT IN ('template0', 'template1') AND datistemplate = false ORDER BY datname")
        db_names = [row[0] for row in cur.fetchall()]

        log(f"\n📁 找到 {len(db_names)} 个数据库\n")
        cur.close()
        conn.close()

        for db_name in db_names:
            conn2 = None
            try:
                conn2 = psycopg2.connect(
                    host=host, port=port, user=user, password=password,
                    dbname=db_name, connect_timeout=10,
                )
            except Exception:
                log(f"  ⚠️  [{db_name}] 无权限访问，跳过")
                continue

            try:
                cur2 = conn2.cursor()

                cur2.execute("""
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                    ORDER BY schema_name
                """)
                schemas = [row[0] for row in cur2.fetchall()]

                all_items = []

                for schema in schemas:
                    cur2.execute("""
                        SELECT table_schema, table_name, table_type,
                               pg_size_pretty(pg_total_relation_size(
                                   '"' || table_schema || '"."' || table_name || '"'
                               )) AS size
                        FROM information_schema.tables t
                        WHERE t.table_schema = %s
                        ORDER BY pg_total_relation_size(
                            '"' || t.table_schema || '"."' || t.table_name || '"'
                        ) DESC
                    """, (schema,))
                    all_items.extend(cur2.fetchall())

                if not all_items:
                    log(f"  📂 [{db_name}] — 无用户表/视图")
                else:
                    sep = "=" * 100
                    log(f"\n{sep}")
                    log(f"  📂 [{db_name}] — {len(all_items)} 个对象")
                    log(sep)
                    log(f"  {'Schema':<20} {'类型':<14} {'表名':<40} {'大小':<12}")
                    log("  " + "-" * 86)
                    for row in all_items:
                        schema = row[0]
                        table_name = row[1]
                        table_type = row[2]
                        size = row[3] if row[3] else "-"
                        log(f"  {schema:<20} {table_type:<14} {table_name:<40} {size:<12}")
                    log()

                    log(f"  📋 [{db_name}] 各表前 3 条数据预览:")
                    log()
                    for row in all_items:
                        schema = row[0]
                        table_name = row[1]
                        table_type = row[2]
                        if table_type == 'VIEW':
                            continue
                        try:
                            cur2.execute(f'SELECT * FROM "{schema}"."{table_name}" LIMIT 3')
                            columns = [desc[0] for desc in cur2.description]
                            rows = cur2.fetchall()
                            log(f"  --- {schema}.{table_name} ({', '.join(columns)}) ---")
                            if rows:
                                for r in rows:
                                    log(f"    {r}")
                            else:
                                log(f"    (空表)")
                            log()
                        except Exception as e:
                            log(f"  --- {schema}.{table_name} — 查询失败: {e}")
                            log()

                cur2.close()
            except Exception as e:
                log(f"  ❌ [{db_name}] 查询失败: {e}")
            finally:
                conn2.close()

        log(f"\n{'='*100}")
        log("✅ 检查完毕")

    except Exception as e:
        log(f"❌ 连接失败: {e}")

    # 写入文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n📄 结果已保存到: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
