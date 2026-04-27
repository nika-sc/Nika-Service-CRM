DO $$
BEGIN
    IF to_regclass('public.orders') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS idx_orders_fts_search
        ON orders
        USING GIN (
            to_tsvector(
                'simple',
                COALESCE(order_id, '') || ' ' ||
                COALESCE(comment, '') || ' ' ||
                COALESCE(symptom_tags, '') || ' ' ||
                COALESCE(appearance, '')
            )
        );
    END IF;

    IF to_regclass('public.customers') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS idx_customers_fts_search
        ON customers
        USING GIN (
            to_tsvector(
                'simple',
                COALESCE(name, '') || ' ' ||
                COALESCE(phone, '') || ' ' ||
                COALESCE(email, '')
            )
        );
    END IF;

    IF to_regclass('public.parts') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS idx_parts_fts_search
        ON parts
        USING GIN (
            to_tsvector(
                'simple',
                COALESCE(name, '') || ' ' ||
                COALESCE(part_number, '') || ' ' ||
                COALESCE(description, '')
            )
        );
    END IF;
END $$;
