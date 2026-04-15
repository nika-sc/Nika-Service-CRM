CREATE TABLE IF NOT EXISTS order_pins (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_order_pins_order_user UNIQUE (order_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_order_pins_user_created
    ON order_pins(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_order_pins_order
    ON order_pins(order_id);
