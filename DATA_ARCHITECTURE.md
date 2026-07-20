# OzonSku 数据架构

## 数据总览（截至 2026-07-17）

| 模块 | 表名 | 记录数 | 数据范围 |
|------|------|--------|----------|
| 商品 | `products` + `stocks` | 39 SKU / 32 库存 | — |
| 订单 | `postings` | 1,934 条 | 2026-03 ~ 2026-07 |
| 财务 | `finance_transactions` | 5,727 条 | 2026-03 ~ 2026-07 |
| 退货 | `returns` | 363 条 | 2026-03 ~ 2026-07 |
| 广告 | `ad_campaigns` + `ad_daily_stats` + `ad_sku_daily_stats` | 101 活动 / 1,011 条 / 1,412 条 | 2026-04-01 ~ 2026-07-16 |
| 汇总 | `sku_daily_summary` | 2,868 行 | 2026-03-24 ~ 2026-07-16 |

---

## 四块数据关系

```
                    ┌──────────────────────┐
                    │     products          │
                    │   (商品主数据)         │
                    │   sku_id 为主键       │
                    │   39 个 SKU           │
                    └──────────┬───────────┘
                               │ sku_id
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ▼                  ▼                  ▼
   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
   │   postings   │   │   finance_   │   │   returns    │
   │   (订单)     │   │ transactions │   │   (退货)     │
   │             │   │   (财务)     │   │              │
   │ 1,934 条    │◄──│  5,727 条    │──►│   363 条     │
   │             │   │              │   │              │
   │ 主键:       │   │ 主键:        │   │ 主键: id     │
   │ posting_    │   │ operation_id │   │ 关联:        │
   │ number      │   │ 关联:        │   │ posting_     │
   └──────┬──────┘   │ posting_     │   │ number       │
          │          │ number       │   │ sku          │
          │          └──────────────┘   └──────────────┘
          │ posting_number
          │
          └────────────→  returns 表通过 posting_number 关联 posting 表
                          posting 表通过 posting_number 关联 finance 表
                          所有表通过 sku_id/sku 关联 products 表
```

### 关联方式

| 从 → 到 | 关联字段 | 关系 |
|---------|---------|------|
| postings → products | `postings.products[].sku` → `products.sku_id` | 多对多（一个 posting 可含多个 SKU） |
| postings → returns | `postings.posting_number` → `returns.posting_number` | 一对一（一个 posting 最多一个 return） |
| finance_transactions → postings | `finance_transactions.posting_number` → `postings.posting_number` | 多对一（一笔订单对应多笔财务流水） |
| finance_transactions → products | `finance_transactions.sku_id` → `products.sku_id` | 多对一 |
| returns → products | `returns.sku` → `products.sku_id` | 多对一 |
| ad_campaign_sku_map → products | `ad_campaign_sku_map.sku_id` → `products.sku_id` | 多对一 |
| ad_sku_daily_stats → products | `ad_sku_daily_stats.sku_id` → `products.sku_id` | 多对一 |
| ad_daily_stats → ad_campaigns | `ad_daily_stats.campaign_id` → `ad_campaigns.campaign_id` | 多对一 |

---

## 1. 商品

### products 表 — 商品主数据

- **39 个 SKU**，来源 Ozon `/v3/product/info/list`
- 核心字段：`sku_id`、`name`、`offer_id`、`price`、`primary_image`、`commission_fbo_pct`
- 特点：数据变化慢，同步时全量刷新

### stocks 表 — 库存快照

- 来源：`/v3/product/info/list` 中的 `stocks.stocks[]`
- 区分 `fbo` / `fbs` 两种库存源
- 字段：`sku_id`、`source`、`present`（现有）、`reserved`（已预留）

---

## 2. 订单

### postings 表 — 订单履约

