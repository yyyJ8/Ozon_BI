"""全量同步所有店铺 — 进度写入 sync_progress.log"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from app.database import SessionLocal, engine
from app.models import Base
from app.services.sync_service import run_full_sync

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "sync_progress.log")

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

log("=== 全量同步开始 ===")
db = SessionLocal()

# 查店铺
from sqlalchemy import text
stores = db.execute(text("SELECT id, name, client_id, api_key FROM ozon.stores WHERE is_active = TRUE")).fetchall()
db.close()

log(f"活跃店铺: {len(stores)} 个")

for s in stores:
    log(f"--- 店铺 {s[0]}: {s[1]} ---")
    db2 = SessionLocal()
    try:
        from app.clients.ozon import OzonClient
        client = OzonClient(s[2], s[3])
        t0 = time.time()
        result = run_full_sync(db2, client, s[0], days_back=500)
        elapsed = time.time() - t0
        log(f"  完成 ({elapsed:.0f}s): {result}")
    except Exception as e:
        log(f"  失败: {e}")
    finally:
        db2.close()

log("=== 全量同步结束 ===")
