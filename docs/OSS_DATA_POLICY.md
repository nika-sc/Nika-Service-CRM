# OSS Data Policy (Reference Only)

## Purpose

This document defines what data can be published in the public repository and what must be removed before any open-source release.

Target public repository: `Nika-Service-CRM`.

## Keep In Public Dataset

Only schema and reference/domain dictionaries are allowed:

- `device_types`
- `device_brands`
- `symptoms`
- `appearance_tags`
- `order_statuses`
- `order_models`
- `services`
- `parts`
- `part_categories`
- `transaction_categories`
- `permissions`
- `role_permissions`
- `system_settings` (neutral values only)
- `general_settings` (sanitized, no real organization data)

Allowed user data:

- Demo users only (`users`) with generated non-production passwords
- Synthetic `managers` and `masters` entries only

## Must Be Deleted Or Fully Reset

Operational, financial, communication, and audit data:

- `customers`, `customer_tokens`
- `devices`
- `orders`
- `order_comments`, `comment_attachments`
- `order_visibility_history`, `order_status_history`
- `order_services`, `order_parts`
- `payments`, `payment_receipts`
- `customer_wallet_transactions`
- `cash_transactions`
- `shop_sales`, `shop_sale_items`
- `purchases`, `purchase_items`
- `stock_movements`
- `warehouse_logs`
- `inventory`, `inventory_items`
- `salary_accruals`, `salary_bonuses`, `salary_fines`, `salary_payments`
- `action_logs`
- `notifications`, `notification_preferences`
- `tasks`, `task_checklists`
- `order_templates`
- `user_role_history`
- `staff_chat_messages`, `staff_chat_attachments`, `staff_chat_reactions`
- FTS data tables (`orders_fts`, `customers_fts`, `parts_fts`)

Filesystem artifacts that must never be published:

- Any `.env` files
- Any SQLite/Postgres dumps/backups
- `uploads/` content (comment/chat attachments)
- Infra/private runbooks with real endpoints or server details

## Sanitization Rules

- Remove real contacts, credentials, and tokens.
- Replace any remaining person-related names with synthetic values.
- Ensure `general_settings.mail_password` and similar secret fields are empty.
- Rebuild/clear search indexes after destructive cleanup.
- Generate a cleanup report for every release candidate.

## Validation Checklist

- Secret scan has no findings in tracked files.
- No `.db`, `.dump`, backups, or uploads are present in public export.
- Public package can start from scratch with migrations.
- Smoke test passes on clean environment.
