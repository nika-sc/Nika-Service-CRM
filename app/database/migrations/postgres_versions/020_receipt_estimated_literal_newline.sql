-- 020: убрать литерал \n в квитанции после 016 (не-E строка regexp_replace).
-- Если предварительная стоимость пустая, печать больше не показывает «\n ».

UPDATE print_templates
SET html_content = replace(html_content, E'\\n', E'\n'),
    updated_at = CURRENT_TIMESTAMP
WHERE position(E'\\n' in html_content) > 0;
