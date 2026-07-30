"""
查看 MySQL 数据库中有哪些表和数据
结果自动保存到 scripts/output/ 目录
用法：python scripts/check_mysql_tables.py
"""
import pymysql
import os
from datetime import datetime

# ============================================
# 👇 在这里填写连接信息
# ============================================
HOST = "223.84.201.140"
PORT = 9030
USER = "wangyilong"
PASSWORD = "wAng0730lonG"
FILTER_KEYWORD = "ozon"  # 筛选包含此关键字的表名
# ============================================

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"mysql_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

lines = []


def log(msg=""):
    print(msg)
    lines.append(msg)


def main():
    url = f"mysql://{USER}:******@{HOST}:{PORT}"
    log(f"🔗 正在连接 {url} ...")

    try:
        conn = pymysql.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            charset='utf8mb4',
            connect_timeout=10,
        )
        cur = conn.cursor()

        # 列出所有数据库
        cur.execute("SHOW DATABASES")
        db_names = [row[0] for row in cur.fetchall()]

        # 排除系统库
        sys_dbs = {'information_schema', 'mysql', 'performance_schema', 'sys', '__recycle_bin__'}
        user_dbs = [db for db in db_names if db not in sys_dbs]

        log(f"\n📁 找到 {len(user_dbs)} 个用户数据库 (共 {len(db_names)} 个)\n")

        for db_name in user_dbs:
            try:
                cur.execute(f"USE `{db_name}`")
            except Exception:
                log(f"  ⚠️  [{db_name}] 无法访问，跳过")
                continue

            # 列出所有表
            cur.execute(f"""
                SELECT TABLE_NAME, TABLE_TYPE,
                       TABLE_ROWS, DATA_LENGTH + INDEX_LENGTH,
                       CREATE_TIME, TABLE_COMMENT
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = '{db_name}'
                ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC
            """)
            tables = cur.fetchall()

            if not tables:
                log(f"  📂 [{db_name}] — 无表")
                continue

            # 筛选含 ozon 的表
            filtered = [t for t in tables if FILTER_KEYWORD.lower() in t[0].lower()]

            if not filtered:
                # 显示前10个表名作为预览
                preview = ", ".join([t[0] for t in tables[:10]])
                more = f" ... (+{len(tables)-10})" if len(tables) > 10 else ""
                log(f"  📂 [{db_name}] — {len(tables)} 个表 (无匹配 '{FILTER_KEYWORD}' 的表，例如: {preview}{more})")
                continue

            # 计算大小
            def fmt_size(size_bytes):
                if size_bytes is None:
                    return "-"
                size_bytes = int(size_bytes)
                if size_bytes >= 1073741824:
                    return f"{size_bytes/1073741824:.2f} GB"
                elif size_bytes >= 1048576:
                    return f"{size_bytes/1048576:.2f} MB"
                elif size_bytes >= 1024:
                    return f"{size_bytes/1024:.2f} KB"
                else:
                    return f"{size_bytes} B"

            sep = "=" * 100
            log(f"\n{sep}")
            log(f"  📂 [{db_name}] — {len(tables)} 个表, 匹配 '{FILTER_KEYWORD}' 的 {len(filtered)} 个")
            log(sep)
            log(f"  {'表名':<45} {'类型':<14} {'行数':<12} {'大小':<14} {'创建时间':<22} {'备注'}")
            log("  " + "-" * 130)
            for t in filtered:
                name, ttype, rows, size, create_time, comment = t
                log(f"  {name:<45} {ttype:<14} {str(rows or '-'):<12} {fmt_size(size):<14} {str(create_time or '-'):<22} {comment or ''}")
            log()

            # 每个表：结构 + 前3条数据
            for t in filtered:
                name = t[0]
                ttype = t[1]
                if ttype == 'VIEW':
                    continue

                log(f"  {'─'*80}")
                log(f"  📋 [{db_name}.{name}]")

                # 表结构
                try:
                    cur.execute(f"SHOW FULL COLUMNS FROM `{db_name}`.`{name}`")
                    columns = cur.fetchall()
                    log(f"  字段 ({len(columns)} 列):")
                    for col in columns:
                        field, col_type, collation, null, key, default, extra, priv, comment = col
                        extras = []
                        if key == 'PRI':
                            extras.append('PK')
                        if null == 'NO':
                            extras.append('NOT NULL')
                        if default is not None:
                            extras.append(f'default={default}')
                        extra_str = ', '.join(extras) if extras else ''
                        comment_str = f" -- {comment}" if comment else ""
                        log(f"    {field:<35} {col_type:<25} {extra_str:<30}{comment_str}")
                except Exception as e:
                    log(f"  ⚠️ 获取结构失败: {e}")

                # 前3条数据
                try:
                    cur.execute(f"SELECT * FROM `{db_name}`.`{name}` LIMIT 3")
                    col_names = [desc[0] for desc in cur.description]
                    rows_data = cur.fetchall()
                    log(f"  数据预览 ({len(rows_data)} 条):")
                    if rows_data:
                        for i, row in enumerate(rows_data):
                            log(f"    --- 第 {i+1} 行 ---")
                            for j, col_name in enumerate(col_names):
                                val = row[j]
                                if isinstance(val, bytes):
                                    val = val.decode('utf-8', errors='replace')
                                log(f"      {col_name}: {val}")
                    else:
                        log(f"    (空表)")
                except Exception as e:
                    log(f"  ⚠️ 查询数据失败: {e}")
                log()

        cur.close()
        conn.close()

        log(f"\n{'='*100}")
        log("✅ 检查完毕")

    except Exception as e:
        log(f"❌ 连接失败: {e}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"\n📄 结果已保存到: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
