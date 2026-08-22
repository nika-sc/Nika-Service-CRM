-- 024: журнал писем клиенту по заявке (создание, смена статуса, готов / закрыт).
-- success — INTEGER 0/1, не BOOLEAN.

CREATE TABLE IF NOT EXISTS order_customer_emails (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    customer_id BIGINT REFERENCES customers(id) ON DELETE SET NULL,
    recipient_email TEXT NOT NULL,
    template_type TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    status_name TEXT,
    success BIGINT NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_order_customer_emails_order
    ON order_customer_emails(order_id, created_at DESC);
