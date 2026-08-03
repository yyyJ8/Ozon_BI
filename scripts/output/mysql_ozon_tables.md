# MySQL db_warehouse — Ozon 6表（含中文说明 + 实际数据）

> 服务器: 223.84.201.140:9030 | 数据库: db_warehouse

---

## 1. ods_ozon_product_f — Ozon产品全量表（532行）

`_f` 结尾表示全量快照表，记录 Ozon 店铺所有产品的完整信息。

| 字段 | 中文名 | 类型 | 例1 | 例2 |
|------|--------|------|-----|-----|
| `product_id` | 产品ID | bigint | 1954467090 | 1954467258 |
| `seller_id` | 卖家ID | bigint | 3013635 | 3013635 |
| `offer_id` | 商家SKU编码 | varchar | 30278-Y07U0001-A01 | 22641-Y07U0004-A01 |
| `archived` | 是否已归档(0否1是) | boolean | 0 | 0 |
| `has_fbo_stocks` | 是否有FBO库存 | boolean | 0 | 0 |
| `has_fbs_stocks` | 是否有FBS库存 | boolean | 1 | 1 |
| `quants` | 数量信息(JSON) | text | [] | [] |
| `barcodes` | 条形码列表(JSON) | text | [] | [] |
| `color_image` | 颜色图片(JSON) | text | [] | [] |
| `commissions` | 佣金信息(JSON, 含FBO/FBS/FBP各模式佣金) | text | [{"sale_schema":"FBO","percent":14,"value":18.9}...] | [{"sale_schema":"FBO","percent":14,"value":53.2}...] |
| `description_category_id` | 描述分类ID | bigint | 17028665 | 17028665 |
| `discounted_fbo_stocks` | 折扣FBO库存数 | int | 0 | 0 |
| `has_discounted_fbo_item` | 是否有折扣FBO商品 | boolean | 0 | 0 |
| `is_autoarchived` | 是否自动归档 | boolean | 0 | 0 |
| `is_discounted` | 是否参与折扣 | boolean | 0 | 0 |
| `is_kgt` | 是否KGT超大件 | boolean | 0 | 0 |
| `is_prepayment_allowed` | 是否允许预付款 | boolean | 1 | 1 |
| `is_super` | 是否超级商品 | boolean | 0 | 0 |
| `marketing_price` | 营销价格(卢布) | varchar | 135.00 | 380.00 |
| `min_price` | 最低价格(卢布) | varchar | (空) | (空) |
| `model_id` | 模型ID | bigint | 490618036 | 481273585 |
| `model_count` | 模型数量 | int | 7 | 1 |
| `name` | 商品名称(俄文) | varchar | Коврик для пазлов на 500, 1000, 1500, 2000 деталей... | Переносной Коврик Для Пазлов До 1000 Деталей |
| `old_price` | 旧价格(卢布) | varchar | 146.99 | 599.90 |
| `price` | 当前售价(卢布) | varchar | 135.00 | 380.00 |
| `price_indexes` | 价格指数(JSON, 含颜色指数/外部价格/平台价格) | text | {"color_index":"COLOR_INDEX_WITHOUT_INDEX"...} | {"color_index":"COLOR_INDEX_GREEN"...} |
| `primary_image` | 主图URL列表(JSON) | text | ["https://cdn1.ozone.ru/s3/multimedia-1-m/7316625190.jpg"] | ["https://cdn1.ozone.ru/s3/multimedia-1-5/7353669173.jpg"] |
| `promotions` | 促销信息(JSON, 如REVIEWS_PROMO) | text | [{"type":"REVIEWS_PROMO","is_enabled":false}] | [{"type":"REVIEWS_PROMO","is_enabled":false}] |
| `sku` | Ozon系统SKU编号 | bigint | 2276167271 | 2276166992 |
| `sources` | 来源信息(JSON, 含sku/shipment_type) | text | [{"sku":2276167271,"source":"sds"...}] | [{"sku":2276166992,"source":"sds"...}] |
| `statuses` | 状态信息(JSON, 含审核/验证/上下架状态) | text | {"status":"price_sent","status_name":"Не продается"...} | {"status":"price_sent","status_name":"Продается"...} |
| `stocks` | 库存信息(JSON, 含present/reserved/source) | text | {"has_stock":true,"stocks":[{"present":200,"reserved":0...}]} | {"has_stock":true,"stocks":[{"present":100,"reserved":0...}]} |
| `type_id` | 商品类型ID | bigint | 92941 | 92941 |
| `updated_at` | Ozon平台更新时间 | datetime | 2025-06-12 02:22:35 | 2025-06-12 02:23:53 |
| `vat` | 增值税率 | varchar | 0.00 | 0.00 |
| `visibility_details` | 可见性详情(JSON, has_price/has_stock) | text | {"has_price":true,"has_stock":true} | {"has_price":true,"has_stock":true} |
| `volume_weight` | 体积重量(kg) | decimal | 1.40 | 4.10 |
| `create_time` | 数据创建时间(ETL) | datetime | 2025-09-20 10:45:13 | 2025-09-20 10:45:13 |
| `update_time` | 数据更新时间(ETL) | datetime | 2025-10-15 03:45:03 | 2025-10-17 03:45:03 |

