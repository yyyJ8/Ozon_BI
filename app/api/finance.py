"""财务流水 API"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FinanceTransaction
from app.schemas.finance import FinanceTransactionItem

# Ozon 操作类型俄→中映射
OPERATION_TYPE_MAP: dict[str, str] = {
    "OperationAgentDeliveredToCustomer": "订单配送完成",
    "OperationCreateReturn": "创建退货",
    "OperationGoodsReturned": "商品退货",
    "OperationWriteOffFromFboStorage": "FBO 仓储扣费",
    "OperationMovingToFboWarehouseService": "FBO 入库服务费",
    "OperationFboOutfitService": "FBO 拣货打包费",
    "OperationRecomendation": "广告费",
    "OperationAcquiring": "支付手续费",
    "OperationDeliveryToCustomer": "物流配送费",
    "OperationRepacking": "重新包装费",
    "OperationWriteOffFromFbs": "FBS 扣费",
    "OperationAgentNotDelivered": "配送失败",
    "OperationAgentPartiallyDelivered": "部分配送",
    "OperationReturnDelivery": "退货物流费",
    "OperationCorrection": "调账",
    "OperationPenalty": "罚款",
    "OperationAgentDeliveredToCustomer": "订单配送完成",
    "OperationAgentSale": "代理销售",
}

# 补充按关键词匹配的映射（当 code 没命中时，用俄文名关键词匹配）
KEYWORD_MAP: dict[str, str] = {
    "доставка покупател": "订单配送完成",
    "оплата эквайринг": "支付手续费",
    "возврат товар": "商品退货",
    "возврат": "退货",
    "услуги склад": "仓储服务费",
    "стоимость доставк": "物流运费",
    "реклам": "广告费",
    "штраф": "罚款",
    "акци": "营销活动费",
    "упаковк": "包装费",
    "маркировк": "标签费",
    "комиссия": "佣金",
    "сборк": "拣货费",
    "хранени": "仓储费",
    "доставка до склад": "入仓物流费",
}


def translate_operation_type(transaction: FinanceTransaction) -> str:
    """翻译操作类型：优先用 code 映射，再用俄文关键词匹配，兜底保留原文"""
    # 1. 按 code 精确匹配
    if transaction.operation_type and transaction.operation_type in OPERATION_TYPE_MAP:
        return OPERATION_TYPE_MAP[transaction.operation_type]

    # 2. 按俄文名关键词匹配
    if transaction.operation_type_name:
        name_lower = transaction.operation_type_name.lower()
        for keyword, cn in KEYWORD_MAP.items():
            if keyword in name_lower:
                return cn

    # 3. 兜底
    return transaction.operation_type_name or "未知操作"


router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/transactions", response_model=list[FinanceTransactionItem])
def list_transactions(
    sku_id: int = Query(..., description="SKU 编号"),
    date: date = Query(..., description="日期"),
    db: Session = Depends(get_db),
):
    """查询指定 SKU 在指定日期的所有财务流水"""
    rows = db.query(FinanceTransaction).filter(
        FinanceTransaction.sku_id == sku_id,
        FinanceTransaction.operation_date == date,
    ).order_by(
        FinanceTransaction.operation_id,
    ).all()

    # 翻译操作类型
    for tx in rows:
        tx.operation_type_name = translate_operation_type(tx)

    return rows
