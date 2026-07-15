-- 订单履约表 — 来源 Posting API
-- 用途: 退货归因（posting_number → created_at）+ 漏斗分析（delivered / cancelled）
CREATE TABLE IF NOT EXISTS ozon.postings (
    posting_number VARCHAR(255) PRIMARY KEY,
    order_number   VARCHAR(255),
    delivery_schema VARCHAR(20),
    status         VARCHAR(50),
    cancel_reason_id INTEGER DEFAULT 0,
    created_at     TIMESTAMPTZ,
    in_process_at  TIMESTAMPTZ,
    delivered_at   TIMESTAMPTZ,
    products       JSONB,
    synced_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_postings_status ON ozon.postings(status);
CREATE INDEX IF NOT EXISTS idx_postings_created_at ON ozon.postings(created_at);
CREATE INDEX IF NOT EXISTS idx_postings_delivered_at ON ozon.postings(delivered_at);