---

## 2. ods_ozon_product_stock_d — Ozon产品库存表（每天快照，20,122行）

`_d` 结尾表示按天增量/快照表，`batch_no` 字段标识快照日期。

| 字段 | 中文名 | 类型 | 例1 | 例2 |
|------|--------|------|-----|-----|
| `product_id` | 产品ID | bigint | 1903953946 | 1903953946 |
| `seller_id` | 卖家ID | bigint | 3012909 | 3012909 |
| `offer_id` | 商家SKU编码 | varchar | 15079-Y07U0007-B01 | 15079-Y07U0007-B01 |
| `fbo_present` | FBO可用库存(平台仓在售) | int | 177 | 178 |
| `fbo_reserved` | FBO预留库存(已下单未出库) | int | 1 | 1 |
| `fbo_sku` | FBO SKU编号 | bigint | 2238512937 | 2238512937 |
| `fbo_shipment_type` | FBO发货类型 | varchar | SHIPMENT_TYPE_GENERAL | SHIPMENT_TYPE_GENERAL |
| `fbo_warehouse_ids` | FBO仓库ID列表(JSON) | text | [] | [] |
| `fbs_present` | FBS可用库存(商家仓在售) | int | 0 | 0 |
| `fbs_reserved` | FBS预留库存 | int | 0 | 0 |
| `fbs_sku` | FBS SKU编号 | bigint | 2238512937 | 2238512937 |
| `fbs_shipment_type` | FBS发货类型 | varchar | SHIPMENT_TYPE_GENERAL | SHIPMENT_TYPE_GENERAL |
| `fbs_warehouse_ids` | FBS仓库ID列表(JSON) | text | [] | [] |
| `create_time` | 创建时间 | datetime | 2025-09-20 09:35:40 | 2025-09-20 09:35:40 |
| `update_time` | 更新时间 | datetime | 2026-03-02 00:22:13 | 2026-03-01 00:22:18 |
| `batch_no` | 快照批次号(日期, yyyy-MM-dd) | varchar | 2026-03-02 | 2026-03-01 |

---

## 3. ods_ozon_fbo_order_f — FBO订单主表（平台仓发货, 5,124行）

FBO = Fulfillment by Ozon，平台负责仓储和配送。

