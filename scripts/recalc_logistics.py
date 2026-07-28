"""重新计算物流费 — 修复后的 cost_service.build_costs"""
import sys
sys.path.insert(0, ".")

from datetime import date
from app.database import SessionLocal
from app.services.cost_service import build_costs
from app.services.profit_service import build_profit

MONTHS = [
    (date(2026, 3, 1), date(2026, 3, 31)),
    (date(2026, 4, 1), date(2026, 4, 30)),
    (date(2026, 5, 1), date(2026, 5, 31)),
    (date(2026, 6, 1), date(2026, 6, 30)),
    (date(2026, 7, 1), date(2026, 7, 31)),
]

STORES = [1, 2]

for store_id in STORES:
    print(f"\n{'='*60}")
    print(f"=== 处理 store={store_id} ===")
    print(f"{'='*60}")
    db = SessionLocal()
    try:
        for start, end in MONTHS:
            print(f"\n--- {start} ~ {end} ---")
            result = build_costs(db, start, end, store_id)
            print(f"  costs: {result}")

            result2 = build_profit(db, start, end, store_id)
            print(f"  profit: {result2}")
    finally:
        db.close()

print("\n全部完成!")
