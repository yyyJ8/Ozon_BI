"""验证新公式：实际头程费用/产品成本/头程占比/实际回款"""
import sys
sys.path.insert(0, r"D:\OzonSku")
from app.services.sku_formulas import compute_formulas

# 典型输入（模拟一个 SKU）
inputs = {
    # 尺寸
    "length_cm": 60, "width_cm": 40, "height_cm": 30,
    "actual_weight_kg": 10,          # 实重
    "units_per_carton": 5,           # 装箱数
    "carton_length_cm": 40, "carton_width_cm": 30, "carton_height_cm": 20,
    "first_leg_unit_price": 2,       # 头程单价
    "purchase_cost_rmb": 100,        # 采购成本
    # 费率（小数）
    "acquiring_fee_pct": 0.02,
    "fbo_commission_pct": 0.19,
    "delivery_pickup_rub": 46,
    "advertising_rate_pct": 0.10,
    "return_rate_pct": 0.05,
    "exchange_rate": 13,             # 汇率
    "green_price_rub": 3041,         # 绿标价
}
price = 3650.0  # 售价

r = compute_formulas(inputs, price)

# ── 需求 2：实际头程费用 = 实重 × 头程单价 × 7 ÷ 装箱数 = 10×2×7/5 = 28 ──
z = r["first_leg_cost_rmb"]
assert z == 28.0, f"实际头程费用={z}, 期望 28"
print(f"✅ 实际头程费用 first_leg_cost_rmb = {z}  (10×2×7÷5=28)")

# ── 需求 3：产品成本 = 采购成本 + 送仓费 + 实际头程费用×1.06
# 送仓费: 升=40×30×20/1000=24 → 24<40 → 15
# = 100 + 15 + 28×1.06 = 100+15+29.68 = 144.68 ──
ai = r["product_cost_rmb"]
assert abs(ai - 144.68) < 0.001, f"产品成本={ai}, 期望 144.68"
print(f"✅ 产品成本 product_cost_rmb = {ai}  (100 + 15 + 28×1.06=144.68)")

# ── 需求 4：头程占比 = 实际头程费用×1.06×汇率÷售价 ×100
# = 28×1.06×13/3650×100 = 385.84/3650×100 = 10.57 ──
aa = r["first_leg_pct"]
expect_aa = round(28 * 1.06 * 13 / 3650 * 100, 2)
assert abs(aa - expect_aa) < 0.001, f"头程占比={aa}, 期望 {expect_aa}"
print(f"✅ 头程占比 first_leg_pct = {aa}%  (28×1.06×13÷3650×100={expect_aa}%)")

# ── 需求 5：实际回款 = 平台打款 - 售价×1% - (平台打款 - 实际头程费用×1.06×汇率)×11%
an = r["platform_payout_rub"]  # 平台打款 = 3650×(1-0.137-0.10-0.05-0.19)
expect_ao = round(an - 3650*0.01 - (an - 28*1.06*13) * 0.11, 2)
ao = r["actual_payout_rub"]
assert abs(ao - expect_ao) < 0.001, f"实际回款={ao}, 期望 {expect_ao}"
print(f"✅ 实际回款 actual_payout_rub = {ao}  (平台打款={an}, 手算={expect_ao})")

# 连带字段完整性
for k in ("profit_rmb", "profit_rub", "profit_margin_pct", "target_price_3pct", "tax_and_fee_pct"):
    print(f"   连带 {k} = {r[k]}")

print("\n✅✅ 全部新公式验证通过")
