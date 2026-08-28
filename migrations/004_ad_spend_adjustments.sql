-- ============================================================
-- 迁移 004：广告花费归因调整规则表
-- 场景: 给 SKU A 投广告，买家进 A 后买了关联的 SKU B，
--       Ozon 报告把 spend 记在 A 头上 → A 花费虚高、B 虚低。
--       本表存"转移规则"，计算利润时把 A 的部分广告花费拨给 B。
-- 原则: 只存规则，不落调整后数据（原始 ad_sku_daily_stats 永不动，
--       规则随时可改、可停用、可回滚）。
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS ozon.ad_spend_adjustments (
    id            SERIAL PRIMARY KEY,
    store_id      INTEGER NOT NULL,          -- 店铺 ID
    from_sku_id   BIGINT  NOT NULL,          -- 转出方 SKU（广告入口，花费被高估）
    to_sku_id     BIGINT  NOT NULL,          -- 转入方 SKU（实际成交，花费被低估）
    ratio         NUMERIC(5,2),              -- 转移比例 %（如 50 = 转移50%），与 fixed_amount 二选一
    fixed_amount  NUMERIC(12,2),             -- 固定转移金额 RUB（按日），与 ratio 二选一
    campaign_id   VARCHAR(20),               -- 可选：仅作用于某活动；NULL = 全局（当前计算仅支持全局）
    date_from     DATE,                      -- 可选：生效起始日
    date_to       DATE,                      -- 可选：生效结束日
    note          TEXT,                      -- 备注
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ad_adj_amount_check CHECK (
        (ratio IS NOT NULL AND fixed_amount IS NULL)
        OR (ratio IS NULL AND fixed_amount IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_ad_spend_adjustments_store
    ON ozon.ad_spend_adjustments (store_id, is_active);

COMMIT;
