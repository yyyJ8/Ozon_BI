"""Backfill delivered_at from finance_transactions for delivered postings"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

count = db.execute(text("""
    SELECT COUNT(*)
    FROM ozon.postings p
    WHERE p.status = 'delivered' AND p.delivered_at IS NULL
""")).fetchone()[0]
print(f"Missing delivered_at: {count}")

result = db.execute(text("""
    UPDATE ozon.postings p
    SET delivered_at = (
        SELECT MIN(ft.operation_date)::timestamp
        FROM ozon.finance_transactions ft
        WHERE ft.posting_number = p.posting_number
          AND ft.operation_type = 'OperationAgentDeliveredToCustomer'
    ),
    synced_at = NOW()
    WHERE p.status = 'delivered'
      AND p.delivered_at IS NULL
      AND EXISTS (
        SELECT 1 FROM ozon.finance_transactions ft
        WHERE ft.posting_number = p.posting_number
          AND ft.operation_type = 'OperationAgentDeliveredToCustomer'
      )
"""))
db.commit()
print(f"Filled: {result.rowcount}")

remaining = db.execute(text("""
    SELECT COUNT(*) FROM ozon.postings
    WHERE status = 'delivered' AND delivered_at IS NULL
""")).fetchone()[0]
print(f"Remaining: {remaining}")

db.close()
