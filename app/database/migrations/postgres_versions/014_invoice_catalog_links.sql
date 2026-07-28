-- 014: привязка позиций счёта к каталогу + shop_sale при оплате без заявки

ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS catalog_part_id BIGINT;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS catalog_service_id BIGINT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS shop_sale_id BIGINT;
CREATE INDEX IF NOT EXISTS idx_invoices_shop_sale_id ON invoices(shop_sale_id);
