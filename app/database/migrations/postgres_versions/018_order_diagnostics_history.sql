-- 018: история текста диагностики заявки (версии нельзя стереть)

CREATE TABLE IF NOT EXISTS order_diagnostics_history (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    created_by INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_order_diagnostics_history_order_id
    ON order_diagnostics_history(order_id);
