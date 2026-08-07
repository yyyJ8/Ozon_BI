"""SKU 公式引擎 — 从输入字段自动计算派生字段

所有公式来源于 Excel "SKU管理带公式版本" 中的公式列。
输入字段 = 用户手动填写，计算字段 = 公式自动推导。
"""

import math
from typing import Any, Optional

# ── 字段分类 ──────────────────────────────────────────────

# 用户可编辑的输入字段（会出现在编辑弹窗中）
INPUT_FIELDS = [
    # 基本信息
    "main_sku", "source_url_1688", "specification", "sales_manager",
    "listed_stores", "product_status", "key_notes",
    # 外箱尺寸重量
    "length_cm", "width_cm", "height_cm", "actual_weight_kg",
    # 头程 & 装箱
    "first_leg_unit_price", "units_per_carton",
    # 内盒尺寸重量
    "carton_length_cm", "carton_width_cm", "carton_height_cm", "gross_weight_kg",
    # 成本
    "purchase_cost_rmb", "purchase_cost_pct",
    # 平台费率 (百分比以小数存储，如 0.02 = 2%)
    "acquiring_fee_pct", "fbo_commission_pct",
    "delivery_pickup_rub", "advertising_rate_pct", "return_rate_pct",
    # 财务
    "product_cost_rmb", "exchange_rate", "green_price_rub",
    # 竞品
    "competitor_1", "competitor_2", "competitor_sales",
]

# 公式自动计算的字段（不在编辑弹窗中出现）
COMPUTED_FIELDS = [
    "volume_cbm",          # 外箱体积
    "density",             # 密度
    "volume_liters",       # 升
    "warehousing_fee_rmb", # 入库费
    "fbo_delivery_fee_rmb",# FBO送仓费
    "first_leg_cost_rmb",  # 头程费用
    "logistics_rub",       # 物流₽
    "first_leg_pct",       # 头程占比
    "last_mile_pct",       # 尾程运费占比
    "discount_pct",        # 折扣比例
    "platform_payout_rub", # 平台打款
    "actual_payout_rub",   # 实际回款
    "tax_and_fee_pct",     # 税点+手续费占比
    "risk_reserve_rub",    # 风险储备金
    "profit_rmb",          # 利润RMB
    "profit_rub",          # 利润₽
    "profit_margin_pct",   # 利润率
]


# ── 辅助函数 ──────────────────────────────────────────────

def _f(v: Any) -> Optional[float]:
    """将值转为 float，None 保持 None"""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    """安全除法，任一为 None 或除数为 0 返回 None"""
    if a is None or b is None or b == 0:
        return None
    return a / b


# ── 公式计算 ──────────────────────────────────────────────

