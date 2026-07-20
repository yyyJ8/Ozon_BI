"""
SQLAlchemy ORM 模型 — 9 张表，每字段带中文注释

主键设计：
  products, stocks, sku_daily_summary, finance_transactions, postings,
  ad_campaigns, ad_daily_stats, ad_campaign_sku_map
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
    other_costs: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="其他费用 RUB（负数，银行手续费/包装/销毁等）")
    net_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="净利润 RUB = revenue + 各项费用")
    profit_margin: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0, comment="净利润率 % = net_profit / revenue * 100")

    # 元数据
    data_quality: Mapped[str] = mapped_column(String(20), default="partial", comment="数据质量: partial(仅有销售) / complete(含财务)")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="最后同步时间")


class Posting(Base):
    """订单履约数据 — 来源 /v2/posting/fbo/list + /v3/posting/fbs/list

    记录每笔订单的完整生命周期：下单 → 配送 → 签收 / 取消
    核心用途：
      1. 退货归因 — posting_number → created_at 找到原销售日期
      2. 漏斗分析 — ordered_units vs delivered vs cancelled
    """
    __tablename__ = "postings"
    __table_args__ = {"schema": "ozon"}

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


class AdCampaign(Base):
    """广告活动主数据 — 来源 Performance API GET /api/client/campaign"""
    __tablename__ = "ad_campaigns"
    __table_args__ = {"schema": "ozon"}

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
    """退货数据 — 来源 /v1/returns/list

    记录每笔退货的完整信息，按 posting_number + sku 定位。
    核心用途：
      1. 区分 Cancellation（未签收退回）vs ClientReturn（签收后退回）
      2. 退货原因归因（return_reason_name → category）
      3. 退货时效：returned_at → finished_at
    """
    __tablename__ = "returns"
    __table_args__ = {"schema": "ozon"}

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
    """广告 SKU 日明细 — 来源 POST /api/client/statistics 异步报告 (ZIP CSV)

    报告内每个活动含 1~N 个 SKU，一个 SKU 一行。
    日常同步: dateFrom=dateTo=昨天 → stat_date=昨天。
    字段来源于异步报告 CSV 的俄文表头。
    """
    __tablename__ = "ad_sku_daily_stats"
    __table_args__ = {"schema": "ozon"}

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
        Date, comment="SKU 加入活动的日期（CSV 字段: Дата добавления）")
    synced_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now,
        comment="最后同步时间")
