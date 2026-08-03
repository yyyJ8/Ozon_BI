"""OZON 直发信息 — 响应模型"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ============================================================
# SKU 基础数据
# ============================================================

class DirectSkuItem(BaseModel):
    """SKU 列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    product_name: Optional[str] = None
    supplier: Optional[str] = None
    store_name: Optional[str] = None
    label_file: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DirectSkuCreate(BaseModel):
    """新增 SKU"""
    sku: str
    product_name: Optional[str] = None
    supplier: Optional[str] = None
    store_name: Optional[str] = None
    label_file: Optional[str] = None


class DirectSkuUpdate(BaseModel):
    """更新 SKU — 所有字段可选"""
    sku: Optional[str] = None
    product_name: Optional[str] = None
    supplier: Optional[str] = None
    store_name: Optional[str] = None
    label_file: Optional[str] = None


# ============================================================
# 直发跟进表
# ============================================================

class DirectShipmentItem(BaseModel):
    """发货记录列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    pr_no: Optional[str] = None
    sku: Optional[str] = None
    product_cn_name: Optional[str] = None
    pr_date: Optional[date] = None
    pr_person: Optional[str] = None
    supplier: Optional[str] = None
    po_no: Optional[str] = None
    online_po_no: Optional[str] = None
    is_received: Optional[str] = None
    total_qty: Optional[int] = None
    total_boxes: Optional[int] = None
    product_label: Optional[str] = None
    carton_mark: Optional[str] = None
    warehouse_receipt: Optional[str] = None
    receiving_address: Optional[str] = None
    labeling_notes: Optional[str] = None
    logistics_provider: Optional[str] = None
    first_leg_tracking: Optional[str] = None
    total_boxes_2: Optional[int] = None
    length_cm: Optional[Decimal] = None
    width_cm: Optional[Decimal] = None
    height_cm: Optional[Decimal] = None
    gross_weight: Optional[Decimal] = None
    total_cbm: Optional[Decimal] = None
    density: Optional[Decimal] = None
    plan_no: Optional[str] = None
    ship_date: Optional[date] = None
    tracking_no: Optional[str] = None
    logistics_company: Optional[str] = None
    special_notes: Optional[str] = None
    previous_aftersales: Optional[str] = None
    qty_total_2: Optional[int] = None
    receiving_status: Optional[str] = None
    shipment_no: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DirectShipmentCreate(BaseModel):
    """新增发货记录"""
    pr_no: Optional[str] = None
    sku: Optional[str] = None
    product_cn_name: Optional[str] = None
    pr_date: Optional[date] = None
    pr_person: Optional[str] = None
    supplier: Optional[str] = None
    po_no: Optional[str] = None
    online_po_no: Optional[str] = None
    is_received: Optional[str] = None
    total_qty: Optional[int] = None
    total_boxes: Optional[int] = None
    product_label: Optional[str] = None
    carton_mark: Optional[str] = None
    warehouse_receipt: Optional[str] = None
    receiving_address: Optional[str] = None
    labeling_notes: Optional[str] = None
    logistics_provider: Optional[str] = None
    first_leg_tracking: Optional[str] = None
    total_boxes_2: Optional[int] = None
    length_cm: Optional[Decimal] = None
    width_cm: Optional[Decimal] = None
    height_cm: Optional[Decimal] = None
    gross_weight: Optional[Decimal] = None
    total_cbm: Optional[Decimal] = None
    density: Optional[Decimal] = None
    plan_no: Optional[str] = None
    ship_date: Optional[date] = None
    tracking_no: Optional[str] = None
    logistics_company: Optional[str] = None
    special_notes: Optional[str] = None
    previous_aftersales: Optional[str] = None
    qty_total_2: Optional[int] = None
    receiving_status: Optional[str] = None
    shipment_no: Optional[str] = None


class DirectShipmentUpdate(BaseModel):
    """更新发货记录 — 所有字段可选"""
    pr_no: Optional[str] = None
    sku: Optional[str] = None
    product_cn_name: Optional[str] = None
    pr_date: Optional[date] = None
    pr_person: Optional[str] = None
    supplier: Optional[str] = None
    po_no: Optional[str] = None
    online_po_no: Optional[str] = None
    is_received: Optional[str] = None
    total_qty: Optional[int] = None
    total_boxes: Optional[int] = None
    product_label: Optional[str] = None
    carton_mark: Optional[str] = None
    warehouse_receipt: Optional[str] = None
    receiving_address: Optional[str] = None
    labeling_notes: Optional[str] = None
    logistics_provider: Optional[str] = None
    first_leg_tracking: Optional[str] = None
    total_boxes_2: Optional[int] = None
    length_cm: Optional[Decimal] = None
    width_cm: Optional[Decimal] = None
    height_cm: Optional[Decimal] = None
    gross_weight: Optional[Decimal] = None
    total_cbm: Optional[Decimal] = None
    density: Optional[Decimal] = None
    plan_no: Optional[str] = None
    ship_date: Optional[date] = None
    tracking_no: Optional[str] = None
    logistics_company: Optional[str] = None
    special_notes: Optional[str] = None
    previous_aftersales: Optional[str] = None
    qty_total_2: Optional[int] = None
    receiving_status: Optional[str] = None
    shipment_no: Optional[str] = None


# ============================================================
# 文件
# ============================================================

class DirectFileItem(BaseModel):
    """文件信息（不含二进制内容）"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_table: str
    source_id: int
    file_name: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    uploaded_at: Optional[datetime] = None


# ============================================================
# 分页响应
# ============================================================

class PaginatedResponse(BaseModel):
    """分页响应"""
    items: list
    total: int
    page: int
    page_size: int
