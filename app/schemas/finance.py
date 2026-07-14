"""财务流水响应模型"""
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FinanceTransactionItem(BaseModel):
    """单笔财务流水"""
    model_config = ConfigDict(from_attributes=True, ser_json_decimal='number')

    operation_id: int
    operation_type_name: Optional[str] = None
    type: Optional[str] = None
    operation_date: date
    posting_number: Optional[str] = None
    delivery_schema: Optional[str] = None
    amount: Decimal = Decimal("0")
    accruals_for_sale: Decimal = Decimal("0")
    sale_commission: Decimal = Decimal("0")
    delivery_charge: Decimal = Decimal("0")
    return_delivery_charge: Decimal = Decimal("0")
