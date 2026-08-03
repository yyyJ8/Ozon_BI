# SKU管理 — 55列数据来源完整说明

> 关联键：所有数据通过 **`offer_id`**（货号，如 `30278-Y07U0001-A01`）或 **`sku_id`**（Ozon 系统 SKU 编号）关联。

---

## 一、本地 PostgreSQL（已在用，Ozon API 同步）

> 连接：`192.168.111.78:5432` / `ai_application` / schema `ozon`

### 1.1 只读列（产品基础信息，来自 `products` 表）

| 列名 | 中文名 | 来源表.字段 | 状态 |
|---|---|---|---|
| `primary_image` | 主图 | `products.primary_image` | ✅ 已在使用 |
| `sku_id` | SKU编号 | `products.sku_id` | ✅ 已在使用 |
| `offer_id` | 货号 | `products.offer_id` | ✅ 已在使用 |
| `name` | 商品名称 | `products.name` | ✅ 已在使用 |
| `price` | 售价（卢布） | `products.price` | ✅ 已在使用 |
| `stock_present` | 当前库存 | `stocks.present` 汇总 | ✅ 已在使用 |

### 1.2 可自动计算的列（来自 `products` / `sku_daily_summary` / `returns`）

| 列名 | 中文名 | 来源表.字段 | 取值方式 |
|---|---|---|---|
| `actual_weight_kg` | 实重（kg） | `products.volume_weight` | 直接映射 |
| `fbo_commission_pct` | FBO佣金率（%） | `products.commission_fbo_pct` | 直接映射 |
| `discount_pct` | 折扣率（%） | `products.price` / `products.old_price` | `(1 − price ÷ old_price) × 100` |
| `advertising_rate_pct` | 广告费率（%） | `sku_daily_summary.advertising` | 近30天广告费 ÷ 近30天收入 × 100 |
| `return_rate_pct` | 退货率（%） | `returns.quantity` / `sku_daily_summary.ordered_units` | 近30天退货件数 ÷ 近30天销量 × 100 |
| `logistics_rub` | 物流费（卢布） | `sku_daily_summary.logistics_costs` | 近30天均值 |
| `delivery_pickup_rub` | 配送费（卢布） | `finance_transactions.delivery_charge` | 近30天按 SKU 均值 |

---

## 二、中台 OMS_PG — 采购/申购/头程

> 连接：`pgm-7xvui1j4600t1u27-l2.pg.rds.aliyuncs.com:5432` / `omsprod`

### 2.1 `purchase_order_item`（采购订单明细）→ 按 `item_id`（即 offer_id）关联

| 列名 | 中文名 | 来源字段 | 示例值 | 取值方式 |
|---|---|---|---|---|
| ⭐ `purchase_cost_rmb` | 采购成本（人民币） | `price`（未税单价） | `26.00` | 取该 offer_id **最新一条**采购明细 |
| ⭐ `main_sku` | 主SKU | `main_sku_id` | `41987` | 直接映射 |
| ⭐ `source_url_1688` | 1688采购链接 | `sku_purchase_rul` | 1688商品URL | 直接映射 |
| `units_per_carton` | 装箱数 | `package_qty` | `7` | 直接映射 |

### 2.2 `first_leg_shipping_order_item`（头程发货明细）→ 按 `item_id`（即 offer_id）关联

| 列名 | 中文名 | 来源字段 | 示例值 | 取值方式 |
|---|---|---|---|---|
| `carton_length_cm` | 外箱长（cm） | `package_volume` | `39.00*29.50*7.00` | 按 `*` 分割取第1个 |
| `carton_width_cm` | 外箱宽（cm） | 同上 | → `29.50` | 按 `*` 分割取第2个 |
| `carton_height_cm` | 外箱高（cm） | 同上 | → `7.00` | 按 `*` 分割取第3个 |
| `gross_weight_kg` | 外箱毛重（kg） | `package_weight` | `2.12` | 直接映射 |
| `volume_liters` | 外箱体积（升） | `package_volume` 计算 | `39×29.5×7÷1000 ≈ 8.05` | 长×宽×高÷1000 |
| `specification` | 规格描述 | `material`（材质） | `亚克力`、`毛毡` | 可部分填入规格字段 |
| `units_per_carton` | 装箱数 | `package_qty` | `1` | 与 2.1 的采购装箱数交叉验证 |

### 2.3 `purchase_plan_item`（申购明细）→ 按 `item_id`（即 offer_id）关联

| 列名 | 中文名 | 来源字段 | 示例值 | 取值方式 |
|---|---|---|---|---|
| `main_sku` | 主SKU | `main_sku_id` | `41987` | 与 2.1 的采购主SKU交叉验证 |

---

## 三、中台 DW_MYSQL — Ozon产品/库存/订单

> 连接：`223.84.201.140:9030` / `db_warehouse`

### 3.1 `ods_ozon_product_f`（Ozon产品全量表）→ 按 `offer_id` 关联

