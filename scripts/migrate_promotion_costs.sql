-- 添加 promotion_costs 列到 sku_daily_summary
-- 推广费（OperationPromotionWithCostPerOrder）从 Finance API 提取，
-- 之前只在内存中计算但未持久化
ALTER TABLE ozon.sku_daily_summary
ADD COLUMN IF NOT EXISTS promotion_costs NUMERIC(12, 2) DEFAULT 0;

COMMENT ON COLUMN ozon.sku_daily_summary.promotion_costs IS '推广费 RUB（负数，按单付费推广）';
