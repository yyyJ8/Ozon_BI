"""查询指定 offer_id 的所有成本数据"""
import sys
from sqlalchemy import create_engine, text

DB_URL = "postgresql://wensixin:wenSixiN0949@192.168.111.78:5432/ai_application"
engine = create_engine(DB_URL)
conn = engine.connect()
offer_id = sys.argv[1] if len(sys.argv) > 1 else "37248-Y07U0001-B01"

# 1. 找 sku_id
print("=== 1. 商品基本信息 ===")
rows = conn.execute(text("""
    SELECT sku_id, offer_id, name, price, old_price, commission_fbo_pct, volume_weight, status
    FROM ozon.products
    WHERE offer_id = :oid
"""), {"oid": offer_id}).fetchall()

for r in rows:
    print(dict(r._mapping))

if not rows:
    print(f"未找到 offer_id={offer_id} 的商品！")
    conn.close()
    engine.dispose()
    sys.exit(1)

sku_ids = tuple(r[0] for r in rows)
print(f"\nSKU ID: {sku_ids}")

# 2. SKU日汇总
print("\n=== 2. SKU日汇总成本数据 ===")
rows = conn.execute(text("""
    SELECT date, sku_id, offer_id,
           revenue, ordered_units, delivered_units, cancelled_units,
           returns_amount, returns_units,
           commissions, logistics_costs, storage_fees, advertising, other_costs,
           net_profit, profit_margin, data_quality
    FROM ozon.sku_daily_summary
    WHERE sku_id IN :sids
    ORDER BY date DESC
"""), {"sids": sku_ids}).fetchall()

for r in rows:
    d = dict(r._mapping)
    print(f"  {d['date']} | 销量={d['ordered_units']} | 收入={d['revenue']} | "
          f"退货={d['returns_amount']}({d['returns_units']}件) | "
          f"佣金={d['commissions']} | 物流={d['logistics_costs']} | "
          f"仓储={d['storage_fees']} | 广告={d['advertising']} | "
          f"其他={d['other_costs']} | 净利={d['net_profit']} | 利润率={d['profit_margin']}%")

if rows:
    total = conn.execute(text("""
        SELECT
            SUM(revenue) as total_revenue,
            SUM(ordered_units) as total_ordered,
            SUM(delivered_units) as total_delivered,
            SUM(cancelled_units) as total_cancelled,
            SUM(returns_amount) as total_returns,
            SUM(returns_units) as total_returns_units,
            SUM(commissions) as total_commissions,
            SUM(logistics_costs) as total_logistics,
            SUM(storage_fees) as total_storage,
            SUM(advertising) as total_advertising,
            SUM(other_costs) as total_other,
            SUM(net_profit) as total_net_profit
        FROM ozon.sku_daily_summary
        WHERE sku_id IN :sids
    """), {"sids": sku_ids}).fetchone()
    d = dict(total._mapping)
    print("\n--- 汇总 ---")
    print(f"  总收入: {d['total_revenue']}")
    print(f"  总下单: {d['total_ordered']} 件 | 总送达: {d['total_delivered']} 件 | 总取消: {d['total_cancelled']} 件")
    print(f"  总退货额: {d['total_returns']} | 总退货件数: {d['total_returns_units']}")
    print(f"  总佣金: {d['total_commissions']}")
    print(f"  总物流费: {d['total_logistics']}")
    print(f"  总仓储费: {d['total_storage']}")
    print(f"  总广告费: {d['total_advertising']}")
    print(f"  总其他费用: {d['total_other']}")
    print(f"  总净利润: {d['total_net_profit']}")
    tc = sum(v or 0 for v in [d['total_commissions'], d['total_logistics'], d['total_storage'],
                               d['total_advertising'], d['total_other'], d['total_returns']])
    print(f"  总成本合计(费用+退货): {tc}")

# 3. 财务流水
print("\n=== 3. 财务流水明细 ===")
rows = conn.execute(text("""
    SELECT operation_date, operation_type, operation_type_name, type,
           amount, accruals_for_sale, sale_commission, delivery_charge,
           return_delivery_charge, posting_number, delivery_schema, item_name
    FROM ozon.finance_transactions
    WHERE sku_id IN :sids
    ORDER BY operation_date DESC
"""), {"sids": sku_ids}).fetchall()

if rows:
    for r in rows:
        d = dict(r._mapping)
        print(f"  {d['operation_date']} | {d['type']} | {d['operation_type']} | "
              f"金额={d['amount']} | 佣金={d['sale_commission']} | "
              f"物流={d['delivery_charge']} | 退货物流={d['return_delivery_charge']} | "
              f"posting={d['posting_number']}")
    total = conn.execute(text("""
        SELECT
            COUNT(*) as cnt,
            SUM(amount) as total_amount,
            SUM(sale_commission) as total_commission,
            SUM(delivery_charge) as total_delivery,
            SUM(return_delivery_charge) as total_return_delivery,
            SUM(accruals_for_sale) as total_accruals
        FROM ozon.finance_transactions
        WHERE sku_id IN :sids
    """), {"sids": sku_ids}).fetchone()
    d = dict(total._mapping)
    print(f"\n--- 财务汇总: {d['cnt']} 条 ---")
    print(f"  总金额: {d['total_amount']} | 总佣金: {d['total_commission']} | "
          f"总物流费: {d['total_delivery']} | 总退货物流: {d['total_return_delivery']} | "
          f"总销售应计: {d['total_accruals']}")