| 字段 | 中文名 | 类型 | 例1 | 例2 |
|------|--------|------|-----|-----|
| `posting_number` | 订单唯一标识号(发货编号) | varchar | 00395513-0358-1 | 00451598-0260-1 |
| `seller_id` | 卖家ID | bigint | 3018128 | 3012909 |
| `order_id` | Ozon平台订单ID | varchar | 31811442297 | 30100641038 |
| `order_number` | 订单编号(商家可见) | varchar | 00395513-0358 | 00451598-0260 |
| `status` | 订单状态(delivered/cancelled等) | varchar | delivered | delivered |
| `cancel_reason_id` | 取消原因ID(0=未取消) | bigint | 0 | 0 |
| `created_at` | 订单创建时间(Ozon平台) | datetime | 2025-11-03 16:32:58 | 2025-08-20 18:13:51 |
| `in_process_at` | 订单开始处理时间 | datetime | 2025-11-03 16:33:07 | 2025-08-20 18:13:59 |
| `legal_info` | 法律信息(JSON, 公司名/INN/KPP) | text | {"company_name":"","inn":"","kpp":""} | {"company_name":"","inn":"","kpp":""} |
| `analytics_data` | 分析数据(JSON) | text | NULL | NULL |
| `additional_data` | 附加数据(JSON) | text | [] | [] |
| `create_time` | ETL创建时间 | datetime | 2025-11-05 00:22:03 | 2025-09-19 20:17:28 |
| `update_time` | ETL更新时间 | datetime | 2025-12-03 00:22:07 | 2025-09-19 20:17:28 |

---

## 4. ods_ozon_fbo_order_product_f — FBO订单商品明细（4,755行）

关联 `ods_ozon_fbo_order_f.posting_number`。

| 字段 | 中文名 | 类型 | 例1 | 例2 |
|------|--------|------|-----|-----|
| `id` | 主键ID(订单号+SKU组合) | varchar | 00395513-0358-1_31243-Y07U0002-B03 | 00483672-0197-1_31826-Y07U0003-B01 |
| `posting_number` | 关联订单编号(外键) | varchar | 00395513-0358-1 | 00483672-0197-1 |
| `sku` | 商品SKU编码(Ozon系统) | bigint | 2393838701 | 2401725779 |
| `name` | 商品名称(俄文) | text | Опора под спину регулируемая с подлокотниками... | Прикроватный поручень для пожилых и инвалидов... |
| `quantity` | 商品数量 | int | 1 | 1 |
| `offer_id` | 商家商品编号(对应OMS的SKU) | varchar | 31243-Y07U0002-B03 | 31826-Y07U0003-B01 |
| `price` | 商品售价(卢布) | varchar | 4700.00 | 5063.00 |
| `is_marketplace_buyout` | 是否平台回购(0否1是) | boolean | 0 | 0 |
| `digital_codes` | 数字商品码(JSON) | text | [] | [] |
| `currency_code` | 货币代码(RUB/USD等) | varchar | RUB | RUB |
| `create_time` | ETL创建时间 | datetime | 2025-11-05 00:22:04 | 2025-09-19 20:17:28 |
| `update_time` | ETL更新时间 | datetime | 2025-12-03 00:22:07 | 2025-10-07 03:40:03 |

---

## 5. ods_ozon_fbs_order_f — FBS订单主表（商家自发货, 965行, 60列）

FBS = Fulfillment by Seller，商家自己仓储和发货。字段最多，包含完整物流信息。

### 订单基础信息

| 字段 | 中文名 | 类型 | 例1 | 例2 |
|------|--------|------|-----|-----|
| `posting_number` | 订单唯一标识号 | varchar | 00308364-0495-1 | 0100701034-0165-1 |
| `seller_id` | 卖家ID | bigint | 3012909 | 3018151 |
| `order_id` | Ozon平台订单ID | bigint | 30462605260 | 30660374970 |
| `order_number` | 订单编号(商家可见) | varchar | 00308364-0495 | 0100701034-0165 |
| `status` | 订单状态(delivered/cancelled) | varchar | delivered | cancelled |
| `substatus` | 订单子状态 | varchar | posting_received | posting_canceled |
| `is_express` | 是否加急订单 | boolean | 0 | 0 |
| `parent_posting_number` | 父订单编号(拆单场景) | varchar | (空) | (空) |
| `multi_box_qty` | 多箱数量 | int | 1 | 1 |
| `is_multibox` | 是否多箱订单 | boolean | 0 | 0 |

### 配送物流信息

