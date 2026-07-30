
# PostgreSQL omsprod — 申购/采购/发货 6表


## purchase_plan

| 字段 | 说明 | 例1 | 例2 |
|------|------|-----|-----|
| `id` |  | 1989113041594896386 | 1988093539558117377 |
| `po_plan_no` | 采购申购单号 | QG250926545 | PR2511110085 |
| `status` | 状态 0：待提交、1：待审批、 2：待创建采购单 3：部分创建采购订单 4、已创建采购订单 5、已作废 6.审批中 | 4 | 4 |
| `memo` | 备注 | 春节备货，2026年3月16日左右发往海外仓 | NULL |
| `create_by` |  | 1873928943736360961 | 10020 |
| `create_time` |  | 2025-09-26 15:49:24 | 2025-11-11 11:56:51 |
| `update_by` |  | 1901456830391554049 | 1931895248651698178 |
| `update_time` |  | 2026-03-16 19:15:29 | 2025-11-14 12:02:50 |
| `erp_id` |  | NULL | NULL |
| `sync_to_erp` |  | N | N |
| `erp_try_time` |  | 0 | 0 |
| `sync_erp_error_msg` |  |  |  |
| `erp_number` |  | NULL | NULL |
| `create_dept` |  | 1230000000001040303 | 1888157400544481281 |
| `tenant_id` | 租户编号 | 000000 | 000000 |
| `approval_id` | 下一审批人 | 10049 | NULL |
| `head_id` | 运营人员 | 1873928943736360961 | 10020 |
| `approval_status` | 审批状态 0：待审批 1：运营经理 2：计划员 3:计划经理 | 2 | 2 |
| `process_instance_id` | 流程实例ID | NULL | NULL |
| `approval_time` | 最终审批时间 | 2025-09-28 14:57:20 | 2025-11-13 15:05:13 |
| `df_flag` | 鼎发业务标识 | NULL | NULL |
| `sync_ding_flag` | 同步到钉钉标识 | NULL | NULL |
| `sync_ding_error_msg` | 同步到钉钉错误信息 | NULL | NULL |
| `pull_ding_flag` | 拉取钉钉标识 | NULL | NULL |
| `pull_ding_error_msg` | 拉取钉钉失败标志 | NULL | NULL |
| `plan_type` | 申购类型:0-平台仓备货 1-海外仓备货 2-计划备货 3-组合备货 | 0 | 1 |
| `location_id` | 收货仓id | 1869548027929444353 | 1866686165495889922 |
| `stock_location_id` | 备货仓id | NULL | 12 |
| `plan_head_id` |  | NULL | NULL |
| `approval_desc` |  | NULL | NULL |
| `is_urgent` | 是否紧急 | N | NULL |
| `logistics_method` | 物流方式 | HAIYUN | HAIYUN |
| `customer_class_id` | 自定义分类(oms_order_class.id)，多个用逗号分开 | 1991323400934281217 | NULL |
| `wms_status` | 00初始，10已收货，20已质检，30已上架 | 30 | 30 |
| `wms_time` | WMS执行完成时间 | 2026-02-26 15:30:07 | 2025-12-03 13:02:29 |
| `return_reason` | 退回原因-只获取最新值 | NULL | NULL |
| `assembly_production_task_no` | 组装生产任务编号 | NULL | NULL |
| `task_status` | 组装生产任务状态:0:未到货,1:部分到货,2:已到货待打印拣货单,3:已打印待拣货,4:拣货中,5:生产中,6:已完成 | 0 | 0 |
| `purchase_application_review_time` | 申购审核完成时间 | NULL | NULL |
| `production_starts_time` | 生产开始时间/打印拣货单时间 | NULL | NULL |
| `is_rejected` | 是否被驳回 0否 1是 | 0 | 0 |
| `parent_po_plan_no` | 父申购单号 |  |  |
| `group_no` | 组合销售单号 |  |  |
| `is_group` | 是否组合销售单 Y是 N否 | N | N |
| `combo_flag` | 组合产品标识 0非组合 1组合产品父 2组合产品子 | 0 | 0 |
| `plan_source` | 单据来源 1采购申购单 2计划备货单 | 1 | 1 |
| `po_remark` | 采购标识 0:全部采购 1:部分采购 2:全部库存 | 0 | 0 |
| `shooting_status` | 拍摄状态 0无需拍摄 1待拍摄 2拍摄中 3已拍摄 | 0 | 0 |
| `is_new_product` | 是否新品 Y是 N否 | N | N |
| `final_approval_id` | 最终审批人 | NULL | 10041 |
| `is_year_stock` | 是否年底备货 0否 1是 | 1 | 0 |
| `is_need_purchase` | 是否需要创建采购单 0否 1是 | 1 | 1 |
| `requisition_no` | 备货需求单号 |  |  |
| `shipping_status` | 发货状态 | NULL | NULL |
| `tax_free_flag` | 税务标识：0-无票 1-退税 2-免税 | 0 | 0 |
| `cancel_reason` | 作废原因 | NULL | NULL |
| `need_sample_shooting` | 样品拍摄需求 0否 1是 | NULL | NULL |
| `is_combination_split` | 单品补货标识 | NULL | NULL |
| `transfer_flag` | 是否调拨 | 0 | 0 |


## purchase_plan_item

