# 利润模块实现计划

## 背景

现有的 `sku_daily_summary` 表已有 `net_profit` / `profit_margin` 字段，但成本/利润计算可能不准确。用户希望从原始数据（`finance_transactions` + `postings` + `ad_sku_daily_stats`）重新聚合利润，独立验证并纠正现有数据。

## 目标

在 Dashboard 新增「利润分析」Tab，从原始表直接聚合利润数据，展示:
1. 利润概览 KPI 卡片（收入、净利润、利润率、总费用）
2. 收入 & 利润趋势图（ECharts 多线图）
3. SKU 利润排行表

---

## 新增文件

### 1. `app/schemas/profit.py` — 利润 API 响应模型

```
ProfitOverview: revenue, net_profit, profit_margin, total_costs, total_commissions,
                total_logistics, total_storage, total_advertising, total_promotion,
                total_returns, total_other, ordered_units, sku_count, day_count

ProfitTrendItem: date, revenue, costs (总费用，正数), net_profit, profit_margin

ProfitSkuItem: sku_id, offer_id, name, primary_image, revenue, costs, net_profit,
               profit_margin, ordered_units, commissions, logistics_costs, storage_fees,
               advertising, promotion_costs, returns_amount, other_costs
```

### 2. `app/api/profit.py` — 利润 API 路由

三个端点，全部从原始表聚合:

**`GET /profit/overview`**
- Revenue: `SUM(ft.accruals_for_sale)` WHERE type='orders'
- Commissions: `SUM(ft.sale_commission)` WHERE OperationAgentDeliveredToCustomer
- Logistics: 从 `ft.services` JSON 提取含 "Logistic" 条目
- Storage: `SUM(ft.amount)` WHERE operation_type LIKE '%TemporaryStorage%'
- Returns: `SUM(ft.amount)` WHERE OperationItemReturn / ClientReturnAgentOperation
- Promotion: `SUM(ft.amount)` WHERE OperationPromotionWithCostPerOrder
- Advertising: `SUM(ad_sku_daily_stats.spend)` + SEARCH_PROMO 按日 revenue 分摊
- Other: 剩余负 amount
- 日期归因: 有 posting_number → `postings.created_at`，无 → `operation_date`

**`GET /profit/trend`** — 按日聚合，返回 `ProfitTrendItem[]`

**`GET /profit/sku-ranking`** — 按 SKU 聚合，返回 `ProfitSkuItem[]`，含 product 表 join 拿名称/图片

所有端点接受: `date_from`, `date_to`, `store_id` (默认1, 0=全部), 可选 `sku_id`

### 3. `frontend/src/components/ProfitAnalysis.vue` — 利润分析组件

结构:
```
┌──────────────────────────────────────────────┐
│  [收入]  [净利润]  [利润率]  [总费用]  4张KPI卡片 │
├──────────────────────────────────────────────┤
│          收入 & 利润趋势图 (ECharts)            │
│    折线: 收入(蓝) 费用(红) 净利润(绿)            │
├──────────────────────────────────────────────┤
│          SKU 利润排行表 (el-table)             │
│  排名 | 图片 | SKU | 货号 | 名称 | 收入 |      │
│  净利 | 利润率 | 佣金 | 物流 | 广告 | 退货      │
└──────────────────────────────────────────────┘
```

- KPI 卡片用 `el-row` + `el-card`（参考 SummaryCards 风格）
- 趋势图用 ECharts，三线（revenue/costs/net_profit），含 area fill
- SKU 表格默认按净利润降序，支持排序
- 利润率用 `el-tag` 颜色: ≥20% 绿, ≥0% 橙, <0% 红
- 金额用俄语 locale 格式化 `₽ 1 234,56`
- 可下钻到单个 SKU 的每日利润明细（弹窗）

---

## 修改文件

### 4. `app/api/__init__.py`

加两行:
```python
from app.api.profit import router as profit_router
api_router.include_router(profit_router)
```

### 5. `frontend/src/types/index.ts`

新增:
```typescript
export interface ProfitOverview { revenue: number; net_profit: number; ... }
export interface ProfitTrendItem { date: string; revenue: number; costs: number; net_profit: number; profit_margin: number }
export interface ProfitSkuItem { sku_id: number; ... 同后端 }
```

### 6. `frontend/src/api/index.ts`

新增三个 API 函数:
- `getProfitOverview(dateFrom?, dateTo?, storeId?) → Promise<ProfitOverview>`
- `getProfitTrend(dateFrom?, dateTo?, storeId?) → Promise<ProfitTrendItem[]>`
- `getProfitSkuRanking(dateFrom?, dateTo?, storeId?) → Promise<ProfitSkuItem[]>`

### 7. `frontend/src/views/Dashboard.vue`

- import ProfitAnalysis
- 在 `<el-tabs>` 中新增 `el-tab-pane`（放在第一个或成本分析前面）
- 若需要，让利润分析 Tab 成为默认 `activeTab`

---

## 实现顺序

1. **后端 Schema** → `app/schemas/profit.py`
2. **后端 API** → `app/api/profit.py`（核心：从原始表聚合利润）
3. **注册路由** → `app/api/__init__.py`
4. **前端类型** → `frontend/src/types/index.ts`
5. **前端 API** → `frontend/src/api/index.ts`
6. **前端组件** → `frontend/src/components/ProfitAnalysis.vue`
7. **集成** → `frontend/src/views/Dashboard.vue`

---

## 利润聚合 SQL 核心逻辑

```sql
-- Revenue: 按 posting.created_at 日期归因
SELECT p.created_at::date AS order_date, ft.sku_id,
       SUM(ft.accruals_for_sale) AS revenue
FROM ozon.finance_transactions ft
JOIN ozon.postings p ON ft.posting_number = p.posting_number
WHERE ft.type = 'orders' AND ft.store_id = :sid
  AND p.created_at >= :d1 AND p.created_at < :d2
GROUP BY p.created_at::date, ft.sku_id

-- Costs: 同样按 posting.created_at 归因
-- commissions = sale_commission (OperationAgentDeliveredToCustomer)
-- logistics = services JSON 含 "Logistic" 条目的 price 合计
-- storage = amount (TemporaryStorage)
-- returns = amount (OperationItemReturn / ClientReturnAgentOperation)
-- promotion = amount (OperationPromotionWithCostPerOrder)
-- advertising = ad_sku_daily_stats.spend + SEARCH_PROMO 分摊
-- other = 剩余负 amount

-- 无 posting_number 的费用按 operation_date 归因
```

---

## 验证方式

1. 启动后端 `uvicorn app.main:app --reload`
2. 调用 `GET /api/v1/profit/overview?date_from=2026-07-01&date_to=2026-07-28` 确认返回数据
3. 调用 `GET /api/v1/profit/trend` 确认逐日趋势数据
4. 启动前端 `npm run dev`，切换到「利润分析」Tab
5. 对比新聚合数据与现有 Dashboard「全部数据」Tab 的 SKU 汇总（看 net_profit 差异）
6. 用 `scripts/check_commission.py` 交叉验证佣金数据
