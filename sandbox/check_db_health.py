"""检查数据库健康 + 活动查询/锁"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()
print("DB 连接正常")
try:
    print("\n=== 活动查询 ===")
    for r in c.execute(text(
        "SELECT pid, state, wait_event_type, wait_event, LEFT(query, 120) AS q, now()-query_start AS dur "
        "FROM pg_stat_activity WHERE datname=current_database() AND state <> 'idle' AND pid <> pg_backend_pid()"
    )):
        print(" ", tuple(r))
    print("\n=== 锁 ===")
    for r in c.execute(text(
        "SELECT pid, relation::regclass, mode, granted FROM pg_locks WHERE NOT granted"
    )):
        print(" ", tuple(r))
except Exception as ex:
    print("查询失败:", ex)
c.close()
