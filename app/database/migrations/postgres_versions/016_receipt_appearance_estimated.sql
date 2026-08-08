-- 016: квитанция — объединить «Внешний вид» + «Комплектация», добавить
-- «Предварительная стоимость» рядом с предоплатой.
-- Применяется точечно через regexp_replace; кастомные логотипы/реквизиты не трогаются.
-- Бэкап текущих шаблонов перед правкой.

CREATE TABLE IF NOT EXISTS print_templates_backup_20260808 AS
SELECT * FROM print_templates;

-- 1) Основной блок квитанции клиента: две строки → одна, rowspan 3 → 2
UPDATE print_templates
SET html_content = regexp_replace(
        html_content,
        '<tr>\s*<td><strong>Внешний вид</strong></td>\s*<td>##bc1ae9b1-7b8b-4da6-add5-26982865629e##</td>\s*<td rowspan="3">&nbsp;</td>\s*</tr>\s*<tr>\s*<td><strong>Комплектация</strong></td>\s*<td>##dfd7aa33-fd89-462a-bbbc-39c1550415da##</td>\s*</tr>',
        '<tr><td><strong>Внешний вид / комплектация</strong></td><td>##bc1ae9b1-7b8b-4da6-add5-26982865629e##</td><td rowspan="2">&nbsp;</td></tr>',
        'g'
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE template_type = 'customer'
  AND html_content ~ 'Внешний вид</strong>'
  AND html_content ~ 'Комплектация</strong>'
  AND html_content !~ 'Внешний вид / комплектация';

-- 2) Отрывной корешок (без rowspan): две строки → одна
UPDATE print_templates
SET html_content = regexp_replace(
        html_content,
        '<tr>\s*<td><strong>Внешний вид</strong></td>\s*<td>##bc1ae9b1-7b8b-4da6-add5-26982865629e##</td>\s*</tr>\s*<tr>\s*<td><strong>Комплектация</strong></td>\s*<td>##dfd7aa33-fd89-462a-bbbc-39c1550415da##</td>\s*</tr>',
        '<tr><td><strong>Внешний вид / комплектация</strong></td><td>##bc1ae9b1-7b8b-4da6-add5-26982865629e##</td></tr>',
        'g'
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE template_type = 'customer'
  AND html_content ~ 'Внешний вид</strong>'
  AND html_content ~ 'Комплектация</strong>';

-- 3) Если осталась только подпись «Внешний вид» без комплектации — переименовать
UPDATE print_templates
SET html_content = replace(
        html_content,
        '<strong>Внешний вид</strong>',
        '<strong>Внешний вид / комплектация</strong>'
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE template_type IN ('customer', 'master')
  AND html_content LIKE '%<strong>Внешний вид</strong>%'
  AND html_content NOT LIKE '%Внешний вид / комплектация%';

-- 4) Предварительная стоимость перед блоком предоплаты (клиентская квитанция, TOTAL_PAID)
UPDATE print_templates
SET html_content = regexp_replace(
        html_content,
        '(<p><strong>)Предоплата:\s*##TOTAL_PAID##',
        '<p><strong>Предварительная стоимость: ##ESTIMATED_COST## ##CURRENCY##</strong></p>\n\1Предоплата: ##TOTAL_PAID##',
        'g'
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE template_type = 'customer'
  AND html_content ~ 'Предоплата:\s*##TOTAL_PAID##'
  AND html_content !~ 'Предварительная стоимость:\s*##ESTIMATED_COST##';

-- 5) Предварительная стоимость перед ##PREPAYMENT## (шаблон мастера / кастом)
UPDATE print_templates
SET html_content = regexp_replace(
        html_content,
        '(<tr>\s*<td>Предоплата:</td>\s*<td><strong>)##PREPAYMENT##(\s*##CURRENCY##</strong></td>\s*</tr>)',
        E'<tr><td>Предварительная стоимость:</td><td><strong>##ESTIMATED_COST## ##CURRENCY##</strong></td></tr>\\n\\1##PREPAYMENT##\\2',
        'g'
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE template_type IN ('customer', 'master')
  AND html_content LIKE '%##PREPAYMENT##%'
  AND html_content NOT LIKE '%##ESTIMATED_COST##%';
