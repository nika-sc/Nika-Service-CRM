-- Core hot-path indexes for PostgreSQL performance.
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at);
CREATE INDEX IF NOT EXISTS idx_orders_updated_at ON orders (updated_at);
CREATE INDEX IF NOT EXISTS idx_orders_status_id ON orders (status_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_hidden ON orders (hidden);
CREATE INDEX IF NOT EXISTS idx_orders_created_at_visible ON orders (created_at) WHERE (hidden = 0 OR hidden IS NULL);
CREATE INDEX IF NOT EXISTS idx_orders_date_created_at ON orders ((DATE(created_at)));
CREATE INDEX IF NOT EXISTS idx_orders_date_updated_at ON orders ((DATE(updated_at)));

CREATE INDEX IF NOT EXISTS idx_order_status_history_created_at ON order_status_history (created_at);
CREATE INDEX IF NOT EXISTS idx_order_status_history_date_created_at ON order_status_history ((DATE(created_at)));
CREATE INDEX IF NOT EXISTS idx_order_status_history_order_status_time
    ON order_status_history (order_id, new_status_id, created_at);

CREATE INDEX IF NOT EXISTS idx_payments_order_id_date ON payments (order_id, payment_date);
CREATE INDEX IF NOT EXISTS idx_payments_date_payment_date ON payments ((DATE(payment_date)));

CREATE INDEX IF NOT EXISTS idx_cash_txn_date_type_method ON cash_transactions (transaction_date, transaction_type, payment_method);
CREATE INDEX IF NOT EXISTS idx_cash_txn_date_transaction_date ON cash_transactions ((DATE(transaction_date)));
CREATE INDEX IF NOT EXISTS idx_cash_txn_order_id ON cash_transactions (order_id);
CREATE INDEX IF NOT EXISTS idx_cash_txn_shop_sale_id ON cash_transactions (shop_sale_id);

CREATE INDEX IF NOT EXISTS idx_order_parts_order_id_created_at ON order_parts (order_id, created_at);
CREATE INDEX IF NOT EXISTS idx_order_parts_date_created_at ON order_parts ((DATE(created_at)));
CREATE INDEX IF NOT EXISTS idx_order_services_order_id_created_at ON order_services (order_id, created_at);
CREATE INDEX IF NOT EXISTS idx_order_services_date_created_at ON order_services ((DATE(created_at)));

CREATE INDEX IF NOT EXISTS idx_shop_sales_sale_date ON shop_sales (sale_date);
CREATE INDEX IF NOT EXISTS idx_shop_sales_created_at ON shop_sales (created_at);
CREATE INDEX IF NOT EXISTS idx_shop_sales_date_sale_date ON shop_sales ((DATE(sale_date)));
CREATE INDEX IF NOT EXISTS idx_shop_sales_date_created_at ON shop_sales ((DATE(created_at)));

CREATE INDEX IF NOT EXISTS idx_stock_movements_created_at ON stock_movements (created_at);
CREATE INDEX IF NOT EXISTS idx_stock_movements_date_created_at ON stock_movements ((DATE(created_at)));

CREATE INDEX IF NOT EXISTS idx_transaction_categories_type_sort ON transaction_categories (type, sort_order);
CREATE INDEX IF NOT EXISTS idx_customers_created_at ON customers (created_at);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers (phone);

ANALYZE;