| 字段 | 说明 | 例1 | 例2 |
|------|------|-----|-----|
| `id` |  | 2072888843301572609 | 2066455097794908162 |
| `po_plan_no` | 采购计划单号 | PR2607030140 | PR2606150497 |
| `row_id` | 行号 | 1 | 1 |
| `item_id` | SKU编码 | 32512-Y06N0001-A01 | 30125-G02Y0001-X0029IWEFN |
| `plan_qty` | 计划采购数量 | 14 | 30 |
| `expect_date` | 期望交货日期 | 2026-07-10 | 2026-09-03 |
| `planner_id` | 计划员 | NULL | NULL |
| `store_id` | 销售店铺 | 2000771360717819906 | 1990000000000000110 |
| `fn_sku` | FNSKU | NULL | X0029IWEFN |
| `memo` | 备注 | NULL | NULL |
| `create_by` |  | 10086 | 1903997755399507969 |
| `create_time` |  | 2026-07-03 11:43:07 | 2026-06-15 17:37:43 |
| `update_by` |  | 1990245100895883265 | 1990245100895883265 |
| `update_time` |  | 2026-07-03 15:01:35 | 2026-07-04 15:14:37 |
| `already_qty` | 已下单数量 | 0 | 30 |
| `create_dept` |  | 2009913175807119361 | 1889881739954393090 |
| `tenant_id` | 租户编号 | 000000 | 000000 |
| `asin` | Asin | NULL | NULL |
| `new_flag` | 是否首单 0：否 1：是 | 0 | 0 |
| `marketplace` | 站点名称 | ID | UK |
| `order_type` | 下单类型： 1、新品首单 2、新品返单 3、常规补货 4、集中备货 5、老品新上 6、凑起订量 7、备料订单 | NULL | NULL |
| `seller_sku` |  | 32512-Y06N0001-A01 | UKG3-19-0039 |
| `platform` |  | Shopee | Amazon |
| `package_qty` |  | 1 | 10 |
| `expect_arrive_date` | 采购预计交期 | 2026-07-08 | 2026-06-27 |
| `created_shipping_plan_qty` | 已创建发货计划数量 | 10 | 30 |
| `shipping_plan_status` | 创建发货计划状态:0-待创建 1-部分创建 2-已创建 | 1 | 2 |
| `wms_rec_qty` | WMS收货数量 | 14 | 30 |
| `wms_check_qty` | WMS质检合格数量 | 14 | 30 |
| `wms_onstock_qty` | WMS上架数量 | 14 | 30 |
| `expect_delivery_date` | 期望仓库发货时间 | 2026-07-18 | 2026-07-07 |
| `warehouse_item_code` | 海外仓条码 | YC3757-32512-Y06N0001-A01 |  |
| `main_sku_id` | 主sku | 32512 | 30125 |
| `seller_sku_id` | 平台SKUID | 2018516700044742657 | 6660000000000024501 |
| `next_shipment_reason` | 下次发货原因 |  |  |
| `match_qty` | 匹配到公共库存的数量 | 14 | 0 |
| `match_exclusive_qty` | 匹配到专属库存的数量 | 0 | 0 |
| `is_deduct` | 是否可抵扣  0否 1是 | 0 | 0 |
| `direct_ship_arrival_qty` | 直发采购到货数 | 0 | 0 |
| `direct_ship_arrival_time` | 直发确认到货时间（多次确认覆盖） | 2026-07-03 15:01:35 | 2026-06-16 12:02:14 |


## purchase_order