else:
    print("  无财务流水记录")

# 4. 广告SKU日明细
print("\n=== 4. 广告SKU日明细 (ad_sku_daily_stats) ===")
rows = conn.execute(text("""
    SELECT stat_date, campaign_id, sku_name, sku_price,
           impressions, clicks, ctr, avg_cpc, spend,
           sold_units, sales_promotion, total_ordered,
           drr_promotion, drr_total
    FROM ozon.ad_sku_daily_stats
    WHERE sku_id IN :sids
    ORDER BY stat_date DESC
"""), {"sids": sku_ids}).fetchall()

if rows:
    for r in rows:
        d = dict(r._mapping)
        print(f"  {d['stat_date']} | 活动={d['campaign_id']} | 花费={d['spend']} | "
              f"展示={d['impressions']} | 点击={d['clicks']} | CTR={d['ctr']}% | "
              f"CPC={d['avg_cpc']} | 售出={d['sold_units']} | "
              f"推广销售={d['sales_promotion']} | DRR推广={d['drr_promotion']}% | "
              f"DRR总={d['drr_total']}%")
    total = conn.execute(text("""
        SELECT SUM(spend) as ts, SUM(impressions) as ti, SUM(clicks) as tc,
               SUM(sold_units) as tsu, SUM(sales_promotion) as tsp
        FROM ozon.ad_sku_daily_stats WHERE sku_id IN :sids
    """), {"sids": sku_ids}).fetchone()
    d = dict(total._mapping)
    print(f"\n  广告总花费: {d['ts']} | 总展示: {d['ti']} | 总点击: {d['tc']} | "
          f"总售出: {d['tsu']} | 总推广销售: {d['tsp']}")
else:
    print("  无广告SKU明细记录")

# 5. 广告活动日汇总
print("\n=== 5. 广告活动日汇总 (ad_daily_stats) ===")
rows = conn.execute(text("""
    SELECT ads.stat_date, ads.campaign_id, ads.impressions, ads.clicks,
           ads.spend, ads.orders_count, ads.orders_sum
    FROM ozon.ad_daily_stats ads
    JOIN ozon.ad_campaign_sku_map m ON ads.campaign_id = m.campaign_id
    WHERE m.sku_id IN :sids
    ORDER BY ads.stat_date DESC
"""), {"sids": sku_ids}).fetchall()

if rows:
    for r in rows:
        d = dict(r._mapping)
        print(f"  {d['stat_date']} | 活动={d['campaign_id']} | 花费={d['spend']} | "
              f"展示={d['impressions']} | 点击={d['clicks']} | "
              f"订单数={d['orders_count']} | 订单金额={d['orders_sum']}")
    total = conn.execute(text("""
        SELECT SUM(ads.spend) as ts, SUM(ads.orders_sum) as tos
        FROM ozon.ad_daily_stats ads
        JOIN ozon.ad_campaign_sku_map m ON ads.campaign_id = m.campaign_id
        WHERE m.sku_id IN :sids
    """), {"sids": sku_ids}).fetchone()
    d = dict(total._mapping)
    print(f"  活动总花费: {d['ts']} | 总订单金额: {d['tos']}")
else:
    print("  无关联广告活动数据")

# 6. 库存
print("\n=== 6. 库存数据 ===")
rows = conn.execute(text("""
    SELECT sku_id, source, present, reserved, updated_at
    FROM ozon.stocks WHERE sku_id IN :sids
"""), {"sids": sku_ids}).fetchall()
for r in rows:
    print(dict(r._mapping))
if not rows:
    print("  无库存记录")

# 7. Posting数据
print("\n=== 7. 订单履约数据 (postings) ===")
rows = conn.execute(text("""
    SELECT posting_number, order_number, delivery_schema, status,
           cancel_reason_id, created_at, in_process_at, delivered_at
    FROM ozon.postings
    WHERE posting_number IN (
        SELECT DISTINCT posting_number
        FROM ozon.finance_transactions
        WHERE sku_id IN :sids AND posting_number IS NOT NULL
    )
    ORDER BY created_at DESC
"""), {"sids": sku_ids}).fetchall()

if rows:
    for r in rows:
        d = dict(r._mapping)
        print(f"  {d['posting_number']} | 状态={d['status']} | 创建={d['created_at']} | "
              f"送达={d['delivered_at']} | delivery={d['delivery_schema']}")
    print(f"  共 {len(rows)} 条 posting 记录")
else:
    print("  无关联 posting 记录")

conn.close()
engine.dispose()
