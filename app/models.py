"""
SQLAlchemy ORM 模型 — 5 张表

对应 plan/OzonBI-Database-Design.md v1.2
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON, BigInteger, Boolean, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    """商品主数据 — 来源 /v3/product/info/list"""
    __tablename__ = "products"
    __table_args__ = {"schema": "ozon"}

    sku_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(Text)
    offer_id: Mapped[Optional[str]] = mapped_column(String(255))
    category_id: Mapped[Optional[int]] = mapped_column(Integer)
    barcode: Mapped[Optional[str]] = mapped_column(String(255))
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    old_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    min_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    commission_fbo_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    volume_weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    status: Mapped[Optional[str]] = mapped_column(String(50))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    images: Mapped[Optional[dict]] = mapped_column(JSON)
    primary_image: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    stocks = relationship("Stock", back_populates="product", lazy="selectin")


class Stock(Base):
    """库存明细 — 来源 /v3/product/info/list → stocks.stocks[]"""
    __tablename__ = "stocks"
    __table_args__ = (
        UniqueConstraint("sku_id", "source"),
        {"schema": "ozon"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sku_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ozon.products.sku_id"), nullable=False)
    present: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    product = relationship("Product", back_populates="stocks")


class SkuDailySummary(Base):
    """SKU 日汇总（核心看板表）— 通过同步服务聚合构建"""
    __tablename__ = "sku_daily_summary"
    __table_args__ = (
        UniqueConstraint("date", "sku_id"),
        {"schema": "ozon"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    record_date: Mapped[date] = mapped_column("date", Date, nullable=False)
    sku_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    offer_id: Mapped[Optional[str]] = mapped_column(String(255))

    # 销售指标（来源：analytics API）
    ordered_units: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    # 财务指标（来源：finance API，按 sku + date 聚合）
    returns_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    commissions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    logistics_costs: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    storage_fees: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    advertising: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    other_costs: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    net_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    profit_margin: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)

    # 元数据
    data_quality: Mapped[str] = mapped_column(String(20), default="partial")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class FinanceTransaction(Base):
    """财务流水原始数据 — 来源 /v3/finance/transaction/list"""
    __tablename__ = "finance_transactions"
    __table_args__ = {"schema": "ozon"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    operation_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True)
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    operation_type_name: Mapped[Optional[str]] = mapped_column(Text)
    type: Mapped[Optional[str]] = mapped_column(String(20))  # orders / returns / other
    operation_date: Mapped[date] = mapped_column(Date, nullable=False)
    sku_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    item_name: Mapped[Optional[str]] = mapped_column(Text)
    posting_number: Mapped[Optional[str]] = mapped_column(String(255))
    delivery_schema: Mapped[Optional[str]] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    accruals_for_sale: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    sale_commission: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    delivery_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    return_delivery_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    services: Mapped[Optional[dict]] = mapped_column(JSON)
    items: Mapped[Optional[dict]] = mapped_column(JSON)
    sync_batch_id: Mapped[Optional[str]] = mapped_column(String(100))
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class SyncLog(Base):
    """同步审计日志"""
    __tablename__ = "sync_log"
    __table_args__ = {"schema": "ozon"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sync_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    date_from: Mapped[Optional[date]] = mapped_column(Date)
    date_to: Mapped[Optional[date]] = mapped_column(Date)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    batch_id: Mapped[Optional[str]] = mapped_column(String(100))