| 字段 | 说明 | 例1 | 例2 |
|------|------|-----|-----|
| `id` |  | 2033784932192243714 | 2026531027238539265 |
| `po_no` | 采购单号 | PO2603170440 | PO2602250795 |
| `vendor_id` | 供应商 | 1895077172562145282 | 1895077095722496005 |
| `location_id` | 仓库 | 1866686165495889922 | 1866686165495889922 |
| `po_type` | 采购订单类型：1：计划采购 | 1 | 1 |
| `subsidiary_id` | 公司 | 1951172199303630850 | 1951172199303630850 |
| `approval_status` | 审批状态 0：待审批 1：待主管审批 2：待经理审批 | 3 | 3 |
| `dept_id` | 部门 | 1862101990960173057 | 1862101990960173057 |
| `receipt_date` | 收货日期-预计交货日期(期望交货日期) | 2026-03-22 | 2026-03-23 |
| `sku_type` | 采购订单SKU品类 1:玩具品类 2:非玩具品类 | 781 | 385 |
| `po_approverole` | 审批人 | 10006 | 10006 |
| `trandate` | 采购日期 | 2026-03-17 | 2026-02-25 |
| `po_purchaser_id` | 采购员 | 10054 | 1939867672571715585 |
| `untaxed_amount` | 未税金额 | 1440.00 | 2210.10 |
| `tax_amount` | 税额 | 0.00 | 0.00 |
| `template_memo` | 模板修改说明 | NULL | NULL |
| `other_memo` | 其他备注信息 |  |  |
| `memo` | 备注 | NULL | NULL |
| `status` | 状态 0：待提交 1：已提交 2：待审批 3:待入库 4：部分入库 5：异常  6 已作废 7 完结 21 待申请付款 22 待付款 31 已发货 32 已签收 6666 待下放 | 7 | 7 |
| `create_by` |  | 1957639757833719810 | 1990245100895883265 |
| `create_time` |  | 2026-03-17 13:58:08 | 2026-02-25 13:33:43 |
| `update_by` |  | -1 | NULL |
| `update_time` |  | 2026-04-09 10:01:10 | 2026-04-16 17:01:55 |
| `mode` | (废弃) | NULL | NULL |
| `tx_status` | (废弃) | NULL | NULL |
| `current_tx_status_msg` | (废弃) | NULL | NULL |
| `sync_to_wms` |  | NULL | NULL |
| `wms_try_time` |  | 0 | 0 |
| `sync_wms_error_msg` |  | NULL | NULL |
| `wms_id` |  | NULL | NULL |
| `wms_number` |  | NULL | NULL |
| `erp_id` |  | NULL | NULL |
| `sync_to_erp` |  | N | N |
| `erp_try_time` |  | 0 | 0 |
| `sync_erp_error_msg` |  | NULL | NULL |
| `erp_number` |  | NULL | NULL |
| `create_dept` |  | 1922140285248901121 | 1922140285248901121 |
| `currency_code` | 币别 | CNY | CNY |
| `tenant_id` | 租户编号 | 000000 | 000000 |
| `approve_desc` | 审批描述 |  |  |
| `supplier_settlement` | 结算方式 | 1928079381154885633 | 1933347218503671809 |
| `other_cost` | 其它费用 | 0.00 | 0.00 |
| `already_pay_amount` | 已出账金额 | 1423.00 | 2100.00 |
| `amount` | 总金额 | 1423.00 | 2100.00 |
| `process_instance_id` | 流程实例ID | 3375861 | 3157188 |
| `is_push_success` | 领星：是否推送成功 | NULL | NULL |
| `push_error_details` | 领星：推送错误信息 | NULL | NULL |
| `df_flag` | 鼎发业务标识 | NULL | NULL |
| `lx_number` | 领星采购单号 | NULL | NULL |
| `if_in_transit_count` | 是否参与在途计算 1：参加 0：不参加 (废弃) | 1 | 1 |
| `customer_class_id` | 自定义分类(oms_order_class.id)，多个用逗号分开 | NULL | 1932051006236303362 |
| `prepayment_percent` | 预付款比例 | 100.00 | 10.00 |
| `discount_amount` | 折扣金额 | -150.00 | -128.70 |
| `prepayment_amount` | 预付款金额 | 1423.00 | 210.00 |
| `purchase_platform` | 采购平台 | 0 | 0 |
| `platform_po_no` | 平台单号 | 5102176141370346327 | 5087246653739346327 |
| `platform_po_status` | 平台状态 未下单 待付款 待发货 部分发货 待收货 虚假发货  已收货 已完成 已关闭 等待还款 部分退款 全部退款 | waitbuyerreceive | waitsellersend |
| `payment_status` | 付款状态 0：待付款 1：审核不通过 2：已申请付款 3:部分付款 4:已全部付款 | 4 | 3 |
| `logistics_name` | 物流公司 | 顺心捷达 | NULL |
| `logistics_num` | 物流单号 | S70412043421 | NULL |
| `bill1688_status` | 1688对账状态 0：异常 1：正常 | 1 | 1 |
| `exception_type` | 异常类型 1：来错货 2：少来货 3：多来货 | NULL | NULL |
| `exception_desc` | 来货异常说明 | NULL | NULL |
| `logistics_last_updtime` | 物流最后更新时间 | 2026-03-21 14:04:38 | 2026-03-19 15:25:26 |
| `logistics_last_desc` | 物流最后跟踪信息 | 包裹已由派件员姓名：张士强（勿找商家，有事请呼我），派件员电话:4007006888转41557/18922919697，送达【优优公司  】签收。签收网点电话：4007006888转41557/18 | 发货 |
| `sync_platform_status` | 同步平台状态 0:未同步 1：已同步 | 1 | 1 |
| `purchase_amount` | 采购金额 | 1423.000 | 2100.000 |
| `account_id` | 下单子账号ID(oms_taobao_account.id) | 1925740136287870978 | 1925740136287870978 |
| `expected_pay_time` | 下单预计付款时间 | 2026-03-18 09:13:08 | 2026-02-27 16:13:43 |
| `shipping_fee` | 运费 | 73.00 | 0.00 |
| `platform_amount` | 平台金额 | 1423.00 | 2100.00 |
| `red_discount_amount` | 红包优惠 | 0.00 | 0.00 |
| `line_up_down_flag` | 线上线下标识:1:线上 2:线下， | 1 | 1 |
| `platform_order_notes` | 1688下单备注 | 订单商品数量：60PCS | 订单商品数量：30PCS |
| `is_send_affirm` | 是否发送送货单 1:已发送 0:未发送 | 1 | 1 |
| `is_confirm_message` | 是否确认留言 0：未确认 1：已确认 | 0 | 1 |
| `is_confirm_date` | 是否确认交期 0 否 1 是 | 0 | 1 |
| `purchase_expect_date` | 采购期望交期 | 2026-03-23 | 2026-02-23 |
| `approval_time` | 审批通过时间 | 2026-03-18 13:33:49 | 2026-02-28 16:54:50 |
| `purchase_order_status` | 采购订单状态,数据字典：purchase_order_status，供应商点击触发，暂时不用 | NULL | NULL |
| `is_more_purchase_plan` | 是否多申购单 0否 1是 | 0 | 0 |
| `is_match_stock_exception` | 是否匹配库存异常 0否 1是 | 0 | 0 |
| `is_less_min_order` | 满足订量 0否1是 | 1 | 1 |
| `is_new_warehouse` | 是否新仓库 0否1是 | 3 | 4 |
| `is_year_stock` | 是否年底备货 0否 1是 | 0 | 0 |
| `price_time` | 核价时间 | 2026-03-18 11:30:49 | 2026-02-27 16:15:49 |
| `is_split` | 拆分产品采购单标识，0-否，1-是 | 0 | 0 |
| `cancel_by` | 作废人 | NULL | NULL |
| `cancel_time` | 作废时间 | NULL | NULL |
| `cancel_type` | 作废类型 | NULL | NULL |
| `cancel_reason` | 作废原因 | NULL | NULL |
| `is_new_purchase` | 是否新采，0-否，1-是 | 1 | 0 |
| `new_amazon_product` | amazon新品标签，0-否，1-是 | 1 | 0 |
| `contract_no` | 合同编号 |  |  |
| `tax_free_flag` | 税务标识：0-无票 1-退税 2-免税 | 0 | 0 |
| `purchase_dept_type` | 采购部门类型  1 家具事业部 2供应链中心 | 2 | 2 |
| `sample_version` | 样品次样(样品申购专有，数字为几表示几次样) | NULL | NULL |
| `approval_deadline` | 审批截止时间 | NULL | NULL |
| `pay_way` | 1688订单支持的支付方式编码列表，逗号分隔 | NULL | NULL |


