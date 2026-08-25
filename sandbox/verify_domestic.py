# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\OzonSku")
sys.stdout.reconfigure(encoding="utf-8")

from app.services.replenishment_service import get_replenishment_data

for sid in (1, 2, 3, 4, 5):
    rows = get_replenishment_data(store_id=sid)
    has_dom = [r for r in rows if r["domestic_in_transit"] > 0]
    print("=== store %d: total=%d, 有国内在途=%d ===" % (sid, len(rows), len(has_dom)))
    for r in has_dom[:5]:
        print("   offer=%s 国内在途=%s 跨境在途=%s" % (r["offer_id"], r["domestic_in_transit"], r["cross_border_total"]))
    print()
