-- 019: связи модели с типом и маркой устройства (каскад в заявке)

ALTER TABLE order_models ADD COLUMN IF NOT EXISTS device_type_id BIGINT;
ALTER TABLE order_models ADD COLUMN IF NOT EXISTS device_brand_id BIGINT;

CREATE INDEX IF NOT EXISTS idx_order_models_type_brand
    ON order_models(device_type_id, device_brand_id);

-- Наиболее частая пара тип+марка для уже существующих моделей
UPDATE order_models om
SET device_type_id = sub.dt,
    device_brand_id = sub.db
FROM (
    SELECT ranked.model_id, ranked.dt, ranked.db
    FROM (
        SELECT
            o.model_id,
            d.device_type_id AS dt,
            d.device_brand_id AS db,
            COUNT(*) AS cnt,
            ROW_NUMBER() OVER (
                PARTITION BY o.model_id
                ORDER BY COUNT(*) DESC
            ) AS rn
        FROM orders o
        JOIN devices d ON d.id = o.device_id
        WHERE o.model_id IS NOT NULL
        GROUP BY o.model_id, d.device_type_id, d.device_brand_id
    ) ranked
    WHERE ranked.rn = 1
) sub
WHERE om.id = sub.model_id
  AND om.device_type_id IS NULL
  AND om.device_brand_id IS NULL;
