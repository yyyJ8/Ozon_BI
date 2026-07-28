"""核对物流数据：交叉验证 finance_transactions ↔ sku_daily_summary"""
from sqlalchemy import create_engine, text

DB_URL = "postgresql://wensixin:wenSixiN0949@192.168.111.78:5432/ai_application"
engine = create_engine(DB_URL)
conn = engine.connect()

print("=" * 70)
print("=== 1. sku_daily_summary 物流费总览（按店铺）===")
print("=" * 70)
rows = conn.execute(text("""
    SELECT store_id,
           COUNT(*) as row_cnt,
           COUNT(CASE WHEN logistics_costs != 0 THEN 1 END) as rows_w_l,
           SUM(logistics_costs) as total_l,
           MIN(logistics_costs) as min_l,
           MAX(logistics_costs) as max_l
    FROM ozon.sku_daily_summary
    GROUP BY store_id ORDER BY store_id
""")).fetchall()
for r in rows:
    print(f"store={r[0]}: {r[1]}行, 有物流费={r[2]}行, "
          f"总和={r[3]}, min={r[4]}, max={r[5]}")

print()
print("=" * 70)
print("=== 2. 物流费按月份汇总 ===")
print("=" * 70)
rows = conn.execute(text("""
    SELECT store_id, DATE_TRUNC('month', date)::date AS mon,
           SUM(logistics_costs) as total_l,
           SUM(revenue) as total_rev
    FROM ozon.sku_daily_summary
    WHERE logistics_costs != 0
    GROUP BY store_id, DATE_TRUNC('month', date)
    ORDER BY store_id, mon DESC
""")).fetchall()
for r in rows:
    rev = float(r[3] or 0)
    lc = float(r[2] or 0)
    rate = round(-lc / rev * 100, 2) if rev else 0
    print(f"  store={r[0]} | {r[1]} | 物流费={r[2]} | 收入={r[3]} | 费率={rate}%")

print()
print("=" * 70)
print("=== 3. finance_transactions 物流相关字段统计 ===")
print("=" * 70)
rows = conn.execute(text("""
    SELECT store_id,
           COUNT(*) as cnt,
           COUNT(CASE WHEN delivery_charge != 0 THEN 1 END) as dc_cnt,
           COUNT(CASE WHEN return_delivery_charge != 0 THEN 1 END) as rdc_cnt,
           SUM(delivery_charge) as sum_dc,
           SUM(return_delivery_charge) as sum_rdc
    FROM ozon.finance_transactions
    GROUP BY store_id ORDER BY store_id
""")).fetchall()
for r in rows:
    print(f"store={r[0]}: 总计{r[1]}条, "
          f"delivery_charge={r[2]}条 合计{r[4]}, "
          f"return_delivery={r[3]}条 合计{r[5]}")

print()
print("=" * 70)
print("=== 4. finance 按 operation_type 分组（含物流的） ===")
print("=" * 70)
rows = conn.execute(text("""
    SELECT store_id, operation_type,
           COUNT(*) as cnt,
           SUM(delivery_charge) as sum_dc,
           SUM(return_delivery_charge) as sum_rdc,
           SUM(amount) as sum_amt
    FROM ozon.finance_transactions
    WHERE delivery_charge != 0 OR return_delivery_charge != 0
    GROUP BY store_id, operation_type
    ORDER BY store_id, cnt DESC
""")).fetchall()
for r in rows:
    print(f"  store={r[0]} | {r[1]}: {r[2]}条 | "
          f"del={r[3]} | ret_del={r[4]} | amt={r[5]}")

print()
print("=" * 70)
print("=== 5. 交叉核对：finance 物流费 vs summary 物流费（按天汇总对比）===")
print("=" * 70)

# finance侧：按 posting.created_at 归因后的物流费
rows = conn.execute(text("""
    WITH finance_logistics AS (
        SELECT
            ft.store_id,
            COALESCE(p.created_at::date, ft.operation_date) AS attr_date,
            SUM(ft.delivery_charge) + SUM(ft.return_delivery_charge) AS fin_logistics
        FROM ozon.finance_transactions ft
        LEFT JOIN ozon.postings p ON ft.posting_number = p.posting_number
            AND ft.store_id = p.store_id
        WHERE ft.delivery_charge != 0 OR ft.return_delivery_charge != 0
        GROUP BY ft.store_id, COALESCE(p.created_at::date, ft.operation_date)
    ),
    summary_logistics AS (
        SELECT store_id, date AS attr_date,
               SUM(logistics_costs) AS sum_logistics
        FROM ozon.sku_daily_summary
        WHERE logistics_costs != 0
        GROUP BY store_id, date
    )
    SELECT
        fl.store_id, fl.attr_date,
        fl.fin_logistics,
        COALESCE(sl.sum_logistics, 0) AS sum_logistics,
        fl.fin_logistics - COALESCE(sl.sum_logistics, 0) AS diff
    FROM finance_logistics fl
    LEFT JOIN summary_logistics sl
        ON fl.store_id = sl.store_id AND fl.attr_date = sl.attr_date
    ORDER BY fl.attr_date DESC
""")).fetchall()

