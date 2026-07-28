# 异常模块实现计划

## 背景

用户需要在 Dashboard 中新增「异常预警」Tab，根据业务规则自动检测异常的 SKU 商品。规则定义在 YAML 配置文件中，改 YAML 即可调整阈值，不需要改代码。

---

## 规则分析

YAML 中定义了 6 条异常检测规则，涉及 3 个数据源：

| 规则 | 数据源 | 条件 | 周期 |
|------|--------|------|------|
| SKU退货异常 | `sku_daily_summary` | `returns_units ≥ 4 AND ordered_units ≥ 20` | 当月累计 |
| SKU利润率预警 | `sku_daily_summary` | `profit_margin < 10` (critical: <0, warning: <10) | 当月累计 |
| 广告DRR过高 | `ad_sku_daily_stats` | `drr_total ≥ 5 AND spend ≥ 500` | 当月累计 |
| 高点击低转化 | `ad_sku_daily_stats` | `ctr ≥ 3 AND spend ≥ 300 AND sold_units ≤ 5` | 当月累计 |
| SKU断货风险 | `stocks` | `present ≤ 10` | 实时快照 |
| SKU滞销积压 | `sku_daily_summary` | `ordered_units = 0 AND stock_present ≥ 20` | 当日 |

**数据源映射:**
- `get_daily_summary` → `ozon.sku_daily_summary` 表
- `get_ad_performance` → `ozon.ad_sku_daily_stats` 表
- `get_stock_snapshot` → `ozon.stocks` 表（当前库存实时数据）

---

## 新增文件

### 1. `app/anomaly_rules.yaml` — 异常规则配置文件

将用户提供的 YAML 配置落成文件，放在 `app/` 目录下，方便服务端读取。结构与用户给的一致，额外增加 `data_source_table` 映射。

```yaml
# OZON 业务口径配置
# 改 yaml 即可生效，不需要改代码。

data_sources:
  get_daily_summary:
    table: ozon.sku_daily_summary
    description: "SKU 日汇总表"
  get_ad_performance:
    table: ozon.ad_sku_daily_stats
    description: "广告 SKU 日明细表"
  get_stock_snapshot:
    table: ozon.stocks
    description: "库存实时快照"

anomaly_rules:
  SKU退货异常:
    type: "阈值"
    require: "all"
    data_source: get_daily_summary
    period: "monthly"          # 当月累计聚合
    conditions:
      - field: returns_units
        op: "gte"
        value: 4
      - field: ordered_units
        op: "gte"
        value: 20
    description: "退货 ≥4件 且 月订单 ≥20 单"

  SKU利润率预警:
    type: "阈值"
    require: "all"
    data_source: get_daily_summary
    period: "monthly"
    conditions:
      - field: profit_margin
        op: "lt"
        value: 10
    severity_map:
      critical: "< 0   → 亏损"
      warning: "< 10  → 利润过低"
    description: "利润率异常"

  # ... 其余 4 条规则同用户定义
```

### 2. `app/services/anomaly_service.py` — 异常检测引擎

核心服务，职责：

- **加载 YAML** — 启动时读 `app/anomaly_rules.yaml`，缓存规则
- **数据源查询** — 每个 `data_source` 对应一个查询方法：
  - `get_daily_summary` → 查询 `sku_daily_summary`，按 `store_id + sku_id` 聚合当月数据
  - `get_ad_performance` → 查询 `ad_sku_daily_stats`，按 `store_id + sku_id` 聚合当月数据
  - `get_stock_snapshot` → 查询 `stocks` 当前库存快照（SUM(present) GROUP BY store_id, sku_id）
- **条件判定** — 遍历每条规则，对查询结果逐行检查 conditions
- **严重程度** — 根据 `severity_map` 自动分级
- **结果组装** — 返回标准化异常列表，附带 product 表 join 拿名称/图片

