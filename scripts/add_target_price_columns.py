#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Add target price columns to ozon.sku_management."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.database import engine
from sqlalchemy import text, inspect

COLUMNS = ["target_price_3pct", "target_price_5pct", "target_price_10pct"]

inspector = inspect(engine)
existing = {c["name"] for c in inspector.get_columns("sku_management", schema="ozon")}
to_add = [c for c in COLUMNS if c not in existing]

if not to_add:
    print("All columns already exist")
else:
    with engine.connect() as conn:
        for col in to_add:
            conn.execute(text(f"ALTER TABLE ozon.sku_management ADD COLUMN {col} NUMERIC(10, 2)"))
            print(f"  Added: {col}")
        conn.commit()
    print(f"Done: added {len(to_add)} column(s)")