- **1,934 条**，来源 `/v2/posting/fbo/list` + `/v3/posting/fbs/list`
- 10 个字段，见 [app/models.py:102](app/models.py#L102)

#### 状态分布

| 状态 | 数量 | 说明 |
|------|------|------|
| `delivered` | 1,493 | 已签收（成交） |
| `cancelled` | 350 | 已取消 |
| `delivering` | 84 | 运输中 |
| `awaiting_deliver` | 6 | 等待发货 |
| `awaiting_packaging` | 1 | 等待打包 |

#### 履约漏斗

```
下单 → 处理(in_process_at) → 等待发货 → 运输中 → 已签收(delivered_at)
                                                 ↘ 取消 + 退货
```

#### 核心字段

| 字段 | 说明 |
|------|------|
| `posting_number` | 主键，发货单号 |
| `order_number` | 订单号（一个订单可拆多个 posting） |
| `delivery_schema` | FBO / FBS |
| `status` | 当前状态 |
| `created_at` | 下单时间 |
| `in_process_at` | 开始处理时间 |
| `delivered_at` | 签收时间 |
| `cancel_reason_id` | 取消原因 ID（数字，需 join returns 表获取可读原因） |
| `products` | JSON: `[{sku, name, quantity, offer_id, price}]` |

#### 数据补全

| 分析需求 | 用到的 join |
|---------|------------|
| 实际收入 | join `finance_transactions` on `posting_number`，取 `OperationAgentDeliveredToCustomer` |
| 取消原因 | join `returns` on `posting_number`，取 `return_reason_name`（`type=Cancellation`） |
| 商品中文名/图片 | join `products` on `sku` |

---

## 3. 财务

### finance_transactions 表 — 财务流水

- **5,727 条**，来源 `/v3/finance/transaction/list`

#### 大类分布

| type | 数量 | 说明 |
|------|------|------|
| `other` | 1,818 | 仓储费、包装费、销毁费、银行手续费等 |
| `orders` | 1,753 | 销售订单（`OperationAgentDeliveredToCustomer`） |
| `services` | 1,190 | 物流、分拣等服务费 |
| `returns` | 965 | 退货退款流水（`OperationItemReturn` + `ClientReturnAgentOperation`） |
| `compensation` | 1 | 赔偿 |

#### 核心字段

| 字段 | 说明 |
|------|------|
| `operation_id` | 主键 |
| `operation_type` | 操作类型代码 |
| `type` | 大类: orders / returns / services / other |
| `operation_date` | 发生日期 |
| `sku_id` | 关联 SKU |
| `posting_number` | 关联订单 |
| `amount` | 金额（正=收入，负=支出） |
| `sale_commission` | 销售佣金 |
| `delivery_charge` / `return_delivery_charge` | 物流费 / 退货物流费 |
| `services` | JSON: 服务明细列表 |

---

## 4. 退货

### returns 表 — 退货数据

- **363 条**，来源 `/v1/returns/list`
- 12 个字段，见 [app/models.py](app/models.py#L248)

#### type × 状态

| type | 数量 | 说明 |
|------|------|------|
| `Cancellation` | 304 | 未签收退回（拒收 / 未取件 / 取消订单） |
| `ClientReturn` | 59 | 签收后发起退货（质量 / 损坏 / 发错 / 假货） |

#### 退货原因（ClientReturn 59 条）

| 原因 | 数量 | 分类 |
|------|------|------|
| Покупатель передумал（改变主意） | 28 | 客户原因 |
| Упаковка и товар повреждены（包装商品损坏） | 14 | 物流/质量问题 |
| Покупатель получил не те товары（收到错误商品） | 6 | 仓库问题 |
| Товар в неполной комплектации（缺配件） | 4 | 仓库问题 |
| Товар поврежден, но упаковка цела（包装完好、商品损坏） | 3 | 质量问题 |
| Товар не работает / брак（故障） | 3 | 质量问题 |
| Товар поддельный（假货） | 1 | 质量问题 |

#### 状态分布（9 种状态）

| 状态 | 数量 | 是否为终态 |
|------|------|-----------|
| `ReturnedToOzon` | 310 | ✓ |
| `Utilized` | 26 | ✓ |
| `ArrivedAtReturnPlace` | 8 | — |
| `MovingToOzon` | 5 | — |
| `ReceivedBySeller` | 5 | ✓ |
| `MovingToSeller` | 3 | — |
| `WaitingShipment` | 3 | — |
| `Utilizing` | 2 | — |
| `WriteOff` | 1 | ✓ |

---

## 5. 广告

### 数据来源

- **Performance API** (`https://api-performance.ozon.ru`)，OAuth 2.0 client_credentials 认证
- SDK 客户端: [app/clients/perf.py](app/clients/perf.py)

### 四张表

| 表 | 说明 | 记录数 | 更新方式 |
|------|------|:---:|------|
| `ad_campaigns` | 广告活动主数据（名称、预算、状态） | 101 | 全量刷新 |
| `ad_daily_stats` | 活动级每日统计（展示/点击/花费/订单） | 1,011 | 每日增量 |
| `ad_campaign_sku_map` | 活动 ↔ SKU 映射（活动推广了哪些商品） | 20 | 按活动查询 |
| `ad_sku_daily_stats` | SKU 级每日统计（含 CTR、加购、订单数） | 1,412 | 异步报告逐日拉取 |

### 数据链路

```
Performance API
    │
    ├── GET /api/client/statistics/daily → CSV → ad_daily_stats (活动级每日汇总)
    ├── GET /api/client/campaign             → ad_campaigns (活动列表)
    ├── POST /api/client/campaign/{id}/sku   → ad_campaign_sku_map (活动-SKU 映射)
    └── POST /api/client/statistics          → UUID → poll → ZIP → ad_sku_daily_stats (SKU 级明细)
```

### ad_sku_daily_stats 核心字段

| 字段 | 说明 |
|------|------|
| `campaign_id` | 广告活动 ID（composite key） |
| `sku_id` | 关联 products.sku_id（composite key） |
| `stat_date` | 统计日期（composite key） |
| `impressions` | 展示量 |
| `clicks` | 点击量 |
| `ctr` | 点击率 |
| `avg_cpc` | 平均 CPC |
| `spend` | 花费（RUB） |
| `sold_units` | 广告直接成交件数 |
| `total_ordered` | 广告带来的总订单金额 |
| `drr_total` | DRR = spend / total_ordered（广告费占比） |

### 异步报告限制

- 每种凭证每天有请求配额限制
- 同一时间仅允许 **1 个活跃异步报告**
- 每个异步报告最多 **10 个活动**
- 报告有效期约 5 分钟，超时 UUID 失效返回 404
- 建议逐天请求，23 个活动约 3 批/天 ≈ 6~10 分钟/天

### 汇总逻辑

广告费用从 `ad_sku_daily_stats` 按 SKU+日期聚合 `spend`，写入 `sku_daily_summary.advertising`。

广告模块同步脚本:
- `scripts/backfill_ad_sku.py` — 历史数据回填
- `app/services/advertising_sync.py` — 每日自动同步

---

## 6. 汇总

### sku_daily_summary 表 — SKU 日汇总

- **2,868 行**，2026-03-24 ~ 2026-07-16（约 115 天）
- 由四块数据聚合而成，自动构建

#### 字段来源映射

| 字段 | 数据来源 |
|------|---------|
| `ordered_units`、`revenue` | 销售分析 API → analytics 数据 |
| `delivered_units`、`cancelled_units` | postings 表聚合 |
| `commissions`、`logistics_costs` | finance_transactions 聚合 |
| `returns_amount`、`returns_units` | finance_transactions 退货流水 |
| `storage_fees`、`other_costs` | finance_transactions 聚合 |
| `advertising` | ad_sku_daily_stats 按 SKU+日期聚合 spend |
| `stock_present`、`stock_reserved` | stocks 表快照 |
| `net_profit`、`profit_margin` | 计算: revenue + 各项费用 |

#### 数据质量

- 早期数据：`data_quality = "partial"`（仅有销售数据，无财务）
- 近期数据：`data_quality = "complete"`（销售 + 财务齐全）

---

## 同步流程

```
run_full_sync (sync_service.py)
├── 1. products      → 全量刷新商品 + 库存
├── 2. analytics     → 销售数据（最近 500 天）
├── 3. finance       → 财务流水（最近 500 天）
├── 4. postings      → 订单履约（最近 30 天增量 + 补齐缺失）
├── 5. returns       → 退货数据（最近 90 天）
├── 6. advertising   → 广告活动 + 每日统计
├── 7. ad_sku_daily  → 广告 SKU 明细（最近 3 天）
└── 8. summary       → 构建 sku_daily_summary
```

定时执行：每天 5:00 和 16:00（`sync_cron_hours: "5,16"`）
