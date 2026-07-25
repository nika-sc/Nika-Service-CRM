-- Remove SMTP passwords that older /settings requests could copy into action_logs.
-- The active SMTP credential remains only in general_settings.mail_password.
UPDATE action_logs
SET details = (details::jsonb - 'mail_password')::text
WHERE details IS NOT NULL
  AND details::jsonb ? 'mail_password';
