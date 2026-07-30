-- 迁移 004：补全 sku_management 表中遗漏的 Excel 列

BEGIN;

ALTER TABLE ozon.sku_management ADD COLUMN IF NOT EXISTS purchase_cost_pct     NUMERIC(6,2);
ALTER TABLE ozon.sku_management ADD COLUMN IF NOT EXISTS first_leg_pct         NUMERIC(6,2);
ALTER TABLE ozon.sku_management ADD COLUMN IF NOT EXISTS last_mile_pct         NUMERIC(6,2);
ALTER TABLE ozon.sku_management ADD COLUMN IF NOT EXISTS product_cost_rmb      NUMERIC(10,2);
ALTER TABLE ozon.sku_management ADD COLUMN IF NOT EXISTS discount_pct          NUMERIC(6,2);
ALTER TABLE ozon.sku_management ADD COLUMN IF NOT EXISTS platform_payout_rub   NUMERIC(10,2);
ALTER TABLE ozon.sku_management ADD COLUMN IF NOT EXISTS actual_payout_rub     NUMERIC(10,2);
ALTER TABLE ozon.sku_management ADD COLUMN IF NOT EXISTS profit_rmb            NUMERIC(10,2);
ALTER TABLE ozon.sku_management ADD COLUMN IF NOT EXISTS profit_rub            NUMERIC(10,2);
ALTER TABLE ozon.sku_management ADD COLUMN IF NOT EXISTS profit_margin_pct     NUMERIC(6,2);

COMMIT;