| 列名 | 中文名 | 来源字段 | 示例值 | 取值方式 |
|---|---|---|---|---|
| `actual_weight_kg` | 实重（kg） | `volume_weight` | `1.40` | 直接映射 |
| `fbo_commission_pct` | FBO佣金率（%） | `commissions` JSON | `[{"sale_schema":"FBO","percent":14}]` | 解析 JSON，取 FBO 的 `percent` |
| `tax_and_fee_pct` | 税费率（%） | `vat` | `0.00` | 直接映射 |
| `product_status` | 商品状态 | `statuses` JSON → `status_name` | `Продается`（在售）/ `Не продается`（未在售） | 解析 JSON，取 `status_name` |
| `stock_present` | 当前库存 | `stocks` JSON → `present` | `200` | 解析 JSON，取 `present` |
| `discount_pct` | 折扣率（%） | `price` vs `old_price` | `135.00` / `146.99` | `(1 − price ÷ old_price) × 100` |
| `green_price_rub` | 绿标价（卢布） | `price_indexes` JSON → `color_index` | `COLOR_INDEX_GREEN` | 辅助判断：GREEN = 价格有竞争力 |

---

## 四、计算字段（有基础数据后可自动算出）

> 以下列不依赖额外数据源，只要前面的一~三提供的基础数据到位即可自动计算。

| 列名 | 中文名 | 计算公式 |
|---|---|---|
| `purchase_cost_pct` | 采购成本占比（%） | `purchase_cost_rmb ÷ product_cost_rmb × 100` |
| `first_leg_pct` | 头程占比（%） | `first_leg_cost_rmb ÷ product_cost_rmb × 100` |
| `product_cost_rmb` | 产品成本（人民币） | `purchase_cost_rmb + warehousing_fee_rmb + fbo_delivery_fee_rmb + first_leg_cost_rmb` |
| `last_mile_pct` | 尾程占比（%） | `(logistics_rub + delivery_pickup_rub) ÷ price ÷ exchange_rate × 100` |
| `platform_payout_rub` | 平台打款（卢布） | `price − (佣金 + 物流 + 广告 + 退货 + 税费 + 风险金)` |
| `actual_payout_rub` | 实际回款（卢布） | `platform_payout_rub × exchange_rate`（此处按公式含义为卢布→人民币） |
| `profit_rub` | 利润（卢布） | `platform_payout_rub − product_cost_rmb × exchange_rate` |
| `profit_rmb` | 利润（人民币） | `profit_rub ÷ exchange_rate` |
| `profit_margin_pct` | 利润率（%） | `profit_rub ÷ platform_payout_rub × 100` |
| `density` | 密度 | `actual_weight_kg ÷ volume_cbm` |
| `volume_cbm` | 单品体积（m³） | `length_cm × width_cm × height_cm ÷ 1,000,000` |

---

## 五、必须业务人员手工填写

> 以下 15 列中台和本地都没有数据，只能靠人填。

| 列名 | 中文名 | 无法自动获取的原因 |
|---|---|---|
| `sales_manager` | 负责人 | 中台只有数字 `head_id`，无姓名映射 |
| `key_notes` | 备注 | 纯业务自由文本 |
| `competitor_1` | 竞品链接1 | 外部信息 |
| `competitor_2` | 竞品链接2 | 外部信息 |
| `competitor_sales` | 竞品销量 | 外部信息 |
| `length_cm` | 单品长（cm） | 中台只有外箱尺寸，无单个商品尺寸 |
| `width_cm` | 单品宽（cm） | 同上 |
| `height_cm` | 单品高（cm） | 同上 |
| `warehousing_fee_rmb` | 入库费（人民币） | 中台无此费用项 |
| `fbo_delivery_fee_rmb` | 送仓费（人民币） | 中台无此费用项 |
| `first_leg_unit_price` | 头程单价（人民币） | 需从物流账单按 SKU 分摊 |
| `first_leg_cost_rmb` | 头程费（人民币） | 需从物流账单按 SKU 分摊 |
| `exchange_rate` | 汇率 | 需人工录入或接入外部汇率 API |
| `acquiring_fee_pct` | 收单费率（%） | Ozon API 未直接提供 |
| `risk_reserve_rub` | 风险准备金（卢布） | 业务决策，非数据 |
| `listed_stores` | 上架店铺 | 中台 `store_id` 需映射到店铺名称 |
| `green_price_rub` | 绿标价（卢布） | 属于定价策略，需人工决策 |

---

## 📊 汇总

| 数据来源 | 可填充列数 | 说明 |
|---|---|---|
| 本地 `ai_application`（已在用） | 7 只读 + 7 可算 = **14 列** | Ozon API 同步数据 |
| 中台 `omsprod`（采购+头程） | **11 列** | `purchase_order_item` + `first_leg_shipping_order_item` + `purchase_plan_item` |
| 中台 `db_warehouse`（Ozon产品） | **7 列** | `ods_ozon_product_f` |
| 计算字段 | **11 列** | 有基础数据后自动得出 |
| **自动/半自动合计** | **43 列** | |
| **必须人工填写** | **17 列** | |
| **总计** | **55 列**（去重后略有交叉） | |

---

## 🔑 核心发现

1. **`purchase_order_item`** 是最有价值的中台表，提供 **采购成本**、**主SKU**、**1688链接**、**装箱数** — 这4列目前全部靠手填。
2. **`first_leg_shipping_order_item`** 提供 **外箱长宽高**、**毛重**、**材质** — 这6列目前也全靠手填。
3. 两个中台库合并后，人工填写的列从 ~40 列缩减到 **~17 列**，大幅降低录入工作量。
4. 关联键统一用 **`offer_id`**（货号），所有表都有这个字段。
5. 对于有历史数据的列（采购订单、头程发货），**取最新一条记录**即可，不需要全量历史。
