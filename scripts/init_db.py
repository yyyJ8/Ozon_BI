"""
初始化数据库 — 在 PostgreSQL 中创建 ozon schema 的 5 张表
运行: python scripts/init_db.py
"""
import sys
from pathlib import Path

# 确保项目根目录在 path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text

from app.database import Base, engine
from app.models import Product, Stock, SkuDailySummary, FinanceTransaction, SyncLog


def create_tables():
    # 先确保 ozon schema 存在
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS ozon"))
        conn.commit()

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 验证建表结果
    inspector = inspect(engine)
    schemas = inspector.get_schema_names()
    print("=== Schema 列表 ===")
    for s in schemas:
        tables = inspector.get_table_names(schema=s)
        if tables:
            print(f"  {s}: {tables}")

    # 打印 ozon 下的表结构
    print("\n=== ozon 表结构 ===")
    for table_name in ["products", "stocks", "sku_daily_summary", "finance_transactions", "sync_log"]:
        columns = inspector.get_columns(table_name, schema="ozon")
        print(f"\n--- {table_name} ---")
        for col in columns:
            pk = "PK" if col.get("primary_key") else ""
            nullable = "" if col.get("nullable", True) else "NOT NULL"
            print(f"  {col['name']:30s} {str(col['type']):25s} {nullable} {pk}")


if __name__ == "__main__":
    create_tables()
