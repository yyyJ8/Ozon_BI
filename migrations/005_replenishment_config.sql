-- 迁移 005：补货提示配置表
-- 存储 Excel 中每个 SKU 的安全天数和物流天数

BEGIN;

CREATE TABLE IF NOT EXISTS ozon.replenishment_config (
    store_id        INTEGER NOT NULL,
    offer_id        VARCHAR(255) NOT NULL,
    product_name    TEXT,
    safety_days     INTEGER DEFAULT 5,
    logistics_days  INTEGER DEFAULT 45,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),

    PRIMARY KEY (store_id, offer_id)
);

CREATE INDEX IF NOT EXISTS idx_repl_config_offer
    ON ozon.replenishment_config(store_id, offer_id);

COMMIT;
