"""一次性入库：全量拉取 Ozon 退货数据并写入 returns 表

时间范围：2024-01-01 ~ 2026-07-16（覆盖所有历史）
来源：/v1/returns/list (FBO + FBS)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal, engine
from app.models import Base, Return
from app.clients.ozon import get_ozon_client
from app.services.returns_sync import sync_returns

# 1. 确保表存在
print("Ensuring returns table exists...")
Return.__table__.create(bind=engine, checkfirst=True)
print("OK")

# 2. 全量拉取
client = get_ozon_client()
db = SessionLocal()

try:
    result = sync_returns(
        db, client,
        date_from="2024-01-01",
        date_to="2026-07-16",
    )
    print(f"\nDone: {result}")
finally:
    db.close()
    client.close()
