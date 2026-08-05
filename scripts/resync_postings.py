"""重新同步 posting — 逐日拉 list API，日志精确到天"""
import sys, os, time
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from sqlalchemy import text
from app.clients.ozon import OzonClient
from app.services.posting_sync import _upsert_posting

LOG = os.path.join(os.path.dirname(__file__), "..", "sync_progress.log")

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

db = SessionLocal()
stores = db.execute(text("SELECT id, name, client_id, api_key FROM ozon.stores WHERE is_active = TRUE")).fetchall()
earliest = db.execute(text("SELECT MIN(created_at) FROM ozon.postings")).fetchone()
start = earliest[0].date() if earliest[0] else date(2026, 3, 1)
end = datetime.now().date()
db.close()

# 生成日期列表
days = []
d = start
while d <= end:
    days.append(d)
    d += timedelta(days=1)

log(f"=== Posting 逐日同步: {start} → {end}, 共 {len(days)} 天, {len(stores)} 店铺 ===")

for s in stores:
    sid, sname, cid, akey = s[0], s[1], s[2], s[3]
    log(f"店铺 {sid} ({sname}) 开始")
    client = OzonClient(cid, akey)

    total_ins = total_upd = total_dfill = 0
    t0 = time.time()

    for i, day in enumerate(days):
        ds = day.isoformat()
        day_ins = day_upd = 0

        db2 = SessionLocal()
        try:
            # pull FBO + FBS
            for schema in ("FBO", "FBS"):
                postings = client.get_all_postings(ds, ds, schema=schema)
                for p in postings:
                    if p.get("delivery_schema") is None:
                        p["delivery_schema"] = schema
                    if _upsert_posting(db2, p, sid):
                        day_ins += 1
                    else:
                        day_upd += 1

            # Phase 3: fill delivered_at from finance
            filled = db2.execute(text("""
                UPDATE ozon.postings p SET delivered_at = (
                    SELECT MIN(ft.operation_date)::timestamp
                    FROM ozon.finance_transactions ft
                    WHERE ft.posting_number = p.posting_number
                      AND ft.operation_type = 'OperationAgentDeliveredToCustomer'
                ), synced_at = NOW()
                WHERE p.store_id = :sid AND p.status = 'delivered'
                  AND p.delivered_at IS NULL
                  AND EXISTS (
                    SELECT 1 FROM ozon.finance_transactions ft
                    WHERE ft.posting_number = p.posting_number
                      AND ft.operation_type = 'OperationAgentDeliveredToCustomer'
                  )
            """), {"sid": sid}).rowcount

            db2.commit()
            total_ins += day_ins
            total_upd += day_upd
            total_dfill += filled

            pct = (i + 1) / len(days) * 100
            parts = [f"ins={day_ins} upd={day_upd}"]
            if filled:
                parts.append(f"dfill={filled}")
            log(f"  [{i+1}/{len(days)} {pct:.0f}%] {ds}  "
                + "  ".join(parts)
                + f"  | 累计 ins={total_ins} upd={total_upd} dfill={total_dfill}")

        except Exception as e:
            log(f"  [{i+1}/{len(days)}] {ds}  失败: {e}")
        finally:
            db2.close()

    elapsed = time.time() - t0
    log(f"店铺 {sid} 完成 ({elapsed:.0f}s): ins={total_ins} upd={total_upd} dfill={total_dfill}")
    client.close()

log("=== Posting 逐日同步结束 ===")
