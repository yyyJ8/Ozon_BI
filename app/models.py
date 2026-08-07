"""
SQLAlchemy ORM 模型 — 10 张数据表 + 1 张 stores 配置表，每字段带中文注释

主键设计：
  所有数据表 = store_id + 业务主键
  stocks FK → products (store_id, sku_id)
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON, BigInteger, Boolean, Date, DateTime, ForeignKey,
    ForeignKeyConstraint,
    Integer, LargeBinary, Numeric, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ============================================================
# Store — 店铺配置表
# ============================================================
class Store(Base):
    """店铺 API 凭证配置"""
    __tablename__ = "stores"
    __table_args__ = {"schema": "ozon"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="店铺 ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="店铺名称")
    client_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="Ozon Seller API Client-Id")
    api_key: Mapped[str] = mapped_column(String(100), nullable=False, comment="Ozon Seller API Key")
    perf_client_id: Mapped[Optional[str]] = mapped_column(String(100), comment="Performance API Client-Id")
    perf_client_secret: Mapped[Optional[str]] = mapped_column(String(100), comment="Performance API Client-Secret")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用同步")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="记录创建时间")


# ============================================================
# 数据表
# ============================================================

class Product(Base):
    """商品主数据 — 来源 /v3/product/info/list"""
    __tablename__ = "products"
    __table_args__ = {"schema": "ozon"}

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="店铺 ID")
    sku_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="SKU 编号（Ozon 唯一标识）")
    product_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="商品 ID（Ozon 内部编号）")
    name: Mapped[Optional[str]] = mapped_column(Text, comment="商品名称")
    offer_id: Mapped[Optional[str]] = mapped_column(String(255), comment="商家自定义商品编码")
    category_id: Mapped[Optional[int]] = mapped_column(Integer, comment="类目 ID")
    barcode: Mapped[Optional[str]] = mapped_column(String(255), comment="条形码")
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="当前售价（RUB）")
    old_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="原价/划线价（RUB）")
    marketing_seller_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="促销价（RUB）——用户实际看到/支付的价格")
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
    __table_args__ = (
        ForeignKeyConstraint(
            ["store_id", "sku_id"],
            ["ozon.products.store_id", "ozon.products.sku_id"],
        ),
        {"schema": "ozon"},
    )

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="店铺 ID")
    sku_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="SKU 编号，关联 products.sku_id")
    source: Mapped[str] = mapped_column(String(20), primary_key=True, comment="库存来源，如 fbo / fbs")
    present: Mapped[int] = mapped_column(Integer, default=0, comment="当前库存量")
    reserved: Mapped[int] = mapped_column(Integer, default=0, comment="已预留库存量（订单占用）")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="记录更新时间")

    product = relationship("Product", back_populates="stocks")


class SkuDailySummary(Base):
    """SKU 日汇总（核心看板表）— 通过同步服务聚合构建"""
    __tablename__ = "sku_daily_summary"
    __table_args__ = {"schema": "ozon"}

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="店铺 ID")
    record_date: Mapped[date] = mapped_column("date", Date, primary_key=True, comment="日期（YYYY-MM-DD）")
    sku_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="SKU 编号")
    offer_id: Mapped[Optional[str]] = mapped_column(String(255), comment="商家自定义商品编码")

    # 销售指标（来源：analytics API）
    ordered_units: Mapped[int] = mapped_column(Integer, default=0, comment="下单件数（analytics API）")
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="销售收入 RUB（analytics API）")

    # 库存快照（来源：stocks 表，同步时快照）
    stock_present: Mapped[int] = mapped_column(Integer, default=0, comment="现有库存件数")
    stock_reserved: Mapped[int] = mapped_column(Integer, default=0, comment="已预留件数")

    # 履约指标（来源：posting API，按 created_at + sku 聚合）
    delivered_units: Mapped[int] = mapped_column(Integer, default=0, comment="实际送达件数（posting delivered）")
    cancelled_units: Mapped[int] = mapped_column(Integer, default=0, comment="取消件数（posting cancelled）")

    # 财务指标（来源：finance API，按 sku + date 聚合）
    returns_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="退货退款金额 RUB（负数）")
    returns_units: Mapped[int] = mapped_column(Integer, default=0, comment="退货件数（已按 posting_number 归因到原销售日期）")
    commissions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="佣金总额 RUB（负数）")
    logistics_costs: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="物流费 RUB（负数）")
    storage_fees: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="仓储费 RUB（负数）")
    advertising: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="广告费 RUB（负数）")
    promotion_costs: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="推广费 RUB（负数，按单付费推广）")
    other_costs: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="其他费用 RUB（负数，银行手续费/包装/销毁等）")
    net_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="净利润 RUB = revenue + 各项费用")
    profit_margin: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0, comment="净利润率 % = net_profit / revenue * 100")

    # 元数据
    data_quality: Mapped[str] = mapped_column(String(20), default="partial", comment="数据质量: partial(仅有销售) / complete(含财务)")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="最后同步时间")


class Posting(Base):
    """订单履约数据 — 来源 /v2/posting/fbo/list + /v3/posting/fbs/list"""
    __tablename__ = "postings"
    __table_args__ = {"schema": "ozon"}

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="店铺 ID")
    posting_number: Mapped[str] = mapped_column(String(255), primary_key=True, comment="发货单号（Ozon 唯一标识）")
    order_number: Mapped[Optional[str]] = mapped_column(String(255), comment="订单号（一个订单可拆多个 posting）")
    delivery_schema: Mapped[Optional[str]] = mapped_column(String(20), comment="配送方案: FBO / FBS")
    status: Mapped[Optional[str]] = mapped_column(String(50), comment="状态: awaiting_deliver / delivering / delivered / cancelled")
    cancel_reason_id: Mapped[int] = mapped_column(Integer, default=0, comment="取消原因 ID（0 = 未取消）")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="下单时间（即原销售日期）")
    in_process_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="开始处理时间")
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="实际送达时间")
    products: Mapped[Optional[dict]] = mapped_column(JSON, comment="商品明细 [{sku, name, quantity, offer_id, price}]")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="最后同步时间")


class FinanceTransaction(Base):
    """财务流水原始数据 — 来源 /v3/finance/transaction/list"""
    __tablename__ = "finance_transactions"
    __table_args__ = {"schema": "ozon"}

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="店铺 ID")
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
    store_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="店铺 ID")
    sync_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="同步类型: products / analytics / finance / summary")
    status: Mapped[str] = mapped_column(String(20), nullable=False, comment="状态: running / success / failed")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="开始时间")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="完成时间")
    records_processed: Mapped[int] = mapped_column(Integer, default=0, comment="处理记录数")
    date_from: Mapped[Optional[date]] = mapped_column(Date, comment="查询起始日期")
    date_to: Mapped[Optional[date]] = mapped_column(Date, comment="查询截止日期")
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="错误信息（失败时记录）")
    batch_id: Mapped[Optional[str]] = mapped_column(String(100), comment="同步批次 ID，用于关联多次操作")


class AdCampaign(Base):
    """广告活动主数据 — 来源 Performance API GET /api/client/campaign"""
    __tablename__ = "ad_campaigns"
    __table_args__ = {"schema": "ozon"}

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="店铺 ID")
    campaign_id: Mapped[str] = mapped_column(
        String(20), primary_key=True,
        comment="广告活动 ID（Ozon Performance 唯一标识）")
    title: Mapped[Optional[str]] = mapped_column(
        Text, comment="活动标题（SKU 类型含 offer_id 前缀，如 33367-亚克力仓鼠笼）")
    campaign_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="活动类型: SKU / SEARCH_PROMO / ALL_SKU_PROMO / REF_VK / REF_BLOGGER")
    state: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="活动状态: CAMPAIGN_STATE_RUNNING / CAMPAIGN_STATE_ARCHIVED / CAMPAIGN_STATE_INACTIVE")
    budget: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), default=0,
        comment="活动预算 RUB（部分活动 budget=0 表示无上限）")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now,
        comment="记录创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now,
        comment="记录更新时间")


class AdDailyStats(Base):
    """广告每日统计 — 来源 GET /api/client/statistics/daily (CSV)"""
    __tablename__ = "ad_daily_stats"
    __table_args__ = {"schema": "ozon"}

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="店铺 ID")
    campaign_id: Mapped[str] = mapped_column(
        String(20), primary_key=True,
        comment="广告活动 ID，关联 ad_campaigns.campaign_id")
    stat_date: Mapped[date] = mapped_column(
        Date, primary_key=True,
        comment="统计日期（CSV 字段: Дата）")
    impressions: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="展示量（CSV 字段: Показы）")
    clicks: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="点击量（CSV 字段: Клики）")
    spend: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0,
        comment="广告花费 RUB，正数（CSV 字段: Расход, %s）。聚合到 sku_daily_summary 时需取负" % chr(8381))
    orders_count: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="广告带来的订单数（CSV 字段: Заказы, шт.）")
    orders_sum: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0,
        comment="广告带来的订单金额 RUB（CSV 字段: Заказы, %s）" % chr(8381))
    synced_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now,
        comment="最后同步时间")


class AdCampaignSkuMap(Base):
    """广告活动 → SKU 映射表（自动/手动建立关联）"""
    __tablename__ = "ad_campaign_sku_map"
    __table_args__ = {"schema": "ozon"}

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="店铺 ID")
    campaign_id: Mapped[str] = mapped_column(
        String(20), primary_key=True,
        comment="广告活动 ID，关联 ad_campaigns.campaign_id")
    sku_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True,
        comment="SKU 编号，关联 products.sku_id")
    offer_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="商家自定义商品编码（反范式冗余，便于查询）")
    mapping_method: Mapped[str] = mapped_column(
        String(20), default="auto",
        comment="映射方式: auto（offer_id 前缀自动匹配）/ manual（人工指定）")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now,
        comment="映射创建时间")


class Return(Base):
    """退货数据 — 来源 /v1/returns/list"""
    __tablename__ = "returns"
    __table_args__ = {"schema": "ozon"}

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="店铺 ID")
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="退货 ID（Ozon 唯一标识）")
    posting_number: Mapped[str] = mapped_column(String(255), nullable=False, comment="发货单号，关联 postings.posting_number")
    sku: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="SKU 编号，关联 products.sku_id")
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="退货类型: Cancellation(未签收就退) / ClientReturn(签收后退货)")
    return_reason_name: Mapped[Optional[str]] = mapped_column(Text, comment="退货原因（俄文原文，如 Покупатель передумал = 改变主意）")
    quantity: Mapped[int] = mapped_column(Integer, default=0, comment="退货件数")
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="退货时售价 RUB")
    visual_status: Mapped[str] = mapped_column(String(50), nullable=False, comment="退货当前状态: ReturnedToOzon/Utilized/WriteOff/ReceivedBySeller 等")
    status_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="最后状态变更时间（visual.change_moment）")
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="退货发起时间（logistic.return_date，客户交退货快递/退货点的时间）")
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="退货完结时间（终态取 logistic.final_moment，无则用 status_changed_at 兜底，中间态为 NULL）")
    schema: Mapped[str] = mapped_column(String(10), nullable=False, comment="配送方案: Fbo / Fbs")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="最后同步时间")


class AdSkuDailyStats(Base):
    """广告 SKU 日明细 — 来源 POST /api/client/statistics 异步报告 (ZIP CSV)"""
    __tablename__ = "ad_sku_daily_stats"
    __table_args__ = {"schema": "ozon"}

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="店铺 ID")
    campaign_id: Mapped[str] = mapped_column(
        String(20), primary_key=True,
        comment="广告活动 ID")
    sku_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True,
        comment="SKU 编号（SEARCH_PROMO 等全店活动记为 0）")
    stat_date: Mapped[date] = mapped_column(
        Date, primary_key=True,
        comment="统计日期（当天 report 的 dateFrom=dateTo）")
    sku_name: Mapped[Optional[str]] = mapped_column(
        Text, comment="SKU 名称（CSV 字段: Название товара）")
    sku_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), comment="SKU 单价 RUB（CSV 字段: Цена товара, %s）" % chr(8381))
    impressions: Mapped[int] = mapped_column(
        Integer, default=0, comment="展示量（CSV 字段: Показы）")
    clicks: Mapped[int] = mapped_column(
        Integer, default=0, comment="点击量（CSV 字段: Клики）")
    ctr: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4), comment="点击率 %（CSV 字段: CTR, %%）")
    add_to_cart: Mapped[int] = mapped_column(
        Integer, default=0, comment="加入购物车次数（CSV 字段: Добавления в корзину）")
    avg_cpc: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), comment="平均单次点击费用 RUB（CSV 字段: Средняя стоимость клика, %s）" % chr(8381))
    spend: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0, comment="广告花费 RUB（CSV 字段: Расход, %s, с НДС）" % chr(8381))
    sold_units: Mapped[int] = mapped_column(
        Integer, default=0, comment="推广直接售出件数（CSV 字段: Продано товаров）")
    sales_promotion: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), comment="推广直接销售额 RUB（CSV 字段: Продажи в продвижении, %s）" % chr(8381))
    total_ordered: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), comment="该SKU总订单金额 RUB（CSV 字段: Заказано на сумму, %s）" % chr(8381))
    drr_promotion: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4), comment="推广花费占推广收入比 %%（CSV 字段: ДРР в продвижении, %%）")
    drr_total: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4), comment="推广花费占总收入比 %%（CSV 字段: ДРР (общий), %%）")
    date_added: Mapped[Optional[date]] = mapped_column(
        Date, comment="SKU 加入活动的日期")
    synced_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now,
        comment="最后同步时间")


class SkuManagement(Base):
    """SKU 手动管理数据"""
    __tablename__ = "sku_management"
    __table_args__ = {"schema": "ozon"}

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    main_sku: Mapped[Optional[str]] = mapped_column(String(50))
    source_url_1688: Mapped[Optional[str]] = mapped_column(Text)
    specification: Mapped[Optional[str]] = mapped_column(Text)
    sales_manager: Mapped[Optional[str]] = mapped_column(String(50))
    listed_stores: Mapped[Optional[str]] = mapped_column(String(50))
    product_status: Mapped[Optional[str]] = mapped_column(String(50))
    key_notes: Mapped[Optional[str]] = mapped_column(Text)

    length_cm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    width_cm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    height_cm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    actual_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    volume_cbm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    density: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))

    first_leg_unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    units_per_carton: Mapped[Optional[int]] = mapped_column(Integer)
    carton_length_cm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    carton_width_cm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    carton_height_cm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    gross_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    volume_liters: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))

    purchase_cost_rmb: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    warehousing_fee_rmb: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    fbo_delivery_fee_rmb: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    first_leg_cost_rmb: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))

    acquiring_fee_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    fbo_commission_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    logistics_rub: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    delivery_pickup_rub: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    advertising_rate_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    return_rate_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    tax_and_fee_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    risk_reserve_rub: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))

    exchange_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    green_price_rub: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))

    competitor_1: Mapped[Optional[str]] = mapped_column(String(200))
    competitor_2: Mapped[Optional[str]] = mapped_column(String(200))
    competitor_sales: Mapped[Optional[int]] = mapped_column(Integer)

    purchase_cost_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    first_leg_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    last_mile_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    product_cost_rmb: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    discount_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    platform_payout_rub: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    actual_payout_rub: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    profit_rmb: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    profit_rub: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    profit_margin_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class SkuDailySnapshot(Base):
    """SKU 每日快照 — 每日同步时从 products + stocks 表快照价格和库存"""
    __tablename__ = "sku_daily_snapshot"
    __table_args__ = {"schema": "ozon"}

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="店铺 ID")
    sku_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="SKU 编号")
    record_date: Mapped[date] = mapped_column(Date, primary_key=True, comment="记录日期")
    offer_id: Mapped[Optional[str]] = mapped_column(String(255), comment="商品编码（冗余）")

    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="当前售价 RUB")
    old_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="原价/划线价 RUB")
    marketing_seller_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="促销价 RUB")
    min_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="最低允许售价 RUB")
    retail_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="零售价 RUB（v5 接口，通常为 0）")
    net_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="净价 RUB（v5 接口，通常为 0）")
    vat: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="增值税 RUB（v5 接口，通常为 0）")

    green_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="绿标价格/买家展示价 RUB（待定数据源）")

    stock_present: Mapped[int] = mapped_column(Integer, default=0, comment="可售库存件数")
    stock_reserved: Mapped[int] = mapped_column(Integer, default=0, comment="已预留库存件数")

    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="记录创建时间")


# ============================================================
# OZON 直发信息模块
# ============================================================

class OzonDirectSku(Base):
    """OZON 直发 — SKU 基础数据（来源 OZON直发信息.xlsx Sheet1）"""
    __tablename__ = "ozon_direct_sku"
    __table_args__ = {"schema": "ozon"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    sku: Mapped[str] = mapped_column(String(100), nullable=False, comment="SKU 编码")
    product_name: Mapped[Optional[str]] = mapped_column(Text, comment="产品名称")
    supplier: Mapped[Optional[str]] = mapped_column(Text, comment="供应商")
    store_name: Mapped[Optional[str]] = mapped_column(String(50), comment="店铺")
    sales_manager: Mapped[Optional[str]] = mapped_column(String(50), comment="销售负责人")
    label_file: Mapped[Optional[str]] = mapped_column(String(255), comment="标签文件（关联文件名）")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="软删除标记")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="记录创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="记录更新时间")


class OzonDirectShipment(Base):
    """OZON 直发 — 直发跟进表（来源 OZON直发信息.xlsx Sheet2）"""
    __tablename__ = "ozon_direct_shipment"
    __table_args__ = {"schema": "ozon"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="自增主键")

    # 申购信息
    pr_no: Mapped[Optional[str]] = mapped_column(String(100), comment="申购单号")
    sku: Mapped[Optional[str]] = mapped_column(String(100), comment="SKU 编码")
    product_cn_name: Mapped[Optional[str]] = mapped_column(Text, comment="产品中文名")
    pr_date: Mapped[Optional[date]] = mapped_column(Date, comment="申购时间")
    pr_person: Mapped[Optional[str]] = mapped_column(String(50), comment="申购人员")
    supplier: Mapped[Optional[str]] = mapped_column(Text, comment="供应商")
    po_no: Mapped[Optional[str]] = mapped_column(String(100), comment="采购单号")
    online_po_no: Mapped[Optional[str]] = mapped_column(String(200), comment="网采单号")
    is_received: Mapped[Optional[str]] = mapped_column(String(20), comment="是否收货上架")

    # 数量/包装
    total_qty: Mapped[Optional[int]] = mapped_column(Integer, comment="总数")
    total_boxes: Mapped[Optional[int]] = mapped_column(Integer, comment="总箱数")
    product_label: Mapped[Optional[str]] = mapped_column(Text, comment="产品标签")
    carton_mark: Mapped[Optional[str]] = mapped_column(Text, comment="外箱箱唛")
    warehouse_receipt: Mapped[Optional[str]] = mapped_column(String(500), comment="入库清单（关联文件）")

    # 发货信息
    receiving_address: Mapped[Optional[str]] = mapped_column(Text, comment="收货地址")
    labeling_notes: Mapped[Optional[str]] = mapped_column(Text, comment="贴标发货说明")
    logistics_provider: Mapped[Optional[str]] = mapped_column(String(100), comment="物流商")
    first_leg_tracking: Mapped[Optional[str]] = mapped_column(String(200), comment="物流商头程单号")

    # 箱规
    total_boxes_2: Mapped[Optional[int]] = mapped_column(Integer, comment="总箱数（重复列）")
    length_cm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), comment="长（cm）")
    width_cm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), comment="宽（cm）")
    height_cm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), comment="高（cm）")
    gross_weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), comment="毛重（kg）")
    total_cbm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), comment="总方数（CBM）")
    density: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), comment="密度")

    # 物流跟踪
    plan_no: Mapped[Optional[str]] = mapped_column(String(100), comment="计划单号")
    ship_date: Mapped[Optional[date]] = mapped_column(Date, comment="发货时间")
    tracking_no: Mapped[Optional[str]] = mapped_column(String(500), comment="物流单号")
    logistics_company: Mapped[Optional[str]] = mapped_column(String(200), comment="物流公司")

    # 备注/售后
    special_notes: Mapped[Optional[str]] = mapped_column(Text, comment="特殊情况备注")
    previous_aftersales: Mapped[Optional[str]] = mapped_column(Text, comment="上期售后情况")
    qty_total_2: Mapped[Optional[int]] = mapped_column(Integer, comment="总数（重复列）")
    receiving_status: Mapped[Optional[str]] = mapped_column(Text, comment="货物收货情况")
    receiving_date: Mapped[Optional[date]] = mapped_column(Date, comment="收货时间")
    shipment_no: Mapped[Optional[str]] = mapped_column(String(200), comment="货件单号")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="软删除标记")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="记录创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="记录更新时间")


class OzonDirectFile(Base):
    """OZON 直发 — 附件文件（标签PDF、入库清单、上传图片等）"""
    __tablename__ = "ozon_direct_files"
    __table_args__ = {"schema": "ozon"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    source_table: Mapped[str] = mapped_column(String(50), nullable=False, comment="来源表: sku / shipment")
    sku: Mapped[Optional[str]] = mapped_column(String(100), comment="关联 SKU（业务键）")
    pr_no: Mapped[Optional[str]] = mapped_column(String(100), comment="关联申购单号（直发跟进表业务键）")
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    file_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary, comment="文件二进制内容")
    file_size: Mapped[Optional[int]] = mapped_column(Integer, comment="文件大小（字节）")
    file_type: Mapped[Optional[str]] = mapped_column(String(20), comment="文件扩展名")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="上传时间")


# ============================================================
# CargoShipment — 货件汇总（转运仓→FBO仓 追踪）
# ============================================================
class CargoShipment(Base):
    """货件汇总表 — 跟踪货件从中转仓到FBO仓的状态"""
    __tablename__ = "cargo_shipments"
    __table_args__ = {"schema": "ozon"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    sku: Mapped[str] = mapped_column(String(200), index=True, nullable=False, comment="SKU编码（关联 products.offer_id）")
    product_name: Mapped[Optional[str]] = mapped_column(String(500), comment="产品名称")
    store: Mapped[Optional[str]] = mapped_column(String(50), comment="店铺")
    requisitioner: Mapped[Optional[str]] = mapped_column(String(100), comment="申购人")
    replenishment_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="补货数量")
    carton_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="装箱数（每箱装几个）")
    carton_volume: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="外箱体积（单箱 m³）")
    carton_gross_weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="外箱毛重（单箱 kg）")
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="总重量（kg）")
    cbm: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="总方数（CBM）")
    density: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="密度")
    box_count: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="箱数（总箱数）")
    transit_warehouse: Mapped[Optional[str]] = mapped_column(String(200), comment="中转仓")
    logistics_inbound_no: Mapped[Optional[str]] = mapped_column(String(200), comment="物流商入库单号")
    pr_no: Mapped[Optional[str]] = mapped_column(String(200), index=True, comment="关联直发申购单号（来自 ozon_direct_shipment）")
    cargo_status: Mapped[Optional[str]] = mapped_column(String(100), comment="货物状态")
    fbo_warehouse_name: Mapped[Optional[str]] = mapped_column(String(200), comment="FBO仓名称")
    booking_code: Mapped[Optional[str]] = mapped_column(String(200), comment="约仓编码")
    fbo_listing_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="FBO上架时间")
    warehouse_rent_start: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="仓租开始时间")
    actual_listing_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="实际上架数量")
    info_remarks: Mapped[Optional[str]] = mapped_column(Text, comment="信息备注")
    batch_quotation: Mapped[Optional[str]] = mapped_column(String(200), comment="批次报价")
    product_status: Mapped[Optional[str]] = mapped_column(String(100), comment="产品状态")
    stocking_opinion: Mapped[Optional[str]] = mapped_column(Text, comment="备货意见")
    parent_record: Mapped[Optional[str]] = mapped_column(String(200), comment="父记录")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
