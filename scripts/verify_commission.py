from sqlalchemy import create_engine, text
DB_URL = "postgresql://wensixin:wenSixiN0949@192.168.111.78:5432/ai_application"
engine = create_engine(DB_URL)
conn = engine.connect()

# SKU=3646802847, commission_fbo_pct=47%
rows = conn.execute(text("""
    SELECT s.date, s.ordered_units, s.delivered_units, s.revenue, s.commissions,
           ROUND(abs(s.commissions)/NULLIF(s.revenue,0)*100, 1) as day_rate
    FROM ozon.sku_daily_summary s
    WHERE s.store_id=1 AND s.sku_id=3646802847 AND s.revenue>0
    ORDER BY s.date DESC LIMIT 12
""")).fetchall()

print("SKU=3646802847, products.commission_fbo_pct = 47%")
print()
print(f"{'date':>12} | ordered | delivered | {'revenue':>10} | {'comm':>10} | day_rate")
print("-" * 75)
for r in rows:
    print(f"{str(r[0]):>12} | {r[1]:>7} | {r[2]:>9} | {float(r[3]):>10,.0f} | {float(r[4]):>10,.0f} | {r[5]}%")

# 单笔交易级
print()
print("=== single transaction level ===")
rows2 = conn.execute(text("""
    SELECT ft.operation_date, ft.accruals_for_sale, ft.sale_commission,
           ROUND(abs(ft.sale_commission)/NULLIF(ft.accruals_for_sale,0)*100, 1) as tx_rate
    FROM ozon.finance_transactions ft
    WHERE ft.store_id=1 AND ft.sku_id=3646802847
      AND ft.operation_type='OperationAgentDeliveredToCustomer'
    ORDER BY ft.operation_date DESC LIMIT 10
""")).fetchall()
print(f"{'date':>12} | {'accrual':>10} | {'comm':>10} | tx_rate")
print("-" * 50)
for r in rows2:
    print(f"{str(r[0]):>12} | {float(r[1] or 0):>10,.0f} | {float(r[2] or 0):>10,.0f} | {r[3]}%")

conn.close()
engine.dispose()