| 字段 | 中文名 | 类型 | 例1 | 例2 |
|------|--------|------|-----|-----|
| `delivery_id` | 配送方式ID | bigint | 1020005000204760 | 1020005000205887 |
| `delivery_name` | 配送方式名称 | varchar | Доставка Ozon самостоятельно, Balashikha | Доставка Ozon самостоятельно, Balashikha |
| `delivery_warehouse_id` | 发货仓库ID | bigint | 1020005000204760 | 1020005000205887 |
| `delivery_warehouse` | 发货仓库名称 | varchar | EY-FBS | EY-FBS |
| `delivery_tpl_provider_id` | 物流供应商ID | bigint | 24 | 24 |
| `delivery_tpl_provider` | 物流供应商名称 | varchar | Доставка Ozon | Доставка Ozon |
| `tracking_number` | 物流跟踪号 | varchar | (空) | (空) |
| `tpl_integration_type` | 物流集成类型 | varchar | ozon | ozon |
| `in_process_at` | 开始处理时间 | datetime | 2025-08-06 17:09:22 | 2025-08-09 19:40:23 |
| `shipment_date` | 实际发货时间 | datetime | 2025-08-06 15:00:00 | 2025-08-09 15:00:00 |
| `delivering_date` | 配送完成时间 | datetime | 2025-08-07 15:16:43 | NULL |

### 费率/关税信息

| 字段 | 中文名 | 类型 | 例1 | 例2 |
|------|--------|------|-----|-----|
| `current_tariff_rate` | 当前费率 | int | 0 | 0 |
| `current_tariff_type` | 当前费率类型 | varchar | (空) | (空) |
| `current_tariff_charge` | 当前费用 | varchar | (空) | (空) |
| `current_tariff_charge_currency_code` | 当前费用货币 | varchar | (空) | (空) |
| `next_tariff_rate` | 下一费率 | decimal | 0.00 | 0.00 |
| `next_tariff_type` | 下一费率类型 | varchar | (空) | (空) |
| `next_tariff_charge` | 下一费用 | varchar | (空) | (空) |
| `next_tariff_starts_at` | 下一费率生效时间 | datetime | NULL | NULL |
| `next_tariff_charge_currency_code` | 下一费用货币 | varchar | (空) | (空) |
| `destination_place_id` | 目的地ID | bigint | 0 | 0 |
| `destination_place_name` | 目的地名称 | varchar | (空) | (空) |

### 取消信息

| 字段 | 中文名 | 类型 | 例1 | 例2 |
|------|--------|------|-----|-----|
| `cancel_reason_id` | 取消原因ID(0=未取消) | bigint | 0 | 352 |
| `cancel_reason` | 取消原因描述 | varchar | (空) | Товар закончился на складе (库存不足) |
| `cancellation_type` | 取消类型 | varchar | (空) | seller |
| `cancelled_after_ship` | 是否发货后取消 | boolean | 0 | 1 |
| `affect_cancellation_rating` | 是否影响取消评级 | boolean | 0 | 1 |
| `cancellation_initiator` | 取消发起方 | varchar | (空) | Продавец (卖家) |

### 客户/收件人信息（JSON）

| 字段 | 中文名 | 类型 | 例1 | 例2 |
|------|--------|------|-----|-----|
| `customer` | 客户信息(JSON) | varchar | NULL | NULL |
| `addressee` | 收件人信息(JSON) | varchar | NULL | NULL |
| `barcodes` | 条形码信息(JSON) | varchar | NULL | NULL |

### 数据分析 & 财务

| 字段 | 中文名 | 类型 | 例1 | 例2 |
|------|--------|------|-----|-----|
| `analytics_data` | 分析数据(JSON) | text | NULL | NULL |
| `financial_data` | 财务数据(JSON) | text | NULL | NULL |
| `legal_info` | 法律实体信息(JSON) | text | {"company_name":"","inn":"","kpp":""} | {"company_name":"","inn":"","kpp":""} |

### 合规/商品要求（JSON数组，记录需要特殊信息的商品）

