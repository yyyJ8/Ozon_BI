"""SKU management schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SkuManagementItem(BaseModel):
    """SKU management response model"""
    store_id: int
    sku_id: int

    main_sku: Optional[str] = None
    source_url_1688: Optional[str] = None
    specification: Optional[str] = None
    sales_manager: Optional[str] = None
    listed_stores: Optional[str] = None
    product_status: Optional[str] = None
    key_notes: Optional[str] = None

    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    actual_weight_kg: Optional[float] = None
    volume_cbm: Optional[float] = None
    density: Optional[float] = None

    first_leg_unit_price: Optional[float] = None
    units_per_carton: Optional[int] = None
    carton_length_cm: Optional[float] = None
    carton_width_cm: Optional[float] = None
    carton_height_cm: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    volume_liters: Optional[float] = None

    purchase_cost_rmb: Optional[float] = None
    warehousing_fee_rmb: Optional[float] = None
    fbo_delivery_fee_rmb: Optional[float] = None
    first_leg_cost_rmb: Optional[float] = None

    acquiring_fee_pct: Optional[float] = None
    fbo_commission_pct: Optional[float] = None
    logistics_rub: Optional[float] = None
    delivery_pickup_rub: Optional[float] = None
    advertising_rate_pct: Optional[float] = None
    return_rate_pct: Optional[float] = None
    tax_and_fee_pct: Optional[float] = None
    risk_reserve_rub: Optional[float] = None

    exchange_rate: Optional[float] = None
    green_price_rub: Optional[float] = None

    competitor_1: Optional[str] = None
    competitor_2: Optional[str] = None
    competitor_sales: Optional[int] = None

    purchase_cost_pct: Optional[float] = None
    first_leg_pct: Optional[float] = None
    last_mile_pct: Optional[float] = None
    product_cost_rmb: Optional[float] = None
    discount_pct: Optional[float] = None
    platform_payout_rub: Optional[float] = None
    actual_payout_rub: Optional[float] = None
    profit_rmb: Optional[float] = None
    profit_rub: Optional[float] = None
    profit_margin_pct: Optional[float] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    name: Optional[str] = None
    offer_id: Optional[str] = None
    primary_image: Optional[str] = None
    category_name: Optional[str] = None
    price: Optional[float] = None
    stock_present: Optional[int] = None

    model_config = {"from_attributes": True}


class SkuManagementUpdate(BaseModel):
    """Single row update"""
    sku_id: int

    main_sku: Optional[str] = None
    source_url_1688: Optional[str] = None
    specification: Optional[str] = None
    sales_manager: Optional[str] = None
    listed_stores: Optional[str] = None
    product_status: Optional[str] = None
    key_notes: Optional[str] = None

    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    actual_weight_kg: Optional[float] = None
    volume_cbm: Optional[float] = None
    density: Optional[float] = None

    first_leg_unit_price: Optional[float] = None
    units_per_carton: Optional[int] = None
    carton_length_cm: Optional[float] = None
    carton_width_cm: Optional[float] = None
    carton_height_cm: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    volume_liters: Optional[float] = None

    purchase_cost_rmb: Optional[float] = None
    warehousing_fee_rmb: Optional[float] = None
    fbo_delivery_fee_rmb: Optional[float] = None
    first_leg_cost_rmb: Optional[float] = None

    acquiring_fee_pct: Optional[float] = None
    fbo_commission_pct: Optional[float] = None
    logistics_rub: Optional[float] = None
    delivery_pickup_rub: Optional[float] = None
    advertising_rate_pct: Optional[float] = None
    return_rate_pct: Optional[float] = None
    tax_and_fee_pct: Optional[float] = None
    risk_reserve_rub: Optional[float] = None

    exchange_rate: Optional[float] = None
    green_price_rub: Optional[float] = None

    competitor_1: Optional[str] = None
    competitor_2: Optional[str] = None
    competitor_sales: Optional[int] = None

    purchase_cost_pct: Optional[float] = None
    first_leg_pct: Optional[float] = None
    last_mile_pct: Optional[float] = None
    product_cost_rmb: Optional[float] = None
    discount_pct: Optional[float] = None
    platform_payout_rub: Optional[float] = None
    actual_payout_rub: Optional[float] = None
    profit_rmb: Optional[float] = None
    profit_rub: Optional[float] = None
    profit_margin_pct: Optional[float] = None


class SkuManagementBatchUpdate(BaseModel):
    """Batch update request"""
    items: list[SkuManagementUpdate]
