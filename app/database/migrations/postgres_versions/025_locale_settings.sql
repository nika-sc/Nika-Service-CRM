-- 025: tenant locale — phone prefix and currency symbol as free text.
-- Backfill only empty values so an existing tenant (e.g. KGS / 996) is not overwritten.

ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS phone_prefix TEXT;
ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS currency_symbol TEXT;

UPDATE general_settings
SET phone_prefix = '7'
WHERE phone_prefix IS NULL OR btrim(phone_prefix) = '';

UPDATE general_settings
SET currency_symbol = '₽'
WHERE currency_symbol IS NULL OR btrim(currency_symbol) = '';
