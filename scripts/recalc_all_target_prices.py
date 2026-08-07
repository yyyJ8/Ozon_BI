#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Recalculate all target prices for existing sku_management records."""
import sys, io, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.database import SessionLocal
from app.models import Product, SkuManagement
from app.services.sku_formulas import compute_formulas, INPUT_FIELDS

db = SessionLocal()

# 找出所有有 sku_management 记录的 SKU
rows = db.query(SkuManagement, Product.marketing_seller_price).join(
    Product,
    (SkuManagement.store_id == Product.store_id) & (SkuManagement.sku_id == Product.sku_id)
).all()

updated = 0
skipped = 0

for mgmt, price in rows:
    inputs = {f: getattr(mgmt, f, None) for f in INPUT_FIELDS}
    computed = compute_formulas(inputs, float(price) if price else None)

    changed = False
    for key in ("target_price_3pct", "target_price_5pct", "target_price_10pct"):
        new_val = computed.get(key)
        if getattr(mgmt, key) != new_val:
            setattr(mgmt, key, new_val)
            changed = True
    # Also update all computed fields while we're at it
    for key in computed:
        if hasattr(mgmt, key) and getattr(mgmt, key) != computed[key]:
            setattr(mgmt, key, computed[key])
            changed = True

    if changed:
        updated += 1
    else:
        skipped += 1

db.commit()
print(f"Updated: {updated}, Skipped (no change): {skipped}")
db.close()
