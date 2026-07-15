# Ozon Performance API（广告API）分析报告

> 测试日期: 2026-07-14 · 店铺: Тихое Счастье · 脚本: `sandbox/03_test_advertising.py`

---

## 1. API 端点总览

| 端点 | 方法 | 返回格式 | 用途 |
|------|------|---------|------|
| `/api/client/token` | POST | JSON | OAuth 2.0 认证（30分钟有效） |
| `/api/client/campaign` | GET | JSON `{list, total}` | 广告活动列表 |
| `/api/client/statistics/daily` | GET | **CSV** | 每日广告统计（按活动×日期） |

CSV 字段: `ID;Название;Дата;Показы;Клики;Расход, ₽;Заказы, шт.;Заказы, ₽`

---

## 2. 数据现状

### 2.1 活动概况（101个活动）

| 类型 | 数量 | 有标题 | 说明 |
|------|:---:|:---:|------|
| `REF_VK` | 56 | 0 | VK社交推广（自动创建，无标题，budget=0） |
| `SKU` | 22 | 20 | **按商品推广**（标题含 offer_id 前缀） |
| `REF_BLOGGER` | 21 | 0 | 博主推广（自动创建，无标题，budget=0） |
| `SEARCH_PROMO` | 1 | 1 | 搜索推广：全店商品 |
| `ALL_SKU_PROMO` | 1 | 1 | 全商品按单付费推广 |

**运行中**: 84个 | **已归档**: 11个 | **未激活**: 6个

**关键发现**: REF_VK 和 REF_BLOGGER（共77个活动）budget=0，CSV 统计中也没有这些活动的花费数据。实际产生花费的只有 SKU 类型（22个）和 SEARCH_PROMO（1个）。

### 2.2 8天实际花费（7月7日~14日）

| 指标 | Performance API | Finance API (相同时间段) |
|------|:---:|:---:|
| **总花费** | **33,799 ₽** | **16,034 ₽** |
| 记录数 | 90条 (campaign×day) | 70条 (transaction) |
| 数据粒度 | 按活动ID+日期 | 按 operation_id |
| 记录来源 | Performance API 报表 | `OperationMarketplaceCostPerClick` |

**差异（~2倍）**: Finance API 只捕获了 `OperationMarketplaceCostPerClick`（点击付费），但 Performance API 包含 `SEARCH_PROMO`（搜索推广按单付费 `OperationPromotionWithCostPerOrder`）以及可能的其他计费方式。

### 2.3 Finance API 广告数据核心问题

```sql
-- OperationMarketplaceCostPerClick 总计 847 条
-- 其中 sku_id IS NOT NULL 的: 0 条 ← 全部没有 SKU 关联！
```

这意味着 Finance API 返回的广告费用记录 **无法直接分配到具体 SKU**，因此在 `sku_daily_summary` 中 `advertising` 字段目前全是 0。

---

## 3. Campaign → SKU 映射分析

### 3.1 映射规则

SKU 类型活动的标题格式: `{offer_id前缀}-{中文商品名}`，例如:
- `"38797-（黑绿紫）拼图板"` → offer_id=`38797-Y07U0001-A01` → sku_id=`3629891330`

**映射方法**: 取 campaign 标题中 `-` 之前的数字部分，在 `products` 表中匹配 `offer_id` 前缀。

### 3.2 匹配结果

| 活动ID | 活动标题 | offer_id前缀 | DB匹配 | sku_id |
|--------|---------|:---:|:---:|--------|
| 23719961 | 38797-（黑绿紫）拼图板 | 38797 | ✅ | 3629891330 |
| 23760745 | 4002-展示盒组合 | 4002 | ⚠️ | DB是 40002（少一个0） |
| 24050946 | 37965-透明仓鼠笼 | 37965 | ✅ | 3828092422 |
| 24459086 | 37053-金属仓鼠笼 | 37053 | ✅ | 3828469066 |
| 25418895 | 31853-绿黑拼图垫 | 31853 | ✅ | 3625849128 |
| 25479666 | 28180-拼图板清货 | 28180 | ✅ | 3645735675 |
| 27304506 | 35352-面包罩 | 35352 | ✅ | 4245380491 |
| 27392176 | 40243-唱片架 | 40243 | ✅ | 3787642179 |
| 28682272 | 33367-亚克力仓鼠笼 | 33367 | ✅ | 3827770156 |
| 31721254 | 40218-茶包架 | 40218 | ✅ | 4525296761 |
| 31893433 | 39842-三层唱片机架 | 39842 | ✅ | 4525217472 |
| 28603236 | 33386-蓝色金属仓鼠笼子 | 33386 | ✅ | 3828309212 |
| 29086498 | 40002-其他展示盒组合 | 40002 | ✅ | 3648377250 |
| 26969536 | 21071-票夹 | 21071 | ❌ | DB无此前缀 |
| ... | ... | | | |

**结论**: **22个SKU活动中，绝大多数（~90%）可以通过 offer_id 前缀直接匹配到 products.sku_id**。少数不匹配需要人工修正。

### 3.3 不可分配的活动

| 活动ID | 标题 | 类型 | 花费(8天) | 处理方式 |
|--------|------|------|:---:|------|
| 23719965 | Оплата за заказ — все товары | SEARCH_PROMO | 17,183 ₽ | 按SKU销售额比例分摊 |
| 24524152 | Оплата за заказ - все товары | ALL_SKU_PROMO | 0 ₽ | （未激活，跳过） |

