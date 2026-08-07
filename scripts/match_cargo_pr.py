"""匹配 cargo_shipments → ozon_direct_shipment 找到对应 pr_no"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# 1. sku + logistics_inbound_no → first_leg_tracking (精确匹配)
matched_inbound = db.execute(text("""
    SELECT cs.sku, cs.logistics_inbound_no, ds.pr_no
    FROM ozon.cargo_shipments cs
    JOIN ozon.ozon_direct_shipment ds ON ds.is_deleted = false
        AND ds.sku = cs.sku
        AND ds.first_leg_tracking = cs.logistics_inbound_no
    WHERE cs.logistics_inbound_no IS NOT NULL
""")).fetchall()
print(f"=== sku + logistics_inbound_no = first_leg_tracking: {len(matched_inbound)} ===")
for r in matched_inbound:
    print(f"  {r[0]} | {r[1]} → {r[2]}")

# 2. sku only (备用)
matched_sku = db.execute(text("""
    SELECT cs.sku, ds.pr_no
    FROM ozon.cargo_shipments cs
    JOIN ozon.ozon_direct_shipment ds ON ds.is_deleted = false AND ds.sku = cs.sku
    WHERE cs.sku NOT IN (
        SELECT cs2.sku FROM ozon.cargo_shipments cs2
        JOIN ozon.ozon_direct_shipment ds2 ON ds2.is_deleted = false
            AND ds2.sku = cs2.sku AND ds2.first_leg_tracking = cs2.logistics_inbound_no
        WHERE cs2.logistics_inbound_no IS NOT NULL
    )
""")).fetchall()
print(f"\n=== sku only (fallback): {len(matched_sku)} ===")
for r in matched_sku[:10]:
    print(f"  {r[0]} → {r[1]}")
if len(matched_sku) > 10:
    print(f"  ... +{len(matched_sku) - 10} more")

# 3. 未匹配
unmatched = db.execute(text("""
    SELECT cs.sku, cs.logistics_inbound_no
    FROM ozon.cargo_shipments cs
    WHERE NOT EXISTS (
        SELECT 1 FROM ozon.ozon_direct_shipment ds
        WHERE ds.is_deleted = false AND ds.sku = cs.sku
    )
""")).fetchall()
print(f"\n=== 未匹配: {len(unmatched)} ===")
for r in unmatched:
    print(f"  {r[0]} inbound={r[1]}")

db.close()
print("\nDone.")
