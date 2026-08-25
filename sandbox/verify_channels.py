# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\OzonSku")
sys.stdout.reconfigure(encoding="utf-8")

from app.services.replenishment_service import get_replenishment_data

for sid in (1, 2, 3, 4, 5):
    rows = get_replenishment_data(store_id=sid)
    has_cb = [r for r in rows if r["cross_border_total"] > 0]
    print("=== store %d: total=%d, 有跨境在途=%d ===" % (sid, len(rows), len(has_cb)))
    for r in has_cb[:6]:
        print("   offer=%s cb=%s (SDK=%s 运盟=%s 昆仑=%s 超光速=%s)" % (
            r["offer_id"], r["cross_border_total"],
            r["cross_border_sdk"], r["cross_border_yunmeng"], r["cross_border_kunlun"], r["cross_border_cgs"]))
    print()

# 全店校验: cb_total == 渠道之和
rows_all = get_replenishment_data(store_id=0)
bad = [r for r in rows_all if r["cross_border_total"] != (r["cross_border_sdk"] + r["cross_border_yunmeng"] + r["cross_border_kunlun"] + r["cross_border_cgs"])]
print("全店行数:", len(rows_all), " cb_total 与渠道之和不一致的行数:", len(bad))
