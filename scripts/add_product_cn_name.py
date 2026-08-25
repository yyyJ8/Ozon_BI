#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Add product_cn_name column to ozon.sku_management."""
import sys, io, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.database import engine
from sqlalchemy import text, inspect

COL = "product_cn_name"
inspector = inspect(engine)
existing = {c["name"] for c in inspector.get_columns("sku_management", schema="ozon")}

if COL in existing:
    print("Column already exists")
else:
    with engine.connect() as conn:
        conn.execute(text(f"ALTER TABLE ozon.sku_management ADD COLUMN {COL} VARCHAR(255)"))
        conn.commit()
    print(f"Added: {COL}")