SEARCH_PROMO 花费占总花费的 **50.8%**，是最大的广告支出。它推广的是全店商品，无法直接对应到某个SKU，需要按比例分摊。

---

## 4. 推荐方案

### 方案: 建立 Performance API 同步服务 + Campaign-SKU 映射

#### 4.1 数据流

```
Performance API                          DB
┌─────────────────┐        ┌──────────────────────────┐
│ /statistics/daily│  CSV   │ advertising_campaign_stats │ ← 新表（活动日统计）
└─────────────────┘   →    │  - campaign_id             │
                           │  - campaign_name           │
┌─────────────────┐        │  - date                    │
│ /campaign        │  JSON  │  - impressions            │
└─────────────────┘   →    │  - clicks                  │
                           │  - cost                    │
                           │  - orders                  │
                           │  - order_revenue           │
                           └──────────────────────────┘
                                      │
                           ┌──────────▼──────────────┐
                           │ campaign_sku_mapping     │ ← 新表（活动→SKU映射）
                           │  - campaign_id           │
                           │  - sku_id                │
                           │  - match_method          │ (auto/manual/proportional)
                           │  - allocation_ratio      │
                           └──────────────────────────┘
                                      │
                           ┌──────────▼──────────────┐
                           │ sku_daily_summary        │ ← 更新 advertising 字段
                           │  .advertising = cost     │
                           └──────────────────────────┘
```

#### 4.2 映射策略（优先级从高到低）

1. **自动匹配** (SKU campaigns): 从活动标题解析 offer_id 前缀 → `products.offer_id LIKE 'prefix%'` → 得到 sku_id
2. **手动映射** (不匹配的 SKU campaigns): 维护一个 campaign_sku_mapping 表，管理员可手工关联
3. **比例分摊** (SEARCH_PROMO / ALL_SKU_PROMO): 按当日各 SKU 的 `revenue` 占总销售额的比例，将花费分摊到所有 SKU

#### 4.3 建议入库的字段

| 字段 | 来源 | 类型 | 说明 |
|------|------|------|------|
| campaign_id | CSV.ID | varchar(20) | 活动ID |
| campaign_name | CSV.Название | text | 活动名称 |
| date | CSV.Дата | date | 统计日期 |
| impressions | CSV.Показы | integer | 展示量 |
| clicks | CSV.Клики | integer | 点击量 |
| cost | CSV.Расход, ₽ | numeric(12,2) | 广告花费(RUB) |
| orders | CSV.Заказы, шт. | integer | 广告带来的订单数 |
| order_revenue | CSV.Заказы, ₽ | numeric(12,2) | 广告带来的订单金额 |

#### 4.4 同步策略

- **频率**: 每天一次（广告数据按天聚合，实时性要求不高）
- **覆盖策略**: UPSERT（campaign_id + date 作为联合主键），避免重复
- **日期范围**: 拉取最近 30 天，覆盖延迟和补数据场景

---

## 5. 待决定事项

1. **SEARCH_PROMO 17,183 ₽（50%花费）的分摊方式**:
   - A) 按 revenue 比例分摊到所有有销售的商品
   - B) 当作"公司级费用"不分配到 SKU，仅在总看板中展示
   - C) 仅分摊到被该活动实际推广的商品（需要额外 API 获取活动内商品列表）

2. **与 Finance API 广告费的关系**: 当前 Finance API 的 `OperationMarketplaceCostPerClick` 虽然无法关联 SKU，但它是实际扣款记录（已结算）。Performance API 的数据可能是实时上报，并非最终结算金额。建议：
   - 每日看板用 Performance API 数据（更全、更及时）
   - 月度结算以 Finance API 为准
   - 两条数据线可交叉验证

3. **是否替换当前 summary_service 中的广告费逻辑**: 当前代码从 Finance API 聚合 `OperationMarketplaceCostPerClick`，但因 sku_id=None 导致 advertising 全为 0。如果用 Performance API 映射后数据替代，可以真正填充 advertising 字段。

---

## 6. 技术要点

### 认证
```python
# OAuth 2.0 Client Credentials
POST https://api-performance.ozon.ru/api/client/token
Body: {client_id, client_secret, grant_type: "client_credentials"}
→ {access_token, token_type: "Bearer", expires_in: 1800}  # 30分钟过期
```

### 统计数据获取
```python
# GET 请求 (非POST)，参数在 query string
GET https://api-performance.ozon.ru/api/client/statistics/daily?from=2026-06-14&to=2026-07-14
Header: Authorization: Bearer {token}
→ CSV 文本 (Content-Type: text/csv)
```

### CSV 解析注意事项
- 分隔符: `;` (分号)
- 数字格式: 俄式（`,` 为小数点分隔符），需 replace
- 编码: UTF-8
- 表头有特殊字符（₽）

---

## 7. 下一步

1. 创建 `advertising_campaign_stats` 和 `campaign_sku_mapping` 两张表
2. 实现 `app/services/advertising_sync.py` — 同步 Performance API 数据
3. 实现 campaign → SKU 自动映射逻辑
4. 更新 `summary_service.py`，使用映射后的广告数据填充 `sku_daily_summary.advertising`
5. 前端看板增加广告 ROI 视图（花费 vs 订单金额）

**等待用户确认后开始实现。**