## purchase_order_item

| 字段 | 说明 | 例1 | 例2 |
|------|------|-----|-----|
| `id` |  | 2036316949572243457 | 2048977811344740354 |
| `create_by` |  | 1990245100895883265 | 1990245100895883265 |
| `create_time` |  | 2026-03-24 13:39:28 | 2026-04-28 12:09:13 |
| `update_by` |  | 1990245100895883265 | -1 |
| `update_time` |  | 2026-04-03 14:54:19 | 2026-05-05 15:57:48 |
| `package_qty` | 单箱数量 | 1 | 5 |
| `create_dept` |  | 1922140285248901121 | 1922140285248901121 |
| `po_no` | 采购单号 | PO2603240494 | PO2604280457 |
| `row_id` | 行号 | 1 | 1 |
| `item_id` | SKU编码 | NULL | NULL |
| `price` | 未税单价 | 377.90 | 29.00 |
| `qty` | 采购数量 | 40 | 20 |
| `tax_rate` | 税率(%) | 0.00 | 0.00 |
| `untaxed_amount` | 未税金额 | 15116.00 | 580.00 |
| `tax_amount` | 税额 | NULL | NULL |
| `labor_cost` | 分摊人工费 | 1.00 | 1.00 |
| `mold_cost` | 分摊开模费 | 0.00 | 0.00 |
| `risk_value` | 分摊风险系数费用 | 0.00 | 0.00 |
| `expect_receipt_date` | 采购预计交期 | 2026-04-07 | 2026-05-10 |
| `receipt_qty` | 采购收货数量 | 40 | 20 |
| `source_price` | 原未税单价 | 377.90 | 28.80 |
| `cut_price` | 扣减单价 | 0.00 | 0.00 |
| `expect_date` | 计划要求到货日期 | 2026-06-02 | 2026-07-16 |
| `po_plan_no` | 采购计划单号 | PR2603230468 | PR2604270479 |
| `plan_row_id` | 采购计划明细行号 | 1 | 1 |
| `memo` | 备注 | 多补一点，避免断货 | NULL |
| `already_pay_amount` | 已生成账单金额 | 0.00 | 0.00 |
| `return_qty` | 已退货数量 | 0 | 0 |
| `bg_price` | 报关价 | 0.0000 | 0.0000 |
| `bg_chinesename` | 中文报关品名(开票名称) | NULL | NULL |
| `bg_model` | 出口报关型号(开票型号) | NULL | NULL |
| `bg_unit` | 成交单位(开票单位) | NULL | NULL |
| `tax_rate_kingdee` | 税率(%)(金蝶) | 0.00 | 0.00 |
| `price_tax_kingdee` | 含税单价(金蝶) | 377.90 | 28.80 |
| `amount_kingdee` | 金额(金蝶) | 15116.00 | 576.00 |
| `tax_amount_kingdee` | 税额(金蝶) | 15116.00 | 576.00 |
| `notified_flag` | 已通知收标： 1.已通知 2.未通知 | 0 | 0 |
| `if_doc` | 是否加DOC符合性声明：0：否  1：是  | 0 | 0 |
| `if_product_compliance_ifm` | 是否加产品上的合规信息: 0：否 1：是 | 0 | 0 |
| `if_instructions_compliant` | 说明书是否合规：0：否 1：是 | 0 | 0 |
| `if_color_box_compliant` | 彩盒是否合规：0：否 1：是 | 0 | 0 |
| `if_europe_britain` | 是否欧代英代 | 0 | 0 |
| `if_version_four` | 是否采用第四版合规2024-11-7 | NULL | NULL |
| `platform_qty` | 平台下单数量 | NULL | 20 |
| `last_price` | 上次采购单价 | NULL | NULL |
| `discount_amount` | 折扣金额 | 0.00 | 0.00 |
| `platform_price` | 平台1688单价 | NULL | NULL |
| `reject_qty` | 次品数量 | 0 | 0 |
| `offer_id` | 1688接口-商品对应的offer id | NULL | 1043513691949 |
| `spec_id` | 1688接口-商品规格id | NULL | 473c6956124d1348cb7a617fd9fd4efd |
| `sku_purchase_rul` | 采购链接 | https://detail.1688.com/offer/614194151631.html | https://detail.1688.com/offer/1043513691949.html?spm=a28888.manage-offer.0.0.26227197JuhcoH |
| `location_id` | 仓库 | NULL | NULL |
| `tax` | 税额 | 0.000 | 0.000 |
| `amount_with_tax` | 含税价格 | 15116.000 | 580.000 |
| `track_status` | 跟踪状态 待收货、已验收、已质检、已上架 | 3 | 3 |
| `platform_sub_item_id` | 平台子订单id | NULL | 5112618483624346327 |
| `shipping_plan_status` | 发货计划创建状态 0-待创建 1-部分创建 2-已创建 | 0 | 0 |
| `marketplace_code` | 站点 | US | UK |
| `sale_platform` | 销售平台 | Amazon | Amazon |
| `third_location_id` | 第三方仓/平台仓 | NULL | NULL |
| `head_id` | 运营人员/申购人 | 10232 | 1903997755399507969 |
| `sale_store_id` | 销售店铺 | NULL | NULL |
| `accepted_time` | wms回传的验收时间 | 2026-04-03 13:42:11 | 2026-05-04 11:24:23 |
| `check_date` | Wms回传的质检时间 | 2026-04-03 13:47:58 | 2026-05-04 11:27:50 |
| `already_listed_time` | Wms回传的上架时间 | 2026-04-03 14:54:19 | 2026-05-05 15:57:47 |
| `pending_shipment_qty` | 发货单待发货数量 | 40 | 20 |
| `other_cost` | 其他费用 | 0.00 | 0.00 |
| `main_sku_id` | 主sku | 20300 | 20527 |
| `tax_price` | 含税单价 | 377.90 | 29.00 |
| `other_tax_rate` | 其他税率 | 0.00 | 0.00 |
| `vendor_tax_type` | 供应商税务类型:0无票 1退税 2免税 | 0 | 0 |
| `price_with_freight` | 含运单价（未税） | 377.90 | 29.00 |
| `tax_price_with_freight` | 含运单价（含税） | 377.90 | 29.00 |
| `amount_with_tax_new` | 含税单价(最新) | 377.9000 | 28.8000 |
| `untaxed_amount_new` | 不含税单价(最新) | 377.9000 | 28.8000 |
| `freight` | 运费(最新) | 0.0000 | 1.3700 |
| `tax_new` | 税额(最新) | 0.0000 | 0.0000 |
| `receive_qty_sum` | 收货数量总和 | 40 | 20 |
| `return_qty_sum` | 退货数量总和 | 0 | 0 |
| `put_completed_qty_sum` | 上架数量总和 | 40 | 20 |
| `receipt_time` | 收货时间（最后一次收货时间） | 2026-04-03 14:54:19 | 2026-05-05 15:57:48 |
| `put_no` | 上架单号 | PT2604030079 | PT2605040082 |
| `put_time` | 上架时间(最后一次上架时间) | NULL | NULL |
| `sample_price` | 样品价 | NULL | NULL |
| `percent_change` | 涨跌幅度：相对上一张同主SKU非作废采购单含税单价的百分比变化 | NULL | NULL |