def compute_formulas(
    inputs: dict,
    price: Optional[float] = None,
) -> dict:
    """给定输入字段和售价，返回所有计算字段的值。

    Args:
        inputs: 用户输入的字段 dict，键为字段名，值为字段值
        price: 产品售价（₽），来自 products 表，用于多个公式

    Returns:
        dict: 所有 COMPUTED_FIELDS 的计算结果
    """
    # 提取输入值
    L = _f(inputs.get("length_cm"))        # noqa: E741  外箱长
    W = _f(inputs.get("width_cm"))          # 外箱宽
    H_cm = _f(inputs.get("height_cm"))      # 外箱高
    W_kg = _f(inputs.get("actual_weight_kg"))  # 外箱实重

    O = _f(inputs.get("first_leg_unit_price"))  # 头程单价
    P = _f(inputs.get("units_per_carton"))       # 装箱数

    Q = _f(inputs.get("carton_length_cm"))  # 内盒长
    R = _f(inputs.get("carton_width_cm"))   # 内盒宽
    S = _f(inputs.get("carton_height_cm"))  # 内盒高

    # 费率百分比（以小数存储，如 0.02 = 2%）
    AB = _f(inputs.get("acquiring_fee_pct"))      # 收单业务
    AC = _f(inputs.get("fbo_commission_pct"))     # FBO佣金
    AE = _f(inputs.get("delivery_pickup_rub"))    # 配送至取货点₽
    AG = _f(inputs.get("advertising_rate_pct"))   # 广告费率
    AH = _f(inputs.get("return_rate_pct"))        # 退货率

    AI = _f(inputs.get("product_cost_rmb"))       # 产品成本RMB
    AJ = _f(inputs.get("exchange_rate"))          # 汇率
    AL = _f(inputs.get("green_price_rub"))        # 绿标价格

    AK = _f(price)  # 售价

    result: dict = {}

    # --- Step 1: 外箱体积 (M) = I*J*K / 1,000,000 ---
    M = None
    if L is not None and W is not None and H_cm is not None:
        M = L * W * H_cm / 1_000_000
        M = round(M, 6)
    result["volume_cbm"] = M

    # --- Step 2: 密度 (N) = L / M ---
    result["density"] = round(_safe_div(W_kg, M), 2) if _safe_div(W_kg, M) is not None else None

    # --- Step 3: 升 (U) = Q*R*S / 1000 ---
    U = None
    if Q is not None and R is not None and S is not None:
        U = Q * R * S / 1000
        U = round(U, 2)
    result["volume_liters"] = U

    # --- Step 4: 入库费 (X) = L*3 / P ---
    X = None
    if W_kg is not None and P is not None and P != 0:
        X = W_kg * 3 / P
        X = round(X, 2)
    result["warehousing_fee_rmb"] = X

    # --- Step 5: FBO送仓费 (Y) = IF(U<10,5,IF(U<=20,10,IF(U<40,15,20))) ---
    Y = None
    if U is not None:
        if U < 10:
            Y = 5.0
        elif U <= 20:
            Y = 10.0
        elif U < 40:
            Y = 15.0
        else:
            Y = 20.0
    result["fbo_delivery_fee_rmb"] = Y

    # --- Step 6: 头程费用 (Z) = L*(O*7)/P + X + Y ---
    Z = None
    if W_kg is not None and O is not None and P is not None and P != 0 and X is not None and Y is not None:
        Z = W_kg * (O * 7) / P + X + Y
        Z = round(Z, 2)
    result["first_leg_cost_rmb"] = Z

    # --- Step 7: 物流₽ (AD) = tiered IF on U ---
    AD = None
    if U is not None:
        if U < 1:
            AD = 46.0
        elif 1 <= U < 2:
            AD = 56.0
        elif 2 <= U < 3:
            AD = 66.0
        else:
            AD = math.ceil(U - 3) * 15 + 66
        AD = float(AD)
    result["logistics_rub"] = AD

    # --- Step 8: 头程占比 (AA) = Z*AJ / AK ---
    result["first_leg_pct"] = round(_safe_div(Z * AJ, AK), 4) if Z is not None and AJ is not None and AK is not None else None

    # --- Step 9: 尾程运费占比 (AF) = (AD+AE)/AK + AB ---
    AF = None
    if AD is not None and AE is not None and AK is not None and AK != 0 and AB is not None:
        AF = (AD + AE) / AK + AB
        AF = round(AF, 4)
    result["last_mile_pct"] = AF

    # --- Step 10: 折扣比例 (AM) = 1 - AL/AK ---
    result["discount_pct"] = round(1 - _safe_div(AL, AK), 4) if AL is not None and AK is not None and AK != 0 else None

    # --- Step 11: 平台打款 (AN) = AK * (1 - AF - AG - AH - AC) ---
    AN = None
    if AK is not None and AF is not None and AG is not None and AH is not None and AC is not None:
        AN = AK * (1 - AF - AG - AH - AC)
        AN = round(AN, 2)
    result["platform_payout_rub"] = AN

    # --- Step 12: 实际回款 (AO) = AN - (AK*0.02 + AN*0.08) ---
    AO = None
    if AN is not None and AK is not None:
        AO = AN - (AK * 0.02 + AN * 0.08)
        AO = round(AO, 2)
    result["actual_payout_rub"] = AO

    # --- Step 13: 税点+手续费占比 (AP) = (AN - AO) / AK ---
    result["tax_and_fee_pct"] = round(_safe_div(AN - AO, AK), 4) if AN is not None and AO is not None and AK is not None else None

    # --- Step 14: 风险储备金 (AQ) = AK * 1% ---
    result["risk_reserve_rub"] = round(AK * 0.01, 2) if AK is not None else None

    # --- Step 15: 利润RMB (AR) = (AO - AQ) / AJ - AI ---
    AQ = result["risk_reserve_rub"]
    AR = None
    if AO is not None and AQ is not None and AJ is not None and AJ != 0 and AI is not None:
        AR = (AO - AQ) / AJ - AI
        AR = round(AR, 2)
    result["profit_rmb"] = AR

    # --- Step 16: 利润₽ (AS) = AR * AJ ---
    result["profit_rub"] = round(AR * AJ, 2) if AR is not None and AJ is not None else None

    # --- Step 17: 利润率 (AT) = AS / AK ---
    AS = result["profit_rub"]
    result["profit_margin_pct"] = round(_safe_div(AS, AK), 4) if AS is not None and AK is not None else None

    return result
