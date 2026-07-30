-- ============================================================
-- 迁移 003：SKU 手动管理数据表
-- 存储 Ozon API 之外的业务数据（采购成本、物流、竞品等）
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS ozon.sku_management (
    store_id      INTEGER NOT NULL,
    sku_id        BIGINT  NOT NULL,

    -- 基本信息
    main_sku              VARCHAR(50),
    source_url_1688       TEXT,
    specification         TEXT,
    sales_manager         VARCHAR(50),
    listed_stores         VARCHAR(50),
    product_status        VARCHAR(50),
    key_notes             TEXT,

    -- 尺寸重量（单品）
    length_cm             NUMERIC(8,2),
    width_cm              NUMERIC(8,2),
    height_cm             NUMERIC(8,2),
    actual_weight_kg      NUMERIC(8,2),
    volume_cbm            NUMERIC(8,4),
    density               NUMERIC(8,2),

    -- 包装 / 外箱
    first_leg_unit_price  NUMERIC(8,2),
    units_per_carton      INTEGER,
    carton_length_cm      NUMERIC(8,2),
    carton_width_cm       NUMERIC(8,2),
    carton_height_cm      NUMERIC(8,2),
    gross_weight_kg       NUMERIC(8,2),
    volume_liters         NUMERIC(8,2),

    -- 成本（RMB）
    purchase_cost_rmb     NUMERIC(10,2),
    warehousing_fee_rmb   NUMERIC(8,2),
    fbo_delivery_fee_rmb  NUMERIC(8,2),
    first_leg_cost_rmb    NUMERIC(10,2),

    -- 平台费用（₽ / 百分比）
    acquiring_fee_pct     NUMERIC(5,2),
    fbo_commission_pct    NUMERIC(5,2),
    logistics_rub         NUMERIC(10,2),
    delivery_pickup_rub   NUMERIC(10,2),
    advertising_rate_pct  NUMERIC(5,2),
    return_rate_pct       NUMERIC(5,2),
    tax_and_fee_pct       NUMERIC(5,2),
    risk_reserve_rub      NUMERIC(10,2),

    -- 财务
    exchange_rate         NUMERIC(10,4),
    green_price_rub       NUMERIC(10,2),

    -- 竞品
    competitor_1          VARCHAR(200),
    competitor_2          VARCHAR(200),
    competitor_sales      INTEGER,

    -- 元数据
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW(),

    PRIMARY KEY (store_id, sku_id),
    CONSTRAINT fk_sku_mgmt_product
        FOREIGN KEY (store_id, sku_id)
        REFERENCES ozon.products (store_id, sku_id)
        ON DELETE CASCADE
);

-- 索引：按主SKU查所有变体
CREATE INDEX IF NOT EXISTS idx_sku_mgmt_main_sku ON ozon.sku_management(store_id, main_sku);
-- 索引：按产品状态筛选
CREATE INDEX IF NOT EXISTS idx_sku_mgmt_status   ON ozon.sku_management(store_id, product_status);

COMMIT;