```python
# 伪代码结构
def detect_anomalies(db, store_id, date_from, date_to):
    rules = load_yaml("app/anomaly_rules.yaml")
    results = []
    for rule_name, rule in rules["anomaly_rules"].items():
        data = query_data_source(db, rule["data_source"], store_id, date_from, date_to)
        for row in data:
            if all(apply_condition(row, c) for c in rule["conditions"]):
                severity = determine_severity(row, rule)
                results.append(AnomalyItem(sku_id=..., anomaly_type=rule_name, ...))
    return results
```

**关键实现细节:**
- 操作符映射: `gte`→`>=`, `lte`→`<=`, `gt`→`>`, `lt`→`<`, `eq`→`=`
- `period: "monthly"` → 在日期范围内 SUM 聚合后再判条件
- `period: "daily"` (滞销积压) → 按日判定，不做跨日聚合
- `period: "snapshot"` (断货风险) → 直接查 stocks 当前数据

### 3. `app/schemas/anomalies.py` — 异常 API 响应模型

```python
class AnomalyItem(BaseModel):
    """单条异常记录"""
    sku_id: int
    offer_id: str | None
    name: str | None
    primary_image: str | None
    anomaly_type: str              # 规则名称，如 "SKU退货异常"
    severity: str                  # "critical" | "warning" | "info"
    description: str               # 规则描述，如 "退货≥4件 且 月订单≥20单"
    metrics: dict[str, float]      # 触发时的实际指标值
    triggered_conditions: list[str]  # 命中的条件表达式

class AnomalySummary(BaseModel):
    """异常汇总统计"""
    total_anomalies: int
    by_type: dict[str, int]        # {"SKU退货异常": 3, ...}

class AnomalyResponse(BaseModel):
    """完整异常响应"""
    summary: AnomalySummary
    items: list[AnomalyItem]
```

### 4. `app/api/anomalies.py` — 异常 API 路由

```
GET /api/v1/anomalies
  参数: store_id (default=1, 0=全部), date_from?, date_to?
  返回: AnomalyResponse
```

默认日期范围：当月 1 号 → 昨天（因为今天数据不完整）。

如果 `date_from/date_to` 未传，自动取当月。

### 5. `frontend/src/components/AnomalyAnalysis.vue` — 异常分析组件

结构设计（纯 Element Plus 组件）:

```
┌──────────────────────────────────────────────────────┐
│  [异常总数]  [退货异常]  [利润率预警]  [DRR过高]     │
│  [高点击低转化]  [断货风险]  [滞销积压]             │
│  6 张统计卡片 (el-row + el-card)                    │
├──────────────────────────────────────────────────────┤
│  筛选栏: 异常类型(el-select) | 严重程度(el-select)   │
├──────────────────────────────────────────────────────┤
│  异常 SKU 列表 (el-table)                           │
│  图片 | SKU | 货号 | 名称 | 异常类型 | 严重程度     │
│  触发条件 | 实际指标 | 操作(跳转详情)               │
├──────────────────────────────────────────────────────┤
│  严重程度用 el-tag 颜色:                              │
│    critical → danger (红)                            │
│    warning  → warning (橙)                           │
│    info     → info (灰)                              │
└──────────────────────────────────────────────────────┘
```

- 点击行可弹窗展示该 SKU 的详细指标数据
- 异常类型用 `el-select` 支持筛选
- 表格支持排序（按指标值）

---

## 修改文件

### 6. `app/api/__init__.py`

```python
from app.api.anomalies import router as anomalies_router
api_router.include_router(anomalies_router)
```

### 7. `frontend/src/types/index.ts`

新增:
```typescript
export interface AnomalyItem {
  sku_id: number
  offer_id: string | null
  name: string | null
  primary_image: string | null
  anomaly_type: string
  severity: 'critical' | 'warning' | 'info'
  description: string
  metrics: Record<string, number>
  triggered_conditions: string[]
}

export interface AnomalySummary {
  total_anomalies: number
  by_type: Record<string, number>
}

export interface AnomalyResponse {
  summary: AnomalySummary
  items: AnomalyItem[]
}
```

