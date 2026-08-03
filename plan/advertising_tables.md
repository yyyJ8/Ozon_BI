# 广告数据表结构文档

> 数据库: `ai_application` | Schema: `ozon` | 共 4 张表  
> 数据来源: [Ozon Performance API](https://api-performance.ozon.ru)（OAuth 2.0 独立认证）  
> 更新日期: 2026-07-31

---

## 表关系概览

```
ad_campaigns (活动主数据)
    │
    ├── ad_daily_stats (活动×天统计, 来自 GET /statistics/daily CSV)
    │       │
    │       └── ad_campaign_sku_map ──┐
    │           (活动→SKU映射)        │
    │                                │
    └── ad_sku_daily_stats ──────────┘
        (SKU×天明细, 来自 POST /statistics 异步报告)

最终归宿 → sku_daily_summary.advertising (SKU日汇总中的广告费字段)
```

---

## 1. ad_campaigns — 广告活动主数据

**来源**: `GET /api/client/campaign`  
**行数**: 164  
**简介**: 从 Ozon Performance API 拉取的所有广告活动。每个活动一行，记录活动类型、状态和预算。活动类型决定该活动能否关联到具体 SKU（SKU 类型可关联，REF_VK/REF_BLOGGER 不可关联）。

| 字段 | 类型 | 中文说明 | 示例 1 | 示例 2 |
|---|---|---|---|---|
| `campaign_id` | `varchar(20)` PK | 活动 ID（Ozon 唯一标识） | `25216577` | `23719965` |
| `title` | `text` | 活动标题（SKU 类含 offer_id 前缀） | `38555-立体拼图垫` | `Оплата за заказ — все товары` |
| `campaign_type` | `varchar(50)` | 活动类型 | `SKU` | `REF_VK` |
| `state` | `varchar(50)` | 活动状态 | `CAMPAIGN_STATE_RUNNING` | `CAMPAIGN_STATE_ARCHIVED` |
| `budget` | `numeric(12,2)` | 活动预算（RUB，0=无上限） | `0.00` | `5000.00` |
| `created_at` | `timestamp` | 记录创建时间 | `2026-07-16 10:10:18` | `2026-07-22 09:02:15` |
| `updated_at` | `timestamp` | 记录更新时间 | `2026-07-16 10:10:18` | `2026-07-22 09:02:15` |
| `store_id` | `integer` | 店铺 ID（多店铺隔离） | `1` | `1` |

**活动类型说明**:

| 类型代码 | 含义 | 可关联 SKU |
|---|---|---|
| `SKU` | SKU 单品推广 | ✅ 通过标题提取 offer_id 前缀匹配 |
| `SEARCH_PROMO` | 搜索推广 | ❌ |
| `ALL_SKU_PROMO` | 全店推广 | ❌ |
| `REF_VK` | VK 社交引荐 | ❌ |
| `REF_BLOGGER` | 博主引荐 | ❌ |
| `BANNER` | 横幅广告 | ❌ |

**数据分布** (2026-07-31):

| 类型 | 数量 | 运行中 |
|---|---|---|
| REF_VK | 76 | 76 |
| SKU | 53 | 20 |
| REF_BLOGGER | 30 | 30 |
| ALL_SKU_PROMO | 2 | 0 |
| SEARCH_PROMO | 2 | 2 |
| BANNER | 1 | 1 |

---

## 2. ad_daily_stats — 活动每日统计

**来源**: `GET /api/client/statistics/daily?dateFrom=...&dateTo=...`（返回分号分隔 CSV）  
**行数**: 2,320  
**日期范围**: 2026-03-13 ~ 2026-07-31  
**简介**: 每个活动每天的汇总统计，包含花费、展示、点击、订单等核心指标。数据通过 Ozon 同步端点获取，速度快（~3 秒），支持最多约 45 天范围。**spend 存储为正值**，聚合到 `sku_daily_summary` 时取负。

| 字段 | 类型 | 中文说明 | 示例 1 | 示例 2 |
|---|---|---|---|---|
| `campaign_id` | `varchar(20)` PK | 活动 ID | `23719961` | `23719965` |
| `stat_date` | `date` PK | 统计日期 | `2026-07-22` | `2026-07-22` |
| `impressions` | `integer` | 展示量 | `1,552` | `1,640` |
| `clicks` | `integer` | 点击量 | `56` | `20` |
| `spend` | `numeric(12,2)` | 广告花费 RUB（**正数**） | `56.00` | `3,212.40` |
| `orders_count` | `integer` | 广告带来的订单数 | `2` | `7` |
| `orders_sum` | `numeric(12,2)` | 广告带来的订单金额 RUB | `4,560.00` | `32,124.00` |
| `synced_at` | `timestamp` | 最后同步时间 | `2026-07-22 09:02:15` | `2026-07-22 09:02:15` |
| `store_id` | `integer` | 店铺 ID | `1` | `1` |

**对应 CSV 俄文表头**:
`ID;Название;Дата;Показы;Клики;Расход,₽;Заказы,шт.;Заказы,₽`

---

## 3. ad_campaign_sku_map — 活动→SKU 映射表

**来源**: 系统自动构建（同步过程中从活动标题提取 offer_id 前缀匹配 products 表）  
**行数**: 50  
**简介**: 建立广告活动与 SKU 之间的多对多关系。对于 `campaign_type = 'SKU'` 的活动，从标题提取 offer_id 前缀（如 `38555`），在 `products` 表中查找 `offer_id LIKE '38555-%'` 的商品，自动建立映射。这是广告费归因到 SKU 的关键桥梁。

| 字段 | 类型 | 中文说明 | 示例 1 | 示例 2 |
|---|---|---|---|---|
| `campaign_id` | `varchar(20)` PK | 活动 ID | `31893433` | `31721254` |
| `sku_id` | `bigint` PK | SKU 编号（Ozon 唯一标识） | `4525217472` | `4525296761` |
| `offer_id` | `varchar(255)` | 商家自定义商品编码（冗余，便于查询） | `39842-Y07U0002-C02` | `40218-Y07U0001-C02` |
| `mapping_method` | `varchar(20)` | 映射方式 | `auto` | `auto` |
| `created_at` | `timestamp` | 映射创建时间 | `2026-07-16 10:10:21` | `2026-07-16 10:10:21` |
| `store_id` | `integer` | 店铺 ID | `1` | `1` |

**映射方式**:
- `auto` — 从活动标题自动提取 offer_id 前缀匹配
- `manual` — 人工指定（暂未使用）

**当前状态**: 50 个活动已映射，覆盖 48 个 SKU。164 个活动中剩余 114 个（REF_VK/REF_BLOGGER/SEARCH_PROMO 等）无法映射到具体 SKU。

> ⚠️ **注意**: 当一个活动匹配到多个 SKU（多个产品共享同一 offer_id 前缀），广告费会被**均分**到各个 SKU。

---

## 4. ad_sku_daily_stats — SKU 广告日明细

**来源**: `POST /api/client/statistics` → 异步轮询 → 下载 ZIP → 解压 CSV  
**行数**: 2,499  
**日期范围**: 2026-04-01 ~ 2026-07-30  
**简介**: 每个活动内每个 SKU 的每日详细广告数据，包含 CTR、CPC、加购、DRR 等深度指标。这是最细粒度的广告数据，但获取极慢——Ozon 异步生成报告，每批（最多 10 个活动）排队 200~300 秒，23 个活动约需 11 分钟/天。

| 字段 | 类型 | 中文说明 | 示例 1 | 示例 2 |
|---|---|---|---|---|
| `campaign_id` | `varchar(20)` PK | 活动 ID | `28682272` | `25479691` |
| `sku_id` | `bigint` PK | SKU 编号 | `3828092422` | `3659251893` |
| `stat_date` | `date` PK | 统计日期 | `2026-06-11` | `2026-06-11` |
| `sku_name` | `text` | SKU 名称（俄文原文） | `Пластиковый контейнер...` | `Силикон-коврик для...` |
| `sku_price` | `numeric(12,2)` | SKU 单价 RUB | `5450.00` | `6500.00` |
| `impressions` | `integer` | 展示量 | `1,475` | `32` |
| `clicks` | `integer` | 点击量 | `33` | `1` |
| `ctr` | `numeric(8,4)` | 点击率（%） | `2.24` | `3.13` |
| `add_to_cart` | `integer` | 加入购物车次数 | `3` | `0` |
| `avg_cpc` | `numeric(12,2)` | 平均单次点击费用 RUB | `6.05` | `1.00` |
| `spend` | `numeric(12,2)` | 广告花费 RUB（**正数**） | `199.50` | `1.00` |
| `sold_units` | `integer` | 推广直接售出件数 | `0` | `0` |
| `sales_promotion` | `numeric(12,2)` | 推广直接销售额 RUB | `0.00` | `0.00` |
| `total_ordered` | `numeric(12,2)` | 该 SKU 总订单金额 RUB | `0.00` | `0.00` |
| `drr_promotion` | `numeric(8,4)` | 推广 DRR（花费/推广收入，%） | `2.60` | `0.00` |
| `drr_total` | `numeric(8,4)` | 总 DRR（花费/总订单收入，%） | `0.00` | `0.00` |
| `date_added` | `date` | SKU 加入活动日期 | `0001-01-01` | `2026-04-25` |
| `synced_at` | `timestamp` | 最后同步时间 | `2026-07-17 11:44:28` | `2026-07-17 11:44:28` |
| `store_id` | `integer` | 店铺 ID | `1` | `1` |

**对应 CSV 俄文表头**:
`sku;Название товара;Цена товара,₽;Показы;Клики;CTR,%;Добавления в корзину;Средняя стоимость клика,₽;Расход,₽,с НДС;Продано товаров;Продажи в продвижении,₽;Продано товаров модели;Продажи в продвижении с заказов модели,₽;ДРР в продвижении,%;Заказано на сумму,₽;ДРР (общий),%;Дата добавления`

> ⚠️ **注意**: 异步报告跳过汇总行（`sku="Всего"`）和修正行（`sku="Корректировка"`）。`date_added` 为 `0001-01-01` 时表示 Ozon 未返回该字段或数据异常。

**当前覆盖**: 65 个 SKU、51 个活动。

---

## 同步时间安排

| 时间 | 同步内容 | 耗时 |
|---|---|---|
| **5:00** | SKU 广告明细（`ad_sku_daily_stats`，仅昨天） | ~11 分钟 |
| 9:00 | 活动级统计（`ad_daily_stats`，最近 3 天）+ 映射 + 汇总 | ~3 秒 |
| 19:00 | 同上 | ~3 秒 |
| 手动 `POST /sync` | 全量含 SKU 明细 | 视范围而定 |

---

## 数据流

```
Ozon Performance API
    │
    ├── GET /campaign ──────────────────────────→ ad_campaigns
    │
    ├── GET /statistics/daily (CSV, 快速) ──────→ ad_daily_stats
    │       │
    │       ├── 自动匹配 ──→ ad_campaign_sku_map
    │       │
    │       └── CTE聚合+均分 ──→ sku_daily_summary.advertising
    │
    └── POST /statistics (异步, 极慢) ──────────→ ad_sku_daily_stats
            (仅凌晨5:00同步昨天, 用于前端 SKU级分析)
```
