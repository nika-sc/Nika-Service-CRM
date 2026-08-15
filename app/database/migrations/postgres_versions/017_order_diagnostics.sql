-- 017: диагностика заявки для клиента + вложения jpeg/png/pdf

ALTER TABLE orders ADD COLUMN IF NOT EXISTS diagnostics TEXT;

CREATE TABLE IF NOT EXISTS order_client_files (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    created_by INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_order_client_files_order_id ON order_client_files(order_id);