### 8. `frontend/src/api/index.ts`

新增:
```typescript
export async function getAnomalies(
  dateFrom?: string, dateTo?: string, storeId: number = 1,
): Promise<AnomalyResponse> {
  const p = new URLSearchParams()
  p.set('store_id', String(storeId))
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  return fetchJson<AnomalyResponse>(`${BASE}/anomalies?${p.toString()}`)
}
```

### 9. `frontend/src/views/Dashboard.vue`

- import `AnomalyAnalysis`
- 在 `<el-tabs>` 中新增:
```html
<el-tab-pane label="异常预警" name="anomalies">
  <template #label>
    <span><el-icon><WarningFilled /></el-icon> 异常预警</span>
  </template>
  <AnomalyAnalysis :date-range="dateRange" :active-tab="activeTab" />
</el-tab-pane>
```

---

## 实现顺序

1. **YAML 配置** → `app/anomaly_rules.yaml`
2. **后端 Schema** → `app/schemas/anomalies.py`
3. **后端服务** → `app/services/anomaly_service.py`（核心：规则引擎 + SQL 查询）
4. **后端 API** → `app/api/anomalies.py`
5. **注册路由** → `app/api/__init__.py`
6. **前端类型** → `frontend/src/types/index.ts`
7. **前端 API** → `frontend/src/api/index.ts`
8. **前端组件** → `frontend/src/components/AnomalyAnalysis.vue`
9. **集成** → `frontend/src/views/Dashboard.vue`

---

## SQL 查询核心逻辑

```sql
-- 数据源 1: get_daily_summary (sku_daily_summary 当月聚合)
SELECT store_id, sku_id,
       SUM(ordered_units) AS ordered_units,
       SUM(returns_units) AS returns_units,
       SUM(revenue) AS revenue,
       SUM(net_profit) AS net_profit,
       -- profit_margin 聚合后重算
       CASE WHEN SUM(revenue) > 0
            THEN SUM(net_profit) / SUM(revenue) * 100
            ELSE 0 END AS profit_margin,
       MAX(stock_present) AS stock_present
FROM ozon.sku_daily_summary
WHERE store_id = :store_id AND date BETWEEN :date_from AND :date_to
GROUP BY store_id, sku_id

-- 数据源 2: get_ad_performance (ad_sku_daily_stats 当月聚合)
SELECT store_id, sku_id,
       SUM(spend) AS spend,
       SUM(clicks) AS clicks,
       SUM(sold_units) AS sold_units,
       -- ctr 和 drr_total 聚合后重算
       CASE WHEN SUM(impressions) > 0
            THEN SUM(clicks)::float / SUM(impressions) * 100
            ELSE 0 END AS ctr,
       CASE WHEN SUM(total_ordered) > 0
            THEN SUM(spend) / SUM(total_ordered) * 100
            ELSE 0 END AS drr_total
FROM ozon.ad_sku_daily_stats
WHERE store_id = :store_id AND stat_date BETWEEN :date_from AND :date_to
  AND sku_id > 0
GROUP BY store_id, sku_id

-- 数据源 3: get_stock_snapshot (stocks 实时快照)
SELECT s.store_id, s.sku_id,
       COALESCE(SUM(s.present), 0) AS present
FROM ozon.stocks s
WHERE s.store_id = :store_id
GROUP BY s.store_id, s.sku_id
```

---

## 验证方式

1. 启动后端 `uvicorn app.main:app --reload`
2. 确认 `/docs` 中出现了 `/api/v1/anomalies` 端点
3. 调用 `GET /api/v1/anomalies?store_id=1` 确认返回异常数据
4. 修改 `app/anomaly_rules.yaml` 中的阈值，确认改 YAML 即可改变检测结果
5. 启动前端 `npm run dev`，切换到「异常预警」Tab
6. 确认表格正确展示异常 SKU，筛选功能正常
