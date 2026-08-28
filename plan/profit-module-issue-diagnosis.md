# 利润模块问题诊断报告

> 结论先行：利润模块最大的问题不是单一 bug，而是**"利润"在系统内存在多套互相矛盾的公式口径**，且"真实净利"建立在两个不可靠/可能为空的成本数据源上。以下按严重度排序逐条说明，并给出修复建议（本报告仅诊断，未改动任何代码）。

## 涉及的代码与数据表

| 模块 | 入口 | 口径 |
|------|------|------|
| 利润分析 API（平台） | `app/api/profit.py` `/profit/*` | 平台毛利 = 收入 + 7 类费用 |
| 真实利润 API（含成本） | `app/api/real_profit.py` `/real-profit/*` | 平台毛利 − 采购₽ − 头程₽ |
| 汇总利润计算 | `app/services/profit_service.py` → `sku_daily_summary` | 净利 = 收入 + 费用（按天分层） |
| SKU 管理公式 | `app/services/sku_formulas.py` | 利润 = (实际回款 − 风险金 − 成本) |
| 前端利润 Tab | `frontend/src/components/ProfitAnalysis.vue` | 混用 `/real-profit/*` + `/profit/trend` |

---

## 问题 1：系统内存在 3 套互相矛盾的"利润"公式（严重度：高）

同一个 SKU 在不同 Tab 看到完全不同的"利润"，但都被称为"利润"：

| 口径 | 公式 | 数据来源 |
|------|------|----------|
| 利润分析（平台） | `net_profit = revenue + commissions + logistics + storage + advertising + promotion + returns + other`（费用为负） | `finance_transactions` |
| 真实利润 | `real_net = 平台毛利 − (采购单价+头程单价)×销量×汇率` | `finance_transactions` + `omsprod` + `sku_management` |
| SKU 管理 | `profit_rmb = (实际回款 − 风险金)/汇率 − 产品成本`，`profit_rub = profit_rmb × 汇率` | `sku_formulas.py`（基于实际回款，不走费用明细） |
| 汇总层 | `net_profit = revenue + 费用` | `sku_daily_summary` |

**表现**：同一商品在「利润分析」Tab 和「SKU 管理」Tab 的"利润/利润率"数值不一致；「SKU 管理」里显示的利润基于"实际回款"（`actual_payout_rub`），而「利润分析」里基于"收入+费用"，两者往往相差很大。

**影响**：业务侧无法用统一的"利润"做定价、调价、SKU 淘汰，数字互相打架会让整个看板失去可信度。

**建议**：明确一个唯一的"利润"业务口径（推荐以"实际回款 − 风险金 − 采购成本 − 头程 − 其他应扣"为口径），让 `profit.py`/`real_profit.py`/`profit_service.py`/`sku_formulas.py` 全部收敛到同一公式，并在这四处统一命名与注释。在收敛前，界面应明确区分"平台毛利"与"经营利润"，不要都叫"利润"。

---

## 问题 2："真实净利"依赖两个不可靠/可能为空的成本源（严重度：高）

`real_profit.py` 里"真实净利" = 平台毛利 − 采购成本 − 头程费用，但：

### 采购成本（`omsprod`）
```
SELECT DISTINCT ON (ppi.item_id) ppi.item_id, poi.price
FROM public.purchase_plan_item ppi
JOIN public.purchase_order_item poi ON poi.po_plan_no = ppi.po_plan_no
JOIN public.purchase_order po ON po.po_no = poi.po_no
WHERE ppi.item_id = ANY(...) AND ppi.platform='Ozon' AND po.status='7' AND poi.price IS NOT NULL
ORDER BY ppi.item_id, po.create_time DESC
```
- 代码注释自己承认：**`purchase_order_item.item_id 大多为 NULL`**，真正的 SKU 编码在 `purchase_plan_item.item_id`。
- 关联链路依赖 `po_plan_no` 匹配、`po.status='7'`，任何一环对不上就取不到单价。
- 失败后的兜底是 `purchase_unit.get(offer, 0.0)` → 该 SKU 采购成本 = 0。

### 头程费用 & 汇率
- 头程单价来自本地 `sku_management.first_leg_cost_rmb`，而这是 `sku_formulas.py` 公式引擎的**估算值**，并非实际发生额。
- 汇率 `_get_exchange_rates` 对未填写的 SKU **硬编码默认 `12.0`**。

**表现**：
- `sku_with_purchase_cost` / `sku_with_first_leg_cost` 远小于 `sku_count`，大量 SKU 的"真实净利"**直接等于"平台毛利"**。
- 表格里"真实净利"列大量显示 `未填写` / `缺成本` / `—`，使该列失去参考价值。
- 带成本的 SKU 也因头程为估算、汇率为默认而失真。

**建议**：
1. 采购成本链路改成先按 `offer_id`/`sku_id` 在 `purchase_plan_item` 上能稳定命中（目前的 join 链比较脆弱，建议在同步阶段把"最近采购单价"落库到本地表，避免每次实时跨库 join）。
2. 头程费用"估算值"与"实际值"要分开命名与标注，避免把估算当成事实。
3. 汇率未填写时不要静默用默认值，应显式暴露为"缺汇率"并提示，避免用默认值算出的利润误导决策。

---

## 问题 3：COGS 销量口径 ≠ 平台收入口径，导致真实净利系统性偏差（严重度：中高）

