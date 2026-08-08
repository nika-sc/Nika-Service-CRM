-- 015: предварительная стоимость заявки (оценка для клиента, не касса)

ALTER TABLE orders ADD COLUMN IF NOT EXISTS estimated_cost TEXT DEFAULT '0';
