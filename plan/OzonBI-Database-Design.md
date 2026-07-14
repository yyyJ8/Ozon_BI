# Ozon BI — 数据库表设计

> 基于实际 API 数据验证结果设计（2026-07-14 验证）
> 5 张表，1 个核心，覆盖商品/库存/销售/财务全链路

---

## 目录

- [1. 表间关系总览](#1-表间关系总览)
- [2. 表定义](#2-表定义)
  - [2.1 products — 商品主数据](#21-products--商品主数据)
  - [2.2 stocks — 库存明细](#22-stocks--库存明细)
  - [2.3 sku_daily_summary — SKU 日汇总（核心看板表）⭐](#23-sku_daily_summary--sku-日汇总核心看板表)
  - [2.4 finance_transactions — 财务流水原始数据](#24-finance_transactions--财务流水原始数据)
  - [2.5 sync_log — 同步审计日志](#25-sync_log--同步审计日志)
- [3. 看板查询路径示例](#3-看板查询路径示例)
- [4. 同步流程](#4-同步流程)
- [5. 与原始计划对比的调整](#5-与原始计划对比的调整)

---

## 1. 表间关系总览

```
                          ┌──────────────────┐
                          │    sync_log      │
                          │  同步审计日志     │
                          └────────┬─────────┘
                                   │ 记录每次同步结果
                                   │
┌──────────────────┐     ┌─────────┴──────────┐     ┌──────────────────────────┐
│    products      │     │ sku_daily_summary  │     │  finance_transactions    │
│  商品主数据      │◄───►│  SKU日汇总 ⭐      │◄────│  财务流水原始数据         │
│  sku_id (PK)     │     │  date + sku_id     │     │  operation_id (唯一)     │
│  product_id      │     │  (复合唯一)         │     │  sku_id (FK→products)   │
│  name, price,    │     │                    │     │  amount, type, date     │
│  category_id     │     │  ordered_units     │     │  items[].sku → 关联SKU  │
│  commissions     │     │  revenue           │     │  services[].price       │
└────────┬─────────┘     │  returns_amount    │     └──────────────────────────┘
         │               │  commissions       │
         │               │  logistics_costs   │
         ▼               │  storage_fees      │
  ┌──────────────┐       │  advertising       │
  │   stocks     │       │  net_profit        │
  │  库存明细    │       │  profit_margin     │
  │  sku_id (FK) │       └────────────────────┘
  │  present     │
  │  reserved    │
  │  source(FBO) │
  └──────────────┘
```

### 核心说明

| 表 | 角色 | 数据量级 | 更新频率 |
|----|------|---------|---------|
| **products** | 商品维度表 | 41 行 | 每周/按需 |
| **stocks** | 库存事实 | ~50 行 | 每日同步 |
| **sku_daily_summary** ⭐ | **看板核心，所有查询的中心** | ~1,000 行/月 | 每日构建 |
| **finance_transactions** | 原始流水，支持回溯 | ~1,385 行/月 | 每日追加 |
| **sync_log** | 同步审计 | ~5 行/天 | 每次同步写入 |

所有表位于 **`ozon`** schema，与 `public` schema 下的其他业务表隔离。

---

## 2. 表定义

### 2.1 `products` — 商品主数据

存储每个 SKU 的静态信息。来自 `/v3/product/info/list`。

```sql
CREATE TABLE ozon.products (
    sku_id              BIGINT PRIMARY KEY,        -- Ozon SKU ID（全系统核心维度）
    product_id          BIGINT NOT NULL,           -- 商品 ID（可能有不同 SKU 变体）
    name                TEXT,                      -- 商品名称
    offer_id            VARCHAR(255),              -- 商家 SKU 编码
    category_id         INTEGER,                   -- 分类 ID（API 返回 description_category_id）
    barcode             VARCHAR(255),              -- 条码（取 barcodes[] 第一个）
    price               NUMERIC(12,2),             -- 当前售价（如 19000.00）
    old_price           NUMERIC(12,2),             -- 原价/划线价（如 28499.00）
    min_price           NUMERIC(12,2),             -- 最低价（API 可能返回空字符串，存 NULL）
    commission_fbo_pct  NUMERIC(10,4),             -- FBO 方案佣金比例（如 38.0000%）
    volume_weight       NUMERIC(8,2),              -- 体积重（如 6.50 kg）
    status              VARCHAR(50),               -- 商品状态（statuses.status: price_sent 等）
    is_archived         BOOLEAN DEFAULT FALSE,     -- 是否已归档
    images              JSONB,                     -- 图片 URL 列表
    primary_image       TEXT,                      -- 主图 URL（取 primary_image[] 第一个）
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_products_offer_id ON ozon.products(offer_id);
CREATE INDEX idx_products_category ON ozon.products(category_id);
```

**说明：**
- `sku_id` 是 BI 看板的**核心维度**，所有其他表通过它关联
- `category_id` 来自 `description_category_id`，当前 18 个品类
- `commission_fbo_pct` 从 `commissions[]` 数组中取 `sale_schema = 'FBO'` 的 `percent` 字段
- `volume_weight` 来自 API 的 `volume_weight` 字段，用于物流成本估算
- `min_price` API 可能返回空字符串，入库时转为 NULL
- `images` 存 JSON 数组，方便前端直接使用

---

### 2.2 `stocks` — 库存明细

每个 SKU 在每个仓库（FBO/FBS）的库存量。

```sql
CREATE TABLE ozon.stocks (
    id              BIGSERIAL PRIMARY KEY,
    sku_id          BIGINT NOT NULL REFERENCES ozon.products(sku_id),
    present         INTEGER DEFAULT 0,         -- 现有库存（如 47 件）
    reserved        INTEGER DEFAULT 0,         -- 预留库存（订单占用）
    source          VARCHAR(20) NOT NULL,       -- 仓库：fbo / fbs
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(sku_id, source)
);

-- 索引
CREATE INDEX idx_stocks_sku ON ozon.stocks(sku_id);
```

**说明：**
- 数据来源：`/v3/product/info/list` → `stocks.stocks[]` 字段
- 当前数据：31 条 FBO 记录 + 2 条 FBS 记录，总库存 490 件
- 17/41 个商品有库存，24 个无库存

---

### 2.3 `sku_daily_summary` — SKU 日汇总（核心看板表）⭐

**这是看板所有查询的中心表。** 数据来自两个渠道的聚合：
- 销售指标 ← `/v1/analytics/data`（ordered_units, revenue）
- 财务指标 ← `/v3/finance/transaction/list` 按 SKU+日期聚合

```sql
CREATE TABLE ozon.sku_daily_summary (
    id              BIGSERIAL PRIMARY KEY,
    date            DATE NOT NULL,
    sku_id          BIGINT NOT NULL,
    offer_id        VARCHAR(255),

    -- 销售指标（来源：analytics API）
    ordered_units   INTEGER DEFAULT 0,         -- 销量（如 32 件）
    revenue         NUMERIC(12,2) DEFAULT 0,   -- 收入（如 167,200.00 RUB）

    -- 财务指标（来源：finance API，按 sku + date 聚合）
    returns_amount  NUMERIC(12,2) DEFAULT 0,   -- 退货金额
    commissions     NUMERIC(12,2) DEFAULT 0,   -- 佣金（负数）
    logistics_costs NUMERIC(12,2) DEFAULT 0,   -- 物流费（负数）
    storage_fees    NUMERIC(12,2) DEFAULT 0,   -- 仓储费（负数）
    advertising     NUMERIC(12,2) DEFAULT 0,   -- 广告费（负数）
    other_costs     NUMERIC(12,2) DEFAULT 0,   -- 其他费用（银行手续费等，负数）
    net_profit      NUMERIC(12,2) DEFAULT 0,   -- 净利润 = revenue + 所有费用（含符号）
    profit_margin   NUMERIC(5,2) DEFAULT 0,    -- 利润率 % = net_profit / revenue * 100

    -- 元数据
    data_quality    VARCHAR(20) DEFAULT 'partial',  -- complete / partial / estimated
    synced_at       TIMESTAMP DEFAULT NOW(),

    UNIQUE(date, sku_id)
);

-- 索引（看板查询优化）
CREATE INDEX idx_summary_date ON ozon.sku_daily_summary(date);
CREATE INDEX idx_summary_sku ON ozon.sku_daily_summary(sku_id);
CREATE INDEX idx_summary_date_sku ON ozon.sku_daily_summary(date DESC, sku_id);
```

**聚合逻辑（同步服务处理）：**

```
revenue       = analytics_api.revenue                  (直接取数)
ordered_units = analytics_api.ordered_units            (直接取数)

commissions   = SUM(finance.sale_commission)           WHERE type = 'OperationAgentDeliveredToCustomer'
returns       = SUM(finance.amount)                    WHERE type = 'OperationItemReturn' 或 'ClientReturnAgentOperation'
logistics     = SUM(finance.services[].price)          WHERE service 含 Logistics
storage       = SUM(finance.amount)                    WHERE type = 'OperationMarketplaceItemTemporaryStorage*'
advertising   = SUM(finance.amount)                    WHERE type = 'OperationMarketplaceCostPerClick'
other_costs   = SUM(finance.amount)                    减去以上所有

net_profit    = revenue + commissions + returns + logistics + storage + advertising + other
               (费用为负数，直接相加即扣减)
profit_margin = CASE WHEN revenue > 0 THEN net_profit / revenue * 100 ELSE 0 END
```

---

### 2.4 `finance_transactions` — 财务流水原始数据

存储 Ozon 财务 API 返回的原始明细。用于回溯、重新聚合、详情页展示。

```sql
CREATE TABLE ozon.finance_transactions (
    id                  BIGSERIAL PRIMARY KEY,
    operation_id        BIGINT UNIQUE,          -- Ozon 操作 ID（API 去重）
    operation_type      VARCHAR(100) NOT NULL,  -- 费用类型（共 12 种）
    operation_type_name TEXT,                   -- 俄文描述
    type                VARCHAR(20),            -- 大类：orders / returns / other
    operation_date      DATE NOT NULL,          -- 操作日期
    sku_id              BIGINT,                 -- 关联 SKU（来自 items[0].sku）
    item_name           TEXT,                   -- 商品名（来自 items[0].name）
    posting_number      VARCHAR(255),           -- 订单号
    delivery_schema     VARCHAR(20),            -- FBO / FBS
    amount              NUMERIC(12,2) NOT NULL, -- 金额（正=收入，负=支出）
    accruals_for_sale   NUMERIC(12,2) DEFAULT 0,-- 应记收入
    sale_commission     NUMERIC(12,2) DEFAULT 0,-- 佣金金额
    delivery_charge     NUMERIC(12,2) DEFAULT 0,-- 物流费
    return_delivery_charge NUMERIC(12,2) DEFAULT 0,-- 返件物流费
    services            JSONB,                  -- 服务明细：[{name, price}]
    items               JSONB,                  -- 商品明细：[{sku, name}] 保留原始数据
    sync_batch_id       VARCHAR(100),           -- 同步批次 ID
    synced_at           TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_finance_date ON ozon.finance_transactions(operation_date);
CREATE INDEX idx_finance_sku ON ozon.finance_transactions(sku_id);
CREATE INDEX idx_finance_type ON ozon.finance_transactions(operation_type);
CREATE INDEX idx_finance_batch ON ozon.finance_transactions(sync_batch_id);
```

**12 种费用类型分布（近 30 天）：**

| operation_type | 数量 | 金额( RUB) | 说明 |
|---------------|------|-----------|------|
| `OperationAgentDeliveredToCustomer` | 151 | +238,560 | 订单销售收入 |
| `MarketplaceRedistributionOfAcquiringOperation` | 149 | -4,026 | 银行手续费 |
| `OperationItemReturn` | 94 | -6,856 | 退货处理费 |
| `OperationMarketplaceCostPerClick` | 66 | -11,650 | 广告点击费 |
| `MarketplaceServiceItemCrossdocking` | 15 | -5,062 | 交叉转运 |
| `ClientReturnAgentOperation` | 7 | -15,796 | 买家退货 |
| `OperationMarketplaceItemTemporaryStorageRedistribution` | 5 | -1,269 | 仓储费 |
| `OperationPromotionWithCostPerOrder` | 5 | -2,648 | 推广费（按订单） |
| `DisposalReasonFailedToPickupOnTime` | 4 | -450 | 未取件销毁 |
| `OperationMarketplaceSupplyExpirationDateProcessing` | 2 | -268 | 库存有效期处理 |
| `OperationMarketplaceServiceSupplyInboundCargoShortage` | 1 | -800 | 入仓短缺 |
| `OperationMarketplaceServiceSupplyInboundCargoSurplus` | 1 | -800 | 入仓溢余 |

---

### 2.5 `sync_log` — 同步审计日志

记录每次数据同步的执行情况。

```sql
CREATE TABLE ozon.sync_log (
    id                  BIGSERIAL PRIMARY KEY,
    sync_type           VARCHAR(50) NOT NULL,  -- products / analytics / finance / summary
    status              VARCHAR(20) NOT NULL,  -- running / success / failed / partial
    started_at          TIMESTAMP NOT NULL,
    completed_at        TIMESTAMP,
    records_processed   INTEGER DEFAULT 0,
    date_from           DATE,
    date_to             DATE,
    error_message       TEXT,
    batch_id            VARCHAR(100)
);

-- 索引
CREATE INDEX idx_sync_type ON ozon.sync_log(sync_type, started_at DESC);
```

---

## 3. 看板查询路径示例

### 3.1 主看板 — KPI 汇总

```sql
-- 总收入、总销量、动销 SKU 数、利润率
SELECT
    COUNT(DISTINCT sku_id) AS active_skus,
    SUM(ordered_units)     AS total_orders,
    SUM(revenue)           AS total_revenue,
    SUM(net_profit)        AS total_profit,
    CASE WHEN SUM(revenue) > 0
         THEN ROUND(SUM(net_profit) / SUM(revenue) * 100, 1)
         ELSE 0
    END AS profit_margin_pct
FROM ozon.sku_daily_summary
WHERE date BETWEEN '2026-06-01' AND '2026-07-13';
```

### 3.2 销售趋势（每日）

```sql
SELECT date,
       SUM(ordered_units) AS orders,
       SUM(revenue)       AS revenue
FROM ozon.sku_daily_summary
WHERE date BETWEEN '2026-06-01' AND '2026-07-13'
GROUP BY date
ORDER BY date;
```

### 3.3 品类分布

```sql
SELECT p.category_id,
       SUM(s.revenue) AS revenue,
       SUM(s.ordered_units) AS orders
FROM ozon.sku_daily_summary s
JOIN ozon.products p ON s.sku_id = p.sku_id
WHERE s.date BETWEEN '2026-06-01' AND '2026-07-13'
GROUP BY p.category_id
ORDER BY SUM(s.revenue) DESC;
```

### 3.4 费用构成（堆叠图）

```sql
SELECT date,
       SUM(commissions)     AS commissions,
       SUM(logistics_costs) AS logistics,
       SUM(storage_fees)    AS storage,
       SUM(advertising)     AS advertising,
       SUM(other_costs)     AS other
FROM ozon.sku_daily_summary
WHERE date BETWEEN '2026-06-01' AND '2026-07-13'
GROUP BY date
ORDER BY date;
```

### 3.5 SKU 排名表

```sql
SELECT p.name,
       p.offer_id,
       SUM(s.ordered_units) AS units_sold,
       SUM(s.revenue)       AS revenue,
       SUM(s.net_profit)    AS profit,
       AVG(s.profit_margin) AS margin
FROM ozon.sku_daily_summary s
JOIN ozon.products p ON s.sku_id = p.sku_id
WHERE s.date BETWEEN '2026-06-01' AND '2026-07-13'
GROUP BY s.sku_id, p.name, p.offer_id
ORDER BY SUM(s.revenue) DESC
LIMIT 20;
```

---

## 4. 同步流程

```
定时器（每日 3:00 AM）
       │
       ├── 1. Sync Products ────────────────────► products 表
       │       /v3/product/list (分页)              stocks 表
       │       /v3/product/info/list (批量)
       │
       ├── 2. Sync Analytics ──────────────────► sku_daily_summary.ordered_units
       │       /v1/analytics/data                    sku_daily_summary.revenue
       │       dimension: [sku, day]
       │
       ├── 3. Sync Finance ────────────────────► finance_transactions 表
       │       /v3/finance/transaction/list          （原始数据全量保存）
       │       每次30天范围，分页拉取
       │
       └── 4. Build Summary ───────────────────► sku_daily_summary（更新费用字段）
               按finance_transactions按sku+date聚合      commissions/logistics/
               更新sku_daily_summary的费用字段            storage/advertising/net_profit
```

### 启动时检测
- 如果 `products` 表为空 → 执行全量同步
- 如果 `sku_daily_summary` 表为空 → 回溯最近 30 天数据
- 后续每日增量同步

---

## 5. 与原始计划对比的调整

| 项目 | 原计划 | 实际调整 | 原因 |
|------|--------|---------|------|
| `products.category_name` | 直接存储 | 改为只存 `category_id` | API 返回的是 ID，无名称 |
| `products.commission_schemas` | 单个比例 | 从 commissions[] 数组取 FBO 方案的 percent，改名 `commission_fbo_pct` | 每个商品有 4 种销售方案的佣金 |
| `products.fulfillment` | FBO/FBS | **已删除** | API 不返回单一发货方式，每个商品有 4 套方案 |
| `products.visibility` | 可见性 | **已删除** | API 不返回此字段 |
| `products.vat` | 增值税率 | **已删除** | API 始终返回 "0.00"，无业务意义 |
| ➕ `products.volume_weight` | 无 | **新增** | API 有该字段，用于物流成本分析 |
| ➕ `products.is_archived` | 无 | **新增** | 用于商品筛选过滤 |
| ~~流量字段~~ | impressions, visits, conversion | **已删除** | API 已废弃这些指标 |
| **新增** advertising | 无 | **新增广告费字段** | 财务 API 实际有广告点击费数据 |
| `finance_transactions` | 简单表 | **增加 services JSONB** | 财务流水含服务明细需要存储 |
| ➕ `finance_transactions.type` | 无 | **新增** | API 返回大类分类：orders/returns/other |
| ➕ `finance_transactions.return_delivery_charge` | 无 | **新增** | API 有返件物流费字段 |
| ➕ `finance_transactions.items JSONB` | 无 | **新增** | 保留原始商品明细便于回溯 |
| `stocks` | 合并在 products | **独立成表** | 库存每日变化，需要独立更新 |
| category_id 数量 | 预期较少 | 实际 18 个品类 | 按实际数据 |

---

> 版本：v1.2 | 最后更新：2026-07-14
> 基于 Ozon Seller API 实际数据验证结果
