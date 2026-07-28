"""追查佣金数据来源是否合理"""
from sqlalchemy import create_engine, text
DB_URL = "postgresql://wensixin:wenSixiN0949@192.168.111.78:5432/ai_application"
engine = create_engine(DB_URL)
conn = engine.connect()

print("=== 1. 产品类目佣金率分布 ===")
rows = conn.execute(text("""
    SELECT category_id, COUNT(*) as cnt,
           ROUND(AVG(commission_fbo_pct) * 100, 1) as avg_comm_pct,
           ROUND(MIN(commission_fbo_pct) * 100, 1) as min_c,
           ROUND(MAX(commission_fbo_pct) * 100, 1) as max_c
    FROM ozon.products WHERE store_id = 1 AND commission_fbo_pct IS NOT NULL
    GROUP BY category_id ORDER BY cnt DESC LIMIT 15
""")).fetchall()
for r in rows:
    print(f"  cat={r[0]:>10}: {r[1]}个, fbo佣金率={r[2]}% (范围{r[3]}%-{r[4]}%)")

print()
print("=== 2. 高佣金率 SKU (收入>50000) ===")
rows = conn.execute(text("""
    SELECT s.sku_id, s.offer_id, p.category_id, p.commission_fbo_pct,
           SUM(s.revenue) as rev, SUM(s.commissions) as comm,
           ROUND(SUM(s.commissions)/NULLIF(SUM(s.revenue),0)*-100, 2) as rate,
           SUM(s.ordered_units) as u,
           MAX(p.name) as pname
    FROM ozon.sku_daily_summary s
    LEFT JOIN ozon.products p ON s.sku_id=p.sku_id AND s.store_id=p.store_id
    WHERE s.store_id=1 AND s.revenue>0 AND s.commissions!=0
    GROUP BY s.sku_id, s.offer_id, p.category_id, p.commission_fbo_pct
    HAVING SUM(s.revenue) > 50000
    ORDER BY rate DESC LIMIT 10
""")).fetchall()
for r in rows:
    pct = float(r[3] or 0) * 100
    print(f"  sku={r[0]} | {r[1]} | cat={r[2]} | fbo率={pct:.1f}% | "
          f"实际佣金率={r[6]}% | rev={float(r[4]):>10,.0f} | comm={float(r[5]):>10,.0f} | units={r[7]}")

print()
print("=== 3. finance.sale_commission vs summary.commissions 逐日核对 ===")
rows = conn.execute(text("""
    SELECT s.sku_id, s.date, s.revenue, s.commissions as sc,
           COALESCE(
             (SELECT SUM(ft.sale_commission) FROM ozon.finance_transactions ft
              LEFT JOIN ozon.postings p ON ft.posting_number=p.posting_number AND ft.store_id=p.store_id
              WHERE ft.store_id=1 AND ft.sku_id=s.sku_id
                AND COALESCE(p.created_at::date, ft.operation_date)=s.date
                AND ft.operation_type='OperationAgentDeliveredToCustomer'), 0
           ) as fc
    FROM ozon.sku_daily_summary s
    WHERE s.store_id=1 AND s.commissions!=0 AND s.revenue>0
    ORDER BY s.date DESC LIMIT 15
""")).fetchall()
for r in rows:
    fc = float(r[4] or 0)
    sc = float(r[3] or 0)
    diff = fc - sc
    flag = " DIFF!" if abs(diff) > 0.01 else " OK"
    print(f"  {r[1]} | sku={r[0]} | rev={float(r[2]):>8,.0f} | s_comm={sc:>8,.0f} | f_comm={fc:>8,.0f} | diff={diff:.2f}{flag}")

print()
print("=== 4. 深入: 某高佣金SKU的所有 OperationAgentDeliveredToCustomer 流水 ===")
# 取佣金率最高的一个 SKU
top = conn.execute(text("""
    SELECT s.sku_id, SUM(s.revenue) as rev, SUM(s.commissions) as comm,
           ROUND(SUM(s.commissions)/NULLIF(SUM(s.revenue),0)*-100, 2) as rate
    FROM ozon.sku_daily_summary s WHERE s.store_id=1 AND s.revenue>50000 AND s.commissions!=0
    GROUP BY s.sku_id ORDER BY rate DESC LIMIT 1
""")).fetchone()
if top:
    sid = top[0]
    print(f"  SKU={sid}, 实际佣金率={top[3]}%")
    rows = conn.execute(text("""
        SELECT ft.operation_id, ft.operation_date, ft.amount,
               ft.accruals_for_sale, ft.sale_commission,
               ft.posting_number, ft.delivery_schema
        FROM ozon.finance_transactions ft
        WHERE ft.store_id=1 AND ft.sku_id=:sid
          AND ft.operation_type='OperationAgentDeliveredToCustomer'
        ORDER BY ft.operation_date DESC LIMIT 10
    """), {"sid": sid}).fetchall()
    for r in rows:
        accrual = float(r[3] or 0)
        comm = float(r[4] or 0)
        amt = float(r[2] or 0)
        rate = round(abs(comm) / accrual * 100, 1) if accrual else 0
        check = accrual + comm  # amount without logistics
        print(f"    op={r[0]} | {r[1]} | accrual={accrual:>8,.0f} | comm={comm:>8,.0f}({rate}%)"
              f" | amount={amt:>8,.0f} | posting={r[5]}")

# 5. 关键：对比 analytics revenue 和 finance accruals_for_sale
print()
print("=== 5. analytics revenue vs finance accruals_for_sale (同SKU同日) ===")
rows = conn.execute(text("""
    SELECT s.date, s.sku_id, s.revenue, s.ordered_units, s.delivered_units,
           s.commissions,
           COALESCE((SELECT SUM(ft.accruals_for_sale)
            FROM ozon.finance_transactions ft
            LEFT JOIN ozon.postings p ON ft.posting_number=p.posting_number AND ft.store_id=p.store_id
            WHERE ft.store_id=1 AND ft.sku_id=s.sku_id
              AND COALESCE(p.created_at::date, ft.operation_date)=s.date
              AND ft.operation_type='OperationAgentDeliveredToCustomer'), 0) as fin_accrual
    FROM ozon.sku_daily_summary s
    WHERE s.store_id=1 AND s.revenue>0 AND s.commissions!=0 AND s.revenue>10000
    ORDER BY s.date DESC LIMIT 10
""")).fetchall()
for r in rows:
    rev = float(r[2] or 0)
    fa = float(r[6] or 0)
    ratio = rev/fa if fa else 0
    print(f"  {r[1]} | sku={r[0]} | analytics_rev={rev:>10,.0f} | finance_accrual={fa:>10,.0f}"
          f" | ratio={ratio:.2f} | ordered={r[3]} | delivered={r[4]}")

conn.close()
engine.dispose()
