-- 022: diagnostics_templates.is_active как INTEGER 0/1 (users/suppliers), не BOOLEAN.
-- 021 могла создать BOOLEAN; этот ALTER приводит живые БД. Повторно безопасен.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'diagnostics_templates'
          AND column_name = 'is_active'
          AND data_type = 'boolean'
    ) THEN
        ALTER TABLE diagnostics_templates
            ALTER COLUMN is_active DROP DEFAULT;
        ALTER TABLE diagnostics_templates
            ALTER COLUMN is_active TYPE BIGINT
            USING CASE WHEN is_active THEN 1 ELSE 0 END;
        ALTER TABLE diagnostics_templates
            ALTER COLUMN is_active SET DEFAULT 1,
            ALTER COLUMN is_active SET NOT NULL;
    END IF;
END $$;
