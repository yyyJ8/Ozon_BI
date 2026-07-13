"""
验证 1: PostgreSQL 数据库连接 + ozon schema
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

print("=" * 60)
print("  数据库连接验证")
print("=" * 60)
print("  目标: %s:%s/%s" % (DB_HOST, DB_PORT, DB_NAME))
print("  用户: %s" % DB_USER)
print()

conn_str = "postgresql://%s:%s@%s:%s/%s" % (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)

try:
    engine = create_engine(conn_str)
    with engine.connect() as conn:
        # 版本信息
        result = conn.execute(text("SELECT version()"))
        row = result.fetchone()
        print("  [OK] 连接成功")
        print("  [DB] %s" % row[0])

        # 检查 ozon schema
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata"))
        schemas = [row[0] for row in result]
        if "ozon" in schemas:
            print("  [OK] ozon schema 已存在")
        else:
            print("  [..] ozon schema 不存在，后续会创建")

        # 检查已有表
        result = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'ozon'"
            )
        )
        tables = [row[0] for row in result]
        if tables:
            print("  [OK] 已有表: %s" % tables)
        else:
            print("  [..] ozon schema 为空表，待创建")

except Exception as e:
    print("  [FAIL] %s" % e)

print("=" * 60)
