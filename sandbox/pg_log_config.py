"""查 PostgreSQL 日志配置和位置，尝试找 8-22 05:00 调度执行的 SQL"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from sqlalchemy import create_engine, text
from app.config import settings

e = create_engine(settings.database_url)
c = e.connect()
for opt in ("log_directory", "data_directory", "log_statement", "log_min_duration_statement", "logging_collector"):
    try:
        r = c.execute(text(f"SHOW {opt}")).scalar()
        print(f"{opt} = {r}")
    except Exception as ex:
        print(f"{opt}: {ex}")
c.close()
