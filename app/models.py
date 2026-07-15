"""
SQLAlchemy ORM 模型 — 5 张表，每字段带中文注释

主键设计：
  products, stocks, sku_daily_summary, finance_transactions
     → 自然主键（业务上就是唯一的）
  sync_log → 自增 id（纯审计，顺序递增更直观）

运行 scripts/reset_db.py 可重建表结构
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON, BigInteger, Boolean, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    """商品主数据 — 来源 /v3/product/info/list"""
    __tablename__ = "products"
    __table_args__ = {"schema": "ozon"}

    sku_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="SKU 编号（Ozon 唯一标识）")
    product_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="商品 ID（Ozon 内部编号）")
    name: Mapped[Optional[str]] = mapped_column(Text, comment="商品名称")
    offer_id: Mapped[Optional[str]] = mapped_column(String(255), comment="商家自定义商品编码")
    category_id: Mapped[Optional[int]] = mapped_column(Integer, comment="类目 ID")
    barcode: Mapped[Optional[str]] = mapped_column(String(255), comment="条形码")
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="当前售价（RUB）")
    old_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="原价/划线价（RUB）")
    min_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="最低允许售价（RUB）")
    commission_fbo_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="FBO 佣金比例（如 0.12 = 12%）")
    volume_weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), comment="体积重（kg）")
    status: Mapped[Optional[str]] = mapped_column(String(50), comment="商品状态，如 created/moderated/approved")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已归档")
    images: Mapped[Optional[dict]] = mapped_column(JSON, comment="图片列表（JSON，含 200x200/400x400 URL）")
    primary_image: Mapped[Optional[str]] = mapped_column(Text, comment="主图 URL")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="记录创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="记录更新时间")

    stocks = relationship("Stock", back_populates="product", lazy="selectin")


class Stock(Base):
    """库存明细 — 来源 /v3/product/info/list -> stocks.stocks[]"""
    __tablename__ = "stocks"
    __table_args__ = {"schema": "ozon"}

    sku_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ozon.products.sku_id"), primary_key=True, comment="SKU 编号，关联 products.sku_id")
    source: Mapped[str] = mapped_column(String(20), primary_key=True, comment="库存来源，如 fbo / fbs")
    present: Mapped[int] = mapped_column(Integer, default=0, comment="当前库存量")
    reserved: Mapped[int] = mapped_column(Integer, default=0, comment="已预留库存量（订单占用）")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="记录更新时间")

    product = relationship("Product", back_populates="stocks")


class SkuDailySummary(Base):
    """SKU 日汇总（核心看板表）— 通过同步服务聚合构建"""
    __tablename__ = "sku_daily_summary"
    __table_args__ = {"schema": "ozon"}

    record_date: Mapped[date] = mapped_column("date", Date, primary_key=True, comment="日期（YYYY-MM-DD）")
    sku_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="SKU 编号")
    offer_id: Mapped[Optional[str]] = mapped_column(String(255), comment="商家自定义商品编码")

    # 销售指标（来源：analytics API）
    ordered_units: Mapped[int] = mapped_column(Integer, default=0, comment="下单件数（analytics API）")
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="销售收入 RUB（analytics API）")

    # 库存快照（来源：stocks 表，同步时快照）
    stock_present: Mapped[int] = mapped_column(Integer, default=0, comment="现有库存件数")
    stock_reserved: Mapped[int] = mapped_column(Integer, default=0, comment="已预留件数")

    # 财务指标（来源：finance API，按 sku + date 聚合）
    returns_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="退货退款金额 RUB（负数）")
    commissions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="佣金总额 RUB（负数）")
    logistics_costs: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="物流费 RUB（负数）")
    storage_fees: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="仓储费 RUB（负数）")
    advertising: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="广告费 RUB（负数）")
    other_costs: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="其他费用 RUB（负数，银行手续费/包装/销毁等）")
    net_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="净利润 RUB = revenue + 各项费用")
    profit_margin: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0, comment="净利润率 % = net_profit / revenue * 100")

    # 元数据
    data_quality: Mapped[str] = mapped_column(String(20), default="partial", comment="数据质量: partial(仅有销售) / complete(含财务)")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="最后同步时间")


class FinanceTransaction(Base):
    """财务流水原始数据 — 来源 /v3/finance/transaction/list"""
    __tablename__ = "finance_transactions"
    __table_args__ = {"schema": "ozon"}

    operation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="操作 ID（Ozon 唯一标识）")
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False, comment="操作类型代码，如 OperationAgentDeliveredToCustomer")
    operation_type_name: Mapped[Optional[str]] = mapped_column(Text, comment="操作类型名称（中文描述）")
    type: Mapped[Optional[str]] = mapped_column(String(20), comment="大类: orders(销售) / returns(退货) / other(其他)")
    operation_date: Mapped[date] = mapped_column(Date, nullable=False, comment="操作日期")
    sku_id: Mapped[Optional[int]] = mapped_column(BigInteger, comment="关联 SKU（部分费用无 SKU）")
    item_name: Mapped[Optional[str]] = mapped_column(Text, comment="商品名称")
    posting_number: Mapped[Optional[str]] = mapped_column(String(255), comment="发货单号")
    delivery_schema: Mapped[Optional[str]] = mapped_column(String(20), comment="配送方案: FBO / FBS / RFBS")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="金额 RUB（正=收入，负=支出）")
    accruals_for_sale: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="销售应计金额")
    sale_commission: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="销售佣金 RUB（负数）")
    delivery_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="物流运费 RUB")
    return_delivery_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="退货物流费 RUB")
    services: Mapped[Optional[dict]] = mapped_column(JSON, comment="服务明细列表（JSON，含名称和价格）")
    items: Mapped[Optional[dict]] = mapped_column(JSON, comment="商品明细列表（JSON）")
    sync_batch_id: Mapped[Optional[str]] = mapped_column(String(100), comment="同步批次 ID")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="记录创建时间")


class SyncLog(Base):
    """同步审计日志"""
    __tablename__ = "sync_log"
    __table_args__ = {"schema": "ozon"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键")
    sync_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="同步类型: products / analytics / finance / summary")
    status: Mapped[str] = mapped_column(String(20), nullable=False, comment="状态: running / success / failed")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="开始时间")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="完成时间")
    records_processed: Mapped[int] = mapped_column(Integer, default=0, comment="处理记录数")
    date_from: Mapped[Optional[date]] = mapped_column(Date, comment="查询起始日期")
    date_to: Mapped[Optional[date]] = mapped_column(Date, comment="查询截止日期")
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="错误信息（失败时记录）")
    batch_id: Mapped[Optional[str]] = mapped_column(String(100), comment="同步批次 ID，用于关联多次操作")
