"""查 pg_stat_statements 中 sku_daily_snapshot 相关 SQL 原文"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()
try:
    rows = c.execute(text("""
        SELECT query, calls, last_execute_at
        FROM pg_stat_statements
        WHERE query ILIKE '%sku_daily_snapshot%'
        ORDER BY last_execute_at DESC NULLS LAST
        LIMIT 10
    """)).fetchall()
    print(f"pg_stat_statements 找到 {len(rows)} 条:")
    for r in rows:
        print(f"--- calls={r[1]} last={r[2]}")
        print(r[0][:600])
        print()
except Exception as ex:
    print("pg_stat_statements 不可用:", ex)
c.close()
