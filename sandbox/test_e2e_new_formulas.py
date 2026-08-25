"""端到端验证：真实 SKU 数据下新公式在 batch_update 链路中正确计算（回滚事务）"""
import sys
sys.path.insert(0, r"D:\OzonSku")

from unittest.mock import patch

from app.api.sku_management import batch_update
from app.database import SessionLocal
from app.models import Product, SkuManagement
from app.schemas.sku_management import SkuManagementUpdate, SkuManagementBatchUpdate
from app.services.sku_formulas import INPUT_FIELDS, compute_formulas

SKU = 5376335343
STORE = 5

db = SessionLocal()
try:
    prod = db.query(Product).filter_by(store_id=STORE, sku_id=SKU).first()
    assert prod, "SKU 不存在"
    mgmt = db.query(SkuManagement).filter_by(store_id=STORE, sku_id=SKU).first()
    assert mgmt, "无 sku_management 记录"

    # 真实输入（复用现有值，只触发一次保存）
    real_inputs = {f: getattr(mgmt, f, None) for f in INPUT_FIELDS}
    price = float(prod.marketing_seller_price)
    real_inputs["fbo_commission_pct"] = float(prod.commission_fbo_pct) if prod.commission_fbo_pct else None
    print(f"售价={price}  实重={real_inputs.get('actual_weight_kg')}  装箱数={real_inputs.get('units_per_carton')}  头程单价={real_inputs.get('first_leg_unit_price')}  采购成本={real_inputs.get('purchase_cost_rmb')}  汇率={real_inputs.get('exchange_rate')}")

    # 手动按新公式计算
    from app.services.sku_formulas import _f
    W = _f(real_inputs.get("actual_weight_kg"))
    O = _f(real_inputs.get("first_leg_unit_price"))
    P = _f(real_inputs.get("units_per_carton"))
    V = _f(real_inputs.get("purchase_cost_rmb"))
    AJ = _f(real_inputs.get("exchange_rate"))
    # 升 → 送仓费
    Q, R, S = _f(real_inputs.get("carton_length_cm")), _f(real_inputs.get("carton_width_cm")), _f(real_inputs.get("carton_height_cm"))
    U = Q * R * S / 1000 if Q and R and S else None
    Y = 5.0 if (U is not None and U < 10) else 10.0 if (U is not None and U <= 20) else 15.0 if (U is not None and U < 40) else 20.0 if U is not None else None
    Z = round(W * (O * 7) / P, 2) if W is not None and O is not None and P and P != 0 else None
    AI = round(V + Y + Z * 1.06, 2) if V is not None and Y is not None and Z is not None else None
    AA = round(Z * 1.06 * AJ / price * 100, 2) if Z is not None and AJ is not None else None
    print(f"手算: 实际头程费用Z={Z}  送仓费Y={Y}  产品成本AI={AI}  头程占比AA={AA}")

    # 调用 batch_update（store=5，改绿标价触发重算；mock commit 后 rollback）
    payload = SkuManagementBatchUpdate(items=[SkuManagementUpdate(sku_id=SKU, green_price_rub=3041.0)])
    with patch.object(db, "commit", lambda: None):
        result = batch_update(payload, store_id=STORE, db=db)
    row = next(r for r in result if r.sku_id == SKU)
    print(f"接口返回: 实际头程费用={row.first_leg_cost_rmb}  产品成本={row.product_cost_rmb}  头程占比={row.first_leg_pct}  实际回款={row.actual_payout_rub}")

    assert row.first_leg_cost_rmb == Z, "实际头程费用不一致"
    assert row.product_cost_rmb == AI, "产品成本不一致"
    assert row.first_leg_pct == AA, "头程占比不一致"
    # 实际回款：用返回的平台打款手动核验
    an = row.platform_payout_rub
    expect_ao = round(an - price * 0.01 - (an - Z * 1.06 * AJ) * 0.11, 2) if an is not None and Z is not None and AJ is not None else None
    assert row.actual_payout_rub == expect_ao, f"实际回款不一致: {row.actual_payout_rub} vs {expect_ao}"
    print(f"✅ 端到端一致：实际回款={row.actual_payout_rub}（手算={expect_ao}）")
    print("\n✅✅ 端到端验证通过")
finally:
    db.rollback()
    db.close()
    print("（已回滚，未改动真实数据）")
