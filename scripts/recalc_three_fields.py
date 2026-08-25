#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""只重算新增的 3 个公式字段：gross_weight_kg, purchase_cost_pct, product_cost_rmb"""
import sys, io, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.database import SessionLocal
from app.models import Product, SkuManagement
from app.services.sku_formulas import compute_formulas, INPUT_FIELDS

# 只更新这 3 个字段
TARGET_KEYS = ("gross_weight_kg", "purchase_cost_pct", "product_cost_rmb")

db = SessionLocal()
rows = db.query(SkuManagement, Product.marketing_seller_price, Product.commission_fbo_pct).join(
    Product,
    (SkuManagement.store_id == Product.store_id) & (SkuManagement.sku_id == Product.sku_id)
).all()

updated = 0
for mgmt, price, commission in rows:
    inputs = {f: getattr(mgmt, f, None) for f in INPUT_FIELDS}
    inputs["fbo_commission_pct"] = float(commission) if commission else None
    computed = compute_formulas(inputs, float(price) if price else None)

    changed = False
    for key in TARGET_KEYS:
        new_val = computed.get(key)
        if getattr(mgmt, key) != new_val:
            setattr(mgmt, key, new_val)
            changed = True
    if changed:
        updated += 1

db.commit()
print("Recalculated 3 fields on {} of {} records".format(updated, len(rows)))
db.close()