## first_leg_shipping_order

| 字段 | 说明 | 例1 | 例2 |
|------|------|-----|-----|
| `id` |  | 2056568281012936705 | 2056264899983331330 |
| `order_code` | 发货单编号 | DE202605190055 | DE202605180091 |
| `plan_code` | 发货计划编号 | SP202605180006 | SP202605180029 |
| `shipment_plan_id` | 货件计划id | 2056189880330727425 | 2056262669972557826 |
| `plan_type` | 计划类型: 0-平台仓备货 1-海外仓备货 2-海外仓中转 | 0 | 0 |
| `channel_code` | 物流方式 | HAIYUN | HAIYUN-IPSF |
| `shipping_warehouse_id` | 发货仓 | 1866686165495889922 | 1866686165495889922 |
| `destination_warehouse_id` | 目的仓 | 1866765372188012546 | 1866765400516341762 |
| `destination_country_code` | 目的国 | US | US |
| `store_id` | 店铺id | 1940396863859892225 | 1940341403991580673 |
| `receiving_platform` | 收货平台 | Amazon | Amazon |
| `third_order_code` | 货件号(第三方入库单号) | FBA19DJK1DS9 | FBA19DH125BV |
| `shipping_plan_time` | 计划发货时间 | 2026-05-26 00:00:00 | 2026-05-20 00:00:00 |
| `ship_date` | 船期 | 2026-05-20 | 2026-05-20 |
| `picking_exception_status` | 拣货异常状态: 0-无 1-异常待处理 2-继续发货 3-停止发货 | 0 | 2 |
| `order_status` | 发货单状态(1-待推送到仓 2-待拣货 3-拣货完成,待装箱  4-装箱完成,待上传头程物流箱唛 5-待质检  6-待上传海外仓入库箱唛 7-待物流专员发货 8-待复核 10-复核完成,待发货 11-已发货 12-已到仓 13-部分到仓 9-已作废 ) | 13 | 11 |
| `warehouse_arrival_status` | 到仓状态:0-未到仓 1-部分到仓 2-全部到仓 | 0 | 0 |
| `create_by` |  | 10183 | 10064 |
| `create_time` |  | 2026-05-19 10:51:02 | 2026-05-18 14:45:30 |
| `update_by` |  | 10035 | 1947115411574902785 |
| `update_time` |  | 2026-05-27 11:28:59 | 2026-05-21 10:37:02 |
| `create_dept` |  | 2031176879487864833 | 1862103553028034562 |
| `remark` | 备注 |  |  |
| `logistics_order` | 物流单号 | LG202605270050 | LG202605210154 |
| `merge_tag` | 是否合并: 0-否 1-是 | 1 | 1 |
| `package_type` | 装箱类型 0-一箱一种sku 1-混装 | 0 | 0 |
| `packing_exception_status` | 装箱异常状态: 0-无 1-异常待处理 2-继续发货 3-停止发货 | 0 | 0 |
| `sync_to_wms` |  | N | Y |
| `wms_try_time` |  | 0 | 0 |
| `sync_wms_error_msg` |  | NULL |  |
| `packing_exception_remark` | 装箱异常处理备注 |  |  |
| `picking_exception_remark` | 拣货异常处理备注 |  | 1 |
| `is_agl` | 是否AGL | 0 | 0 |
| `shipping_time` | 发货时间 | 2026-05-28 11:51:33 | 2026-05-22 08:15:15 |
| `pushed_time` | 推送完成时间 | 2026-05-26 09:53:26 | 2026-05-18 14:50:16 |
| `picked_time` | 拣货完成时间 | 2026-05-26 11:04:31 | 2026-05-18 15:07:23 |
| `packed_time` | 装箱完成时间 | 2026-05-27 11:28:58 | 2026-05-18 15:16:53 |
| `qc_exception_status` | 质检异常状态 | 0 | 0 |
| `qc_exception_remark` | 质检异常处理备注 |  |  |
| `arrived_time` | 到仓时间 | 2026-07-14 12:59:19 | NULL |
| `shelving_time` | 上架时间 | 2026-07-20 07:49:13 | NULL |
| `is_official_provider` | 是否官方物流商(0-否 1-是) | 0 | 0 |
| `reference_id` | 货件跟踪码 | 1J7S29IL |  |
| `inbound_time` | 创建入库单时间 | NULL | NULL |
| `shipment_status` | 货件状态 | CLOSED | IN_TRANSIT |
| `tax_free_flag` | 税务标识：0-无票 1-退税 2-免税 | 0 | 0 |
| `product_qc_finish_time` | 产品质检完成时间 | 2026-05-27 13:28:27 | 2026-05-18 15:50:19 |
| `box_label_qc_finish_time` | 外箱标质检完成时间 | 2026-05-27 13:28:35 | 2026-05-18 15:51:03 |
| `packer_id` | 装箱人 | 1972105089117868034 | 1972105089117868034 |
| `is_direct_ship` | 是否供应商直发,0-不直发 1-直发 | 0 | 0 |
| `label_provided` | 是否提供物流标签,0-否 1-是 | 0 | 0 |
| `form_id` | 来源编号(批次号),多个货件可能是统一批次创建的 | wf82b36543-6f3e-46af-9573-9e94e5ce752d | wf609214e3-3d7d-45e0-81cb-a6977aea8ba5 |
| `cancel_reason` | 标记不发货原因 |  |  |