if rows:
    for r in rows:
        diff = float(r[4] or 0)
        flag = " ⚠️ 不一致!" if abs(diff) > 0.01 else ""
        print(f"  store={r[0]} | {r[1]} | finance={r[2]} | summary={r[3]} | diff={r[4]}{flag}")
else:
    print("  无数据")

# 总差异
print()
total_diff = conn.execute(text("""
    WITH finance_logistics AS (
        SELECT
            ft.store_id,
            COALESCE(p.created_at::date, ft.operation_date) AS attr_date,
            SUM(ft.delivery_charge) + SUM(ft.return_delivery_charge) AS fin_logistics
        FROM ozon.finance_transactions ft
        LEFT JOIN ozon.postings p ON ft.posting_number = p.posting_number
            AND ft.store_id = p.store_id
        WHERE ft.delivery_charge != 0 OR ft.return_delivery_charge != 0
        GROUP BY ft.store_id, COALESCE(p.created_at::date, ft.operation_date)
    ),
    summary_logistics AS (
        SELECT store_id, date AS attr_date,
               SUM(logistics_costs) AS sum_logistics
        FROM ozon.sku_daily_summary
        WHERE logistics_costs != 0
        GROUP BY store_id, date
    )
    SELECT
        fl.store_id,
        SUM(fl.fin_logistics) AS total_fin,
        SUM(COALESCE(sl.sum_logistics, 0)) AS total_sum,
        SUM(fl.fin_logistics) - SUM(COALESCE(sl.sum_logistics, 0)) AS total_diff
    FROM finance_logistics fl
    LEFT JOIN summary_logistics sl
        ON fl.store_id = sl.store_id AND fl.attr_date = sl.attr_date
    GROUP BY fl.store_id
""")).fetchall()
print("--- 按店铺汇总差异 ---")
for r in total_diff:
    diff = float(r[3] or 0)
    flag = " ⚠️ 存在差异!" if abs(diff) > 0.01 else " ✅ 一致"
    print(f"  store={r[0]}: finance汇总={r[1]}, summary汇总={r[2]}, diff={r[3]}{flag}")

print()
print("=" * 70)
print("=== 6. 无 SKU 的 finance 物流费（门店级费用）===")
print("=" * 70)
rows = conn.execute(text("""
    SELECT store_id, operation_type, COUNT(*) as cnt,
           SUM(delivery_charge) as sum_dc,
           SUM(return_delivery_charge) as sum_rdc,
           SUM(amount) as sum_amt
    FROM ozon.finance_transactions
    WHERE (delivery_charge != 0 OR return_delivery_charge != 0)
      AND sku_id IS NULL
    GROUP BY store_id, operation_type
    ORDER BY store_id, cnt DESC
""")).fetchall()
if rows:
    for r in rows:
        print(f"  store={r[0]} | {r[1]}: {r[2]}条 | "
              f"del={r[3]} | ret_del={r[4]} | amt={r[5]}")
else:
    print("  无（全部物流费都有 SKU）")

print()
print("=" * 70)
print("=== 7. 抽查：最近几天物流费不为0的详情 ===")
print("=" * 70)
rows = conn.execute(text("""
    SELECT store_id, date, sku_id, offer_id,
           revenue, logistics_costs, net_profit
    FROM ozon.sku_daily_summary
    WHERE logistics_costs != 0
    ORDER BY date DESC
    LIMIT 20
""")).fetchall()
for r in rows:
    lr = round(float(r[5] or 0) / float(r[4] or 1) * -100, 1) if float(r[4] or 0) else 0
    print(f"  {r[1]} | store={r[0]} | sku={r[2]} | offer={r[3]} | "
          f"收入={r[4]} | 物流={r[5]} | 费率={lr}% | 净利={r[6]}")

conn.close()
engine.dispose()
print()
print("核对完成!")
