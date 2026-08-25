# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\OzonSku")
sys.stdout.reconfigure(encoding="utf-8")

from app.services.replenishment_service import get_replenishment_data

HEART = "\u2665\u263a\u2665"
for sid in (3, 4, 5):
    rows = get_replenishment_data(store_id=sid)
    need = [r for r in rows if r["suggested_replenishment"] != HEART]
    print("=== store %d: total=%d, need=%d ===" % (sid, len(rows), len(need)))
    for r in rows[:5]:
        print("   offer=%s stock=%s wds=%s qty=%s suggested=%s" % (
            r["offer_id"], r["stock_present"], r["weighted_daily_sales"],
            r["replenishment_qty_raw"], r["suggested_replenishment"]))
    print()