## first_leg_shipping_order_item


# MySQL db_warehouse — Ozon 6表

| 字段 | 说明 | 例1 | 例2 |
|------|------|-----|-----|
| `id` |  | 2075491591276744705 | 2075491591280939010 |
| `item_id` | 系统SKU | 40735-N02M0002-X005151F3L | 41020-N02M0001-X0051RNXXT |
| `source_order_code` | 来源单据号 | PR2606150310 | PR2606150309 |
| `fnsku` | fnsku | X005151F3L | X0051RNXXT |
| `update_reason` | 修改理由 |  |  |
| `package_qty` | 箱规-单箱数量 | 1 | 1 |
| `package_volume` | 箱规-单箱体积: 格式 50*20*30 cm | 76.00*43.00*14.00 | 75.00*35.00*10.00 |
| `package_weight` | 箱规-单箱重量 kg | 5.30 | 5.60 |
| `warehouse_qty` | 仓库-单箱数量 | 1 | 1 |
| `warehouse_volume` | 仓库-单箱体积: 格式 50*20*30 cm |  |  |
| `warehouse_weight` | 仓库-单箱重量 kg | 0.00 | 0.00 |
| `final_shipping_num` | 最终发货数 | 30 | 20 |
| `planed_shipping_num` | 计划发货数量 | 30 | 20 |
| `operation_shipping_num` | 运营发货数量 | 30 | 20 |
| `source_order_type` | 来源单据类型:PR-申购单 | PR | PR |
| `create_by` |  | 10207 | 10207 |
| `create_time` |  | 2026-07-10 16:05:31 | 2026-07-10 16:05:31 |
| `update_by` |  | 10207 | 10207 |
| `update_time` |  | 2026-07-10 16:05:31 | 2026-07-10 16:05:31 |
| `create_dept` |  | 2031176879487864833 | 2031176879487864833 |
| `shipping_order_id` | 发货单id | NULL | NULL |
| `category_id` | 品类id | 753 | 753 |
| `order_plan_id` | 申购商品行id | 2066440741128523778 | 2066440741124329475 |
| `shipping_order_code` | 发货单编号 | DE202607100161 | DE202607100161 |
| `row_id` | 行号 | 30 | 20 |
| `store_id` | 店铺id | 1940396863859892225 | 1940396863859892225 |
| `material` | 材质 | 铁 | 铁 |
| `asin` | ASIN |  |  |
| `warehouse_item_code` | 第三方商品条码 | X005151F3L | X0051RNXXT |
| `seller_sku` | 销售Sku | USN44-40735 | USN44-41020 |
| `main_sku_id` | 主sku | 40735 | 41020 |
| `final_planed_shipping_num` | 最终计划确认数量 | 30 | 20 |
| `head_id` | 运营人员 | 10207 | 10207 |
| `head_dept_id` | 运营人员部门 | 2031176879487864833 | 2031176879487864833 |
| `inbound_putaway_qty` | 海外仓上架数量 | 0 | 0 |
| `po_no` | 采购单号 | PO2606160265 | PO2606160266 |
| `vendor_id` | 供应商 | 1895077355941310483 | 1895077355941310483 |
| `po_purchaser_id` | 采购员 | 10312 | 10312 |
| `qc_status` | 质检状态:0-待质检 1-已质检 | 0 | 0 |


## ods_ozon_product_f

