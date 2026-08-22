-- 021: шаблоны текста диагностики (по типу / марке / модели устройства)

CREATE TABLE IF NOT EXISTS diagnostics_templates (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    device_type_id BIGINT REFERENCES device_types(id) ON DELETE SET NULL,
    device_brand_id BIGINT REFERENCES device_brands(id) ON DELETE SET NULL,
    model_id BIGINT REFERENCES order_models(id) ON DELETE SET NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_diagnostics_templates_device
    ON diagnostics_templates(device_type_id, device_brand_id, model_id);

CREATE INDEX IF NOT EXISTS idx_diagnostics_templates_sort
    ON diagnostics_templates(sort_order, id);