| 字段 | 中文名 | 类型 | 例1 | 例2 |
|------|--------|------|-----|-----|
| `products_requiring_gtd` | 需要GTD报关的商品 | text | [] | [] |
| `products_requiring_country` | 需要原产国信息的商品 | text | [] | [] |
| `products_requiring_mandatory_mark` | 需要强制标记的商品 | text | [] | [] |
| `products_requiring_rnpt` | 需要RNPT信息的商品 | text | [] | [] |
| `products_requiring_jw_uin` | 需要JW UIN的商品 | text | [] | [] |
| `products_requiring_change_country` | 需要更改原产国的商品 | text | [] | [] |
| `products_requiring_imei` | 需要IMEI信息的商品 | text | [] | [] |
| `products_requiring_weight` | 需要重量信息的商品 | text | [] | [] |

### 其他

| 字段 | 中文名 | 类型 | 例1 | 例2 |
|------|--------|------|-----|-----|
| `available_actions` | 可用操作列表(JSON) | text | [] | [] |
| `prr_option` | PRR选项(退货/退款) | varchar | (空) | (空) |
| `quantum_id` | Quantum ID | bigint | 0 | 0 |
| `is_presortable` | 是否可预分拣 | boolean | 0 | 0 |
| `pickup_code_verified_at` | 取件码验证时间 | datetime | NULL | NULL |
| `optional` | 可选信息(JSON, 如有无强制标记商品) | text | {"products_with_possible_mandatory_mark":[]} | {"products_with_possible_mandatory_mark":[]} |
| `create_time` | ETL创建时间 | datetime | 2025-09-19 18:26:52 | 2025-09-19 18:21:02 |
| `update_time` | ETL更新时间 | datetime | 2025-09-19 19:36:40 | 2025-09-19 19:36:35 |

---

## 6. ods_ozon_fbs_order_product_f — FBS订单商品明细（971行）

关联 `ods_ozon_fbs_order_f.posting_number`。

| 字段 | 中文名 | 类型 | 例1 | 例2 |
|------|--------|------|-----|-----|
| `id` | 主键ID(订单号+SKU组合) | varchar | 0100701034-0165-1_31826-Y07U0002-B02 | 0106615625-0327-1_30271-Y07U0001-A01 |
| `offer_id` | 商品Offer ID(商家SKU) | varchar | 31826-Y07U0002-B02 | 30271-Y07U0001-A01 |
| `posting_number` | 关联订单编号(外键) | varchar | 0100701034-0165-1 | 0106615625-0327-1 |
| `price` | 商品售价(卢布) | decimal | 5588.00 | 1366.00 |
| `name` | 商品名称(俄文) | text | Прикроватные подлокотники... | 5шт Комплект форсунок для канализации... |
| `sku` | 商品SKU(Ozon系统) | bigint | 2388807686 | 2528573482 |
| `quantity` | 商品数量 | int | 1 | 1 |
| `currency_code` | 货币代码 | varchar | RUB | RUB |
| `is_blr_traceable` | 是否白俄罗斯可追溯 | boolean | 0 | 0 |
| `is_marketplace_buyout` | 是否市场回购(平台买断) | boolean | 0 | 0 |
| `imei` | IMEI信息(JSON数组) | text | [] | [] |
| `create_time` | ETL创建时间 | datetime | 2025-09-19 18:21:02 | 2025-09-19 18:26:55 |
| `update_time` | ETL更新时间 | datetime | 2025-09-19 19:36:36 | 2025-09-29 03:41:03 |

---

## 表关系总览

```
ods_ozon_product_f (产品主表)
  ├── ods_ozon_product_stock_d (库存快照, 通过 product_id+seller_id+offer_id 关联)
  │
  ├── ods_ozon_fbo_order_f (FBO订单主表, 平台仓发货)
  │     └── ods_ozon_fbo_order_product_f (FBO订单商品, 通过 posting_number 关联)
  │
  └── ods_ozon_fbs_order_f (FBS订单主表, 商家自发货)
        └── ods_ozon_fbs_order_product_f (FBS订单商品, 通过 posting_number 关联)
```

> **FBO** = Fulfillment by Ozon，平台仓储配送。卖家发货到Ozon仓库，Ozon负责存储、打包、配送。
> **FBS** = Fulfillment by Seller，商家自发货。卖家自己仓储，收到订单后自行打包发货。

> **表名规则**: `_f` = 全量快照(Full)，`_d` = 按天快照(Daily)。