```
real_net = 平台毛利 − (采购单价 + 头程单价) × 销量 × 汇率
```
其中：
- **平台毛利**：来自 `finance_transactions`，按 `posting.created_at` / `operation_date` 归因（见 `profit.py _aggregate_profit`）。
- **销量 `ordered_units`**：来自 `postings.products` 的 `quantity` 聚合，按 `postings.created_at` 归因（见 `real_profit.py _get_sku_ordered_units`）。

两套归因的日期基准相同（都依赖 `created_at`）但**数据源不同**：财务流水的金额与订单的件数未必 1:1 对齐（涉及退货、退款、订单状态变更、跨期结算），于是单价×销量算出的成本可能与当期实际发生额对不上，导致每个 SKU 的"真实净利"偏离真实值。

**建议**：统一 COGS 与收入的归因基准。优先以 `finance_transactions` 的可信口径为准，或将"单品成本"做成"按当期实际售出数量匹配的结算口径"，避免成本与收入各算各的。

---

## 问题 4：前端趋势图与 KPI/表格数据源割裂（严重度：中）

`ProfitAnalysis.vue` 的 `loadData()`：

```ts
const [ov, sku, trend] = await Promise.all([
  getRealProfitOverview(d1, d2, selectedStoreId.value),   // /real-profit/overview（含成本）
  getRealProfitSkuRanking(d1, d2, selectedStoreId.value),  // /real-profit/sku-ranking（含成本）
  getProfitTrend(d1, d2, selectedStoreId.value),           // /profit/trend（平台口径，不含成本）
])
```

- KPI 卡片（真实净利 / 真实利润率）、成本饼图、SKU 排行表 → 全部走 `/real-profit/*`（含采购+头程）。
- 趋势图 → 走 `/profit/trend`（**平台口径，不含成本**），图例还标着"平台净利"，但把"平台净利"与 KPI 的"真实净利"并列展示，用户容易误读成同一指标。

**表现**：趋势线的"净利"与卡片的"真实净利"对不上；看"趋势"与看"卡片"得到两个不同的净利润，且都没有明确说明二者口径差异。

**建议**：趋势图改用与 KPI 一致的真实利润接口（`/real-profit`），或明确标注趋势图为"平台口径"；至少保证同一屏内所有"净利润"指标口径一致，并加图例/注释说明。

---

## 问题 5：字段/逻辑隐患（严重度：中）

`profit.py _aggregate_profit` 存在以下隐患：

1. **`delivery_charge` / `return_delivery_charge` 被选中但从未参与计算**：`SELECT` 语句里取出了这两个字段，但循环里只用 `_parse_services_logistics(services)` 从 `services` JSON 里解析含 "Logistic" 的条目。若物流费部分落在 `delivery_charge` 字段而 `services` 里没有，会被漏算，导致物流费低估。

2. **日期过滤写法绕、易出边界问题**：
   ```sql
   WHERE ... ft.operation_date BETWEEN :date_from AND :date_to_excl - INTERVAL '1 day'
   ```
   其中 `date_to_excl = date_to + timedelta(days=1)`，相减后又回到 `date_to`。虽然最终等价于 `[date_from, date_to]`，但语义含混，且广告/推广费的处理与主事务在日期上未必一致，容易出现区间边界不一致。

3. **推广费/广告费的分摊逻辑较复杂、易漏**：
   - `OperationPromotionWithCostPerOrder` 且 `sku_id IS NULL` 时先按 posting 分摊，无 posting 时再按当日收入占比分摊（`unmatched` 分支）。
   - 分摊只对 `revenue > 0` 的分组进行，若某天某组有收入但收入为 0（例如只退不销），推广/广告费会被丢弃，造成该日费用被低估。

**建议**：
1. 确认物流费的实际存放位置，若存在 `delivery_charge` 字段应一并计入 `logistics_costs`。
2. 日期过滤统一改为 `BETWEEN :date_from AND :date_to`（或统一的左闭右开 + 显式边界）。
3. 推广/广告费分摊对"无收入但有费用"的日期也要兜底，避免费用丢失。

---

## 附：次要问题（知晓即可）

- **数据质量 `partial` 语义弱化**：`profit_service.py` 把"有收入但全部费用为 0"标记为 `partial`，但当前大多不会触发，无法真正反映"缺成本/缺财务"状态；建议与 `real_profit` 的"缺成本/缺头程"标记统一。
- **双轴图可读性**：趋势图"% 轴"与"₽ 轴"同图，利润率可能为负且量纲差异大，建议分开或限定范围。
- **无缓存/实时聚合**：`/profit/*` 与 `/real-profit/*` 每次实时聚合 `finance_transactions`，数据量大时查询缓慢；`sku_daily_summary` 已做预聚合，应尽量复用。

---

## 结论

利润模块当前最需要的不是一个补丁，而是**先统一"利润"的业务口径**。建议优先级：

1. **（P0）统一利润口径** → 消除同商品"利润"打架的根因。
2. **（P0）修正"真实净利"成本源** → 采购单价落库、头程估算/实际分开、汇率缺失显式提示。
3. **（P1）统一 COGS 与收入归因** → 避免成本与收入各算各的。
4. **（P1）前端指标口径对齐** → 趋势图与 KPI 一致。
5. **（P2）补物流/日期/分摊逻辑** → 修正字段未用与边界问题。

> 本报告基于对 `profit.py`、`real_profit.py`、`profit_service.py`、`sku_formulas.py`、`ProfitAnalysis.vue`、`schemas/profit.py`、`frontend/src/types/index.ts` 及 README 的静态阅读。若需进一步验证（如实际查询 `finance_transactions` / `omsprod` 的命中率、`sku_with_purchase_cost` 的真实覆盖度），可运行诊断脚本或用数据库连接核对。
