-- ============================================================
-- 迁移 002：多店铺支持
-- 1. 建 stores 表
-- 2. 所有数据表加 store_id → 纳入复合主键
-- 3. 迁移现有数据 store_id=1
-- ============================================================

BEGIN;

-- ──────────────────────────────────────
-- 1. 店铺配置表
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS ozon.stores (
    id                 SERIAL PRIMARY KEY,
    name               VARCHAR(100) NOT NULL,
    client_id          VARCHAR(50)  NOT NULL,
    api_key            VARCHAR(100) NOT NULL,
    perf_client_id     VARCHAR(100),
    perf_client_secret VARCHAR(100),
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 店铺 1: Тихое Счастье
INSERT INTO ozon.stores (id, name, client_id, api_key, perf_client_id, perf_client_secret)
VALUES (1, 'Тихое Счастье', '4162868', '04c6742c-1de3-4038-9b9b-a59039c1acbb',
        '97790056-1784192090075@advertising.performance.ozon.ru',
        '7c4rSDHhAoVjzR2BXP8bjKUsGuit0CrdJ6oyRlBzr6hNIfQY_j8duT48-J1289R8voJD9agoBXbRLA-kpA')
ON CONFLICT (id) DO NOTHING;

-- 店铺 2: Новое Небо
INSERT INTO ozon.stores (id, name, client_id, api_key, perf_client_id, perf_client_secret)
VALUES (2, 'Новое Небо', '4111257', '1dc5a805-8925-4d5d-8f8f-1b6bbc3a64ae',
        '97551151-1784009809846@advertising.performance.ozon.ru',
        'pp4ha-Viog1a51PYIauqLSOic54Gohk49b6J9XcvqSmAcscP_XBZ1PGvS4lCD4WaXy4MY58yvbgs3SEejg')
ON CONFLICT (id) DO NOTHING;

-- ──────────────────────────────────────
-- 2. products — 主键 (sku_id) → (store_id, sku_id)
-- ──────────────────────────────────────
ALTER TABLE ozon.products ADD COLUMN IF NOT EXISTS store_id INT NOT NULL DEFAULT 1;
-- 先删 FK（stocks 依赖 products PK）
ALTER TABLE ozon.stocks DROP CONSTRAINT IF EXISTS stocks_sku_id_fkey;
ALTER TABLE ozon.products DROP CONSTRAINT IF EXISTS products_pkey;
ALTER TABLE ozon.products ADD PRIMARY KEY (store_id, sku_id);

-- ──────────────────────────────────────
-- 3. stocks — 主键 (sku_id, source) → (store_id, sku_id, source)，重建 FK
-- ──────────────────────────────────────
ALTER TABLE ozon.stocks ADD COLUMN IF NOT EXISTS store_id INT NOT NULL DEFAULT 1;
ALTER TABLE ozon.stocks DROP CONSTRAINT IF EXISTS stocks_pkey;
ALTER TABLE ozon.stocks ADD PRIMARY KEY (store_id, sku_id, source);
ALTER TABLE ozon.stocks
    ADD CONSTRAINT stocks_sku_id_fkey
    FOREIGN KEY (store_id, sku_id) REFERENCES ozon.products(store_id, sku_id);

-- ──────────────────────────────────────
-- 4. sku_daily_summary — 主键 (date, sku_id) → (store_id, date, sku_id)
-- ──────────────────────────────────────
ALTER TABLE ozon.sku_daily_summary ADD COLUMN IF NOT EXISTS store_id INT NOT NULL DEFAULT 1;
ALTER TABLE ozon.sku_daily_summary DROP CONSTRAINT IF EXISTS sku_daily_summary_pkey;
ALTER TABLE ozon.sku_daily_summary ADD PRIMARY KEY (store_id, date, sku_id);

-- ──────────────────────────────────────
-- 5. finance_transactions — 主键 (operation_id) → (store_id, operation_id)
-- ──────────────────────────────────────
ALTER TABLE ozon.finance_transactions ADD COLUMN IF NOT EXISTS store_id INT NOT NULL DEFAULT 1;
ALTER TABLE ozon.finance_transactions DROP CONSTRAINT IF EXISTS finance_transactions_pkey;
ALTER TABLE ozon.finance_transactions ADD PRIMARY KEY (store_id, operation_id);

-- ──────────────────────────────────────
-- 6. postings — 主键 (posting_number) → (store_id, posting_number)
-- ──────────────────────────────────────
ALTER TABLE ozon.postings ADD COLUMN IF NOT EXISTS store_id INT NOT NULL DEFAULT 1;
ALTER TABLE ozon.postings DROP CONSTRAINT IF EXISTS postings_pkey;
ALTER TABLE ozon.postings ADD PRIMARY KEY (store_id, posting_number);

-- ──────────────────────────────────────
-- 7. ad_campaigns — 主键 (campaign_id) → (store_id, campaign_id)
-- ──────────────────────────────────────
ALTER TABLE ozon.ad_campaigns ADD COLUMN IF NOT EXISTS store_id INT NOT NULL DEFAULT 1;
ALTER TABLE ozon.ad_campaigns DROP CONSTRAINT IF EXISTS ad_campaigns_pkey;
ALTER TABLE ozon.ad_campaigns ADD PRIMARY KEY (store_id, campaign_id);

-- ──────────────────────────────────────
-- 8. ad_daily_stats — 主键 (campaign_id, stat_date) → (store_id, campaign_id, stat_date)
-- ──────────────────────────────────────
ALTER TABLE ozon.ad_daily_stats ADD COLUMN IF NOT EXISTS store_id INT NOT NULL DEFAULT 1;
ALTER TABLE ozon.ad_daily_stats DROP CONSTRAINT IF EXISTS ad_daily_stats_pkey;
ALTER TABLE ozon.ad_daily_stats ADD PRIMARY KEY (store_id, campaign_id, stat_date);

-- ──────────────────────────────────────
-- 9. ad_campaign_sku_map — 主键 (campaign_id, sku_id) → (store_id, campaign_id, sku_id)
-- ──────────────────────────────────────
ALTER TABLE ozon.ad_campaign_sku_map ADD COLUMN IF NOT EXISTS store_id INT NOT NULL DEFAULT 1;
ALTER TABLE ozon.ad_campaign_sku_map DROP CONSTRAINT IF EXISTS ad_campaign_sku_map_pkey;
ALTER TABLE ozon.ad_campaign_sku_map ADD PRIMARY KEY (store_id, campaign_id, sku_id);

-- ──────────────────────────────────────
-- 10. ad_sku_daily_stats — 主键 (campaign_id, sku_id, stat_date) → (store_id, campaign_id, sku_id, stat_date)
-- ──────────────────────────────────────
ALTER TABLE ozon.ad_sku_daily_stats ADD COLUMN IF NOT EXISTS store_id INT NOT NULL DEFAULT 1;
ALTER TABLE ozon.ad_sku_daily_stats DROP CONSTRAINT IF EXISTS ad_sku_daily_stats_pkey;
ALTER TABLE ozon.ad_sku_daily_stats ADD PRIMARY KEY (store_id, campaign_id, sku_id, stat_date);

-- ──────────────────────────────────────
-- 11. returns — 主键 (id) → (store_id, id)
-- ──────────────────────────────────────
ALTER TABLE ozon.returns ADD COLUMN IF NOT EXISTS store_id INT NOT NULL DEFAULT 1;
ALTER TABLE ozon.returns DROP CONSTRAINT IF EXISTS returns_pkey;
ALTER TABLE ozon.returns ADD PRIMARY KEY (store_id, id);

-- ──────────────────────────────────────
-- 12. sync_log — 加 store_id 列 + 索引（主键不变）
-- ──────────────────────────────────────
ALTER TABLE ozon.sync_log ADD COLUMN IF NOT EXISTS store_id INT NOT NULL DEFAULT 1;
CREATE INDEX IF NOT EXISTS idx_sync_log_store ON ozon.sync_log(store_id);

COMMIT;