| 字段 | 说明 | 例1 | 例2 |
|------|------|-----|-----|
| `product_id` |  | 1954466990 | 1954467061 |
| `seller_id` |  | 3013635 | 3013635 |
| `offer_id` |  | 29714-Y07U0002-A01 | 31248-Y07U0001-A01 |
| `archived` |  | 0 | 0 |
| `has_fbo_stocks` |  | 0 | 0 |
| `has_fbs_stocks` |  | 1 | 1 |
| `quants` |  | [] | [] |
| `barcodes` |  | [] | [] |
| `color_image` |  | [] | [] |
| `commissions` |  | [{"delivery_amount":2.22,"percent":14,"return_amount":47.07,"sale_schema":"FBO","value":55.3},{"deli | [{"delivery_amount":2.22,"percent":14,"return_amount":11.17,"sale_schema":"FBO","value":20.3},{"deli |
| `description_category_id` |  | 17028665 | 17028665 |
| `discounted_fbo_stocks` |  | 0 | 0 |
| `has_discounted_fbo_item` |  | 0 | 0 |
| `is_autoarchived` |  | 0 | 0 |
| `is_discounted` |  | 0 | 0 |
| `is_kgt` |  | 0 | 0 |
| `is_prepayment_allowed` |  | 1 | 1 |
| `is_super` |  | 0 | 0 |
| `marketing_price` |  | 395.00 | 145.00 |
| `min_price` |  |  |  |
| `model_id` |  | 513372215 | 490618036 |
| `model_count` |  | 9 | 7 |
| `name` |  | До 1500 деталей Головоломка 2-в-1: подставка и крышка, 6 разноцветных ящиков, темно-серый цвет | Коврик для пазлов на 500, 1000, 1500, 2000 деталей, коврик и аксессуары для сборки пазлов серый зеле |
| `old_price` |  | 699.00 | 300.00 |
| `price` |  | 395.00 | 145.00 |
| `price_indexes` |  | {"color_index":"COLOR_INDEX_WITHOUT_INDEX","external_index_data":{"minimal_price":"","minimal_price_ | {"color_index":"COLOR_INDEX_WITHOUT_INDEX","external_index_data":{"minimal_price":"","minimal_price_ |
| `primary_image` |  | ["https://cdn1.ozone.ru/s3/multimedia-1-a/7578820846.jpg"] | ["https://cdn1.ozone.ru/s3/multimedia-1-c/7405034016.jpg"] |
| `promotions` |  | [{"is_enabled":true,"type":"REVIEWS_PROMO"}] | [{"is_enabled":false,"type":"REVIEWS_PROMO"}] |
| `sku` |  | 2276172200 | 2276172674 |
| `sources` |  | [{"sku":2276172200,"source":"sds","created_at":"2025-06-12T02:11:52.360850Z","shipment_type":"SHIPME | [{"sku":2276172674,"source":"sds","created_at":"2025-06-12T02:11:57.065747Z","shipment_type":"SHIPME |
| `statuses` |  | {"status":"price_sent","status_failed":"","moderate_status":"approved","validation_status":"success" | {"status":"price_sent","status_failed":"","moderate_status":"approved","validation_status":"success" |
| `stocks` |  | {"has_stock":true,"stocks":[{"present":200,"reserved":0,"sku":2276172200,"source":"fbs"}]} | {"has_stock":true,"stocks":[{"present":200,"reserved":0,"sku":2276172674,"source":"fbs"}]} |
| `type_id` |  | 92941 | 92941 |
| `updated_at` |  | 2025-06-12 02:23:24 | 2025-06-12 02:24:25 |
| `vat` |  | 0.00 | 0.00 |
| `visibility_details` |  | {"has_price":true,"has_stock":true} | {"has_price":true,"has_stock":true} |
| `volume_weight` |  | 6.70 | 1.40 |
| `create_time` |  | 2025-09-20 10:45:13 | 2025-09-20 10:45:13 |
| `update_time` |  | 2025-10-15 03:45:03 | 2025-10-15 03:45:04 |


## ods_ozon_product_stock_d

| 字段 | 说明 | 例1 | 例2 |
|------|------|-----|-----|
| `product_id` |  | 1903953946 | 1903953946 |
| `seller_id` |  | 3012909 | 3012909 |
| `offer_id` |  | 15079-Y07U0007-B01 | 15079-Y07U0007-B01 |
| `fbo_present` |  | 177 | 178 |
| `fbo_reserved` |  | 1 | 1 |
| `fbo_sku` |  | 2238512937 | 2238512937 |
| `fbo_shipment_type` |  | SHIPMENT_TYPE_GENERAL | SHIPMENT_TYPE_GENERAL |
| `fbo_warehouse_ids` |  | [] | [] |
| `fbs_present` |  | 0 | 0 |
| `fbs_reserved` |  | 0 | 0 |
| `fbs_sku` |  | 2238512937 | 2238512937 |
| `fbs_shipment_type` |  | SHIPMENT_TYPE_GENERAL | SHIPMENT_TYPE_GENERAL |
| `fbs_warehouse_ids` |  | [] | [] |
| `create_time` |  | 2025-09-20 09:35:40 | 2025-09-20 09:35:40 |
| `update_time` |  | 2026-03-02 00:22:13 | 2026-03-01 00:22:18 |
| `batch_no` |  | 2026-03-02 | 2026-03-01 |


## ods_ozon_fbo_order_f

| 字段 | 说明 | 例1 | 例2 |
|------|------|-----|-----|
| `posting_number` |  | 00508709-0804-1 | 0100707912-0060-1 |
| `seller_id` |  | 3018128 | 3012909 |
| `order_id` |  | 32976980805 | 33815733656 |
| `order_number` |  | 00508709-0804 | 0100707912-0060 |
| `status` |  | delivered | delivered |
| `cancel_reason_id` |  | 0 | 0 |
| `created_at` |  | 2025-12-23 20:24:13 | 2025-12-09 12:06:01 |
| `in_process_at` |  | 2025-12-23 20:24:29 | 2025-12-09 12:06:10 |
| `legal_info` |  | {"company_name":"","inn":"","kpp":""} | {"company_name":"","inn":"","kpp":""} |
| `analytics_data` |  | NULL | NULL |
| `additional_data` |  | [] | [] |
| `create_time` |  | 2025-12-25 00:22:14 | 2025-12-10 00:22:04 |
| `update_time` |  | 2026-01-22 00:22:05 | 2026-01-08 00:22:05 |


## ods_ozon_fbo_order_product_f

| 字段 | 说明 | 例1 | 例2 |
|------|------|-----|-----|
| `id` |  | 00342354-1694-1_30305-Y07U0006-B01 | 0100736701-0093-1_30297-Y07U0003-B03 |
| `posting_number` |  | 00342354-1694-1 | 0100736701-0093-1 |
| `sku` |  | 2482935662 | 2393417469 |
| `name` |  | Коврик-стол для пазлов с 6 цветной ящик,Стол коврик для сборки пазлов 1000PCS светло-серый 77X54CM | Сиденье для душа откидное Fold & Sit / Стул для ванной / складное настенное сиденье |
| `quantity` |  | 1 | 1 |
| `offer_id` |  | 30305-Y07U0006-B01 | 30297-Y07U0003-B03 |
| `price` |  | 4850.00 | 6350.00 |
| `is_marketplace_buyout` |  | 0 | 0 |
| `digital_codes` |  | [] | [] |
| `currency_code` |  | RUB | RUB |
| `create_time` |  | 2025-10-15 03:40:02 | 2025-12-24 00:22:08 |
| `update_time` |  | 2025-11-13 00:22:06 | 2026-01-22 00:22:05 |


## ods_ozon_fbs_order_f

| 字段 | 说明 | 例1 | 例2 |
|------|------|-----|-----|
| `posting_number` |  | 00383143-0753-1 | 0101124226-0023-1 |
| `seller_id` |  | 3012909 | 3018128 |
| `order_id` |  | 30425686311 | 30446872178 |
| `order_number` |  | 00383143-0753 | 0101124226-0023 |
| `status` |  | delivered | delivered |
| `substatus` |  | posting_received | posting_received |
| `delivery_id` |  | 1020005000204760 | 1020005000205801 |
| `delivery_name` |  | Доставка Ozon самостоятельно, Balashikha | Доставка Ozon самостоятельно, Balashikha |
| `delivery_warehouse_id` |  | 1020005000204760 | 1020005000205801 |
| `delivery_warehouse` |  | EY-FBS | EY-FBS |
| `delivery_tpl_provider_id` |  | 24 | 24 |
| `delivery_tpl_provider` |  | Доставка Ozon | Доставка Ozon |
| `tracking_number` |  |  |  |
| `tpl_integration_type` |  | ozon | ozon |
| `in_process_at` |  | 2025-08-13 10:54:18 | 2025-09-03 19:16:33 |
| `shipment_date` |  | 2025-08-13 15:00:00 | 2025-09-03 15:00:00 |
| `delivering_date` |  | 2025-08-14 14:55:13 | 2025-09-04 15:19:50 |
| `cancel_reason_id` |  | 0 | 0 |
| `cancel_reason` |  |  |  |
| `cancellation_type` |  |  |  |
| `cancelled_after_ship` |  | 0 | 0 |
| `affect_cancellation_rating` |  | 0 | 0 |
| `cancellation_initiator` |  |  |  |
| `customer` |  | NULL | NULL |
| `addressee` |  | NULL | NULL |
| `barcodes` |  | NULL | NULL |
| `analytics_data` |  | NULL | NULL |
| `financial_data` |  | NULL | NULL |
| `is_express` |  | 0 | 0 |
| `legal_info` |  | {"company_name":"","inn":"","kpp":""} | {"company_name":"","inn":"","kpp":""} |
| `products_requiring_gtd` |  | [] | [] |
| `products_requiring_country` |  | [] | [] |
| `products_requiring_mandatory_mark` |  | [] | [] |
| `products_requiring_rnpt` |  | [] | [] |
| `products_requiring_jw_uin` |  | [] | [] |
| `products_requiring_change_country` |  | [] | [] |
| `products_requiring_imei` |  | [] | [] |
| `products_requiring_weight` |  | [] | [] |
| `parent_posting_number` |  |  |  |
| `available_actions` |  | [] | [] |
| `multi_box_qty` |  | 1 | 1 |
| `is_multibox` |  | 0 | 0 |
| `prr_option` |  |  |  |
| `quantum_id` |  | 0 | 0 |
| `current_tariff_rate` |  | 0 | 0 |
| `current_tariff_type` |  |  |  |
| `current_tariff_charge` |  |  |  |
| `current_tariff_charge_currency_code` |  |  |  |
| `next_tariff_rate` |  | 0.00 | 0.00 |
| `next_tariff_type` |  |  |  |
| `next_tariff_charge` |  |  |  |
| `next_tariff_starts_at` |  | NULL | NULL |
| `next_tariff_charge_currency_code` |  |  |  |
| `destination_place_id` |  | 0 | 0 |
| `destination_place_name` |  |  |  |
| `is_presortable` |  | 0 | 0 |
| `pickup_code_verified_at` |  | NULL | NULL |
| `optional` |  | {"products_with_possible_mandatory_mark":[]} | {"products_with_possible_mandatory_mark":[]} |
| `create_time` |  | 2025-09-19 18:26:52 | 2025-09-19 18:26:55 |
| `update_time` |  | 2025-09-19 19:36:40 | 2025-10-03 03:41:02 |


## ods_ozon_fbs_order_product_f

| 字段 | 说明 | 例1 | 例2 |
|------|------|-----|-----|
| `id` |  | 00383143-0753-1_14435-Y07U0008-B01 | 0101124226-0023-1_30283-Y07U0001-A01 |
| `offer_id` |  | 14435-Y07U0008-B01 | 30283-Y07U0001-A01 |
| `posting_number` |  | 00383143-0753-1 | 0101124226-0023-1 |
| `price` |  | 7959.00 | 1500.00 |
| `name` |  | Коврик-стол для пазлов с Цветная коробка ящиками,Органайзер для пазлов 2000 таблеток темно-серый | 6шт насадок на шланг для ВЫСОКОДАВЛЕННОЙ промывки канализации прочистка труб под давлением 5000 PSI |
| `sku` |  | 2306440040 | 2529264542 |
| `quantity` |  | 1 | 1 |
| `currency_code` |  | RUB | RUB |
| `is_blr_traceable` |  | 0 | 0 |
| `is_marketplace_buyout` |  | 0 | 0 |
| `imei` |  | [] | [] |
| `create_time` |  | 2025-09-19 18:26:53 | 2025-09-19 18:26:55 |
| `update_time` |  | 2025-09-19 19:36:40 | 2025-10-03 03:41:02 |
