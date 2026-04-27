"""
Сервис для работы с настройками и шаблонами печати.
"""
import os
import json
from typing import Dict, Optional
from app.database.connection import get_db_connection
from app.utils.exceptions import DatabaseError
from app.utils.cache import cache_result, clear_cache
from app.services.action_log_service import ActionLogService
import sqlite3
import logging

logger = logging.getLogger(__name__)


class SettingsService:
    """Сервис для работы с настройками."""

    @staticmethod
    def _upsert_system_settings(cursor, items):
        """
        Кросс-БД upsert для system_settings.
        Работает и в SQLite, и в PostgreSQL.
        """
        cursor.executemany(
            """
            INSERT INTO system_settings (key, value, description, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                description = excluded.description,
                updated_at = CURRENT_TIMESTAMP
            """,
            items,
        )
    
    @staticmethod
    @cache_result(timeout=3600, key_prefix='settings')  # Кэш на 1 час
    def get_general_settings() -> Dict:
        """
        Получает общие настройки организации с кэшированием.
        
        Returns:
            Словарь с настройками
        """
        default_settings = {
            'org_name': '',
            'phone': '',
            'address': '',
            'inn': '',
            'ogrn': '',
            'logo_url': '',
            'currency': 'RUB',
            'country': 'Россия',
            'default_warranty_days': 30,
            'timezone_offset': 3,  # По умолчанию Москва (UTC+3)
            'mail_server': '',
            'mail_port': 587,
            'mail_use_tls': True,
            'mail_use_ssl': False,
            'mail_username': '',
            'mail_password': '',
            'mail_default_sender': '',
            'mail_timeout': 3,
            'close_print_mode': 'choice',
            'auto_email_order_accepted': True,
            'auto_email_status_update': True,
            'auto_email_order_ready': True,
            'auto_email_order_closed': True,
            'sms_enabled': False,
            'telegram_enabled': False,
            'signature_name': '',
            'signature_position': '',
            'director_email': '',
            'auto_email_director_order_accepted': True,
            'auto_email_director_order_closed': True,
            'logo_max_width': 320,
            'logo_max_height': 120,
            'print_page_size': 'A4',
            'print_margin_mm': 3,
        }
        
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM general_settings LIMIT 1")
                settings = cursor.fetchone()
                
                if settings:
                    d = {**default_settings, **dict(settings)}
                    # Доп. параметры печати/логотипа храним в system_settings для совместимости
                    # со старыми БД, где в general_settings нет этих колонок.
                    try:
                        cursor.execute(
                            """
                            SELECT key, value
                            FROM system_settings
                            WHERE key IN ('logo_max_width', 'logo_max_height', 'print_page_size', 'print_margin_mm')
                            """
                        )
                        for row in (cursor.fetchall() or []):
                            k = row['key']
                            v = row['value']
                            if k in ('logo_max_width', 'logo_max_height', 'print_margin_mm'):
                                try:
                                    d[k] = int(v)
                                except (TypeError, ValueError):
                                    pass
                            elif k == 'print_page_size' and v:
                                d[k] = str(v).strip() or 'A4'
                    except Exception:
                        pass
                    # Подставляем из .env, если в БД пусто (для отображения в форме)
                    if not d.get('mail_server') and os.environ.get('MAIL_SERVER'):
                        d['mail_server'] = os.environ.get('MAIL_SERVER', '')
                    if (d.get('mail_port') is None or d.get('mail_port') == '') and os.environ.get('MAIL_PORT'):
                        d['mail_port'] = int(os.environ.get('MAIL_PORT', 587))
                    if not d.get('mail_username') and os.environ.get('MAIL_USERNAME'):
                        d['mail_username'] = os.environ.get('MAIL_USERNAME', '')
                    if not d.get('mail_default_sender') and os.environ.get('MAIL_DEFAULT_SENDER'):
                        d['mail_default_sender'] = os.environ.get('MAIL_DEFAULT_SENDER', '')
                    # Нормализуем булевы/числа для шаблона
                    if d.get('mail_use_tls') is not None and not isinstance(d.get('mail_use_tls'), bool):
                        d['mail_use_tls'] = bool(d.get('mail_use_tls'))
                    if d.get('mail_use_ssl') is not None and not isinstance(d.get('mail_use_ssl'), bool):
                        d['mail_use_ssl'] = bool(d.get('mail_use_ssl'))
                    for _bool_key in (
                        'auto_email_order_accepted',
                        'auto_email_status_update',
                        'auto_email_order_ready',
                        'auto_email_order_closed',
                        'auto_email_director_order_accepted',
                        'auto_email_director_order_closed',
                        'sms_enabled',
                        'telegram_enabled',
                    ):
                        if d.get(_bool_key) is not None and not isinstance(d.get(_bool_key), bool):
                            d[_bool_key] = bool(d.get(_bool_key))
                    return d
        except sqlite3.OperationalError as e:
            logger.warning(f"Ошибка при получении настроек: {e}")
        
        return default_settings
    
    @staticmethod
    def save_general_settings(payload: Dict) -> bool:
        """
        Сохраняет общие настройки организации.
        
        Args:
            payload: Словарь с настройками
            
        Returns:
            True если успешно сохранено
            
        Raises:
            DatabaseError: Если произошла ошибка БД
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("PRAGMA table_info(general_settings)")
                cols = [row[1] for row in cursor.fetchall()]
                has_mail_cols = 'mail_server' in cols
                has_automation_cols = 'close_print_mode' in cols
                has_director_cols = 'director_email' in cols

                cursor.execute("SELECT COUNT(*) FROM general_settings")
                count = cursor.fetchone()[0]
                
                def _mail_port():
                    v = payload.get('mail_port')
                    if v is None or v == '':
                        return 587
                    return int(v) if isinstance(v, (int, float)) else int(v or 587)
                def _mail_bool(key, default=True):
                    v = payload.get(key)
                    if v is None:
                        return default
                    if isinstance(v, bool):
                        return v
                    return str(v).lower() in ('1', 'true', 'on', 'yes')
                def _mail_timeout():
                    v = payload.get('mail_timeout')
                    if v is None or v == '':
                        return 3
                    return int(v) if isinstance(v, (int, float)) else int(v or 3)
                mail_password = (payload.get('mail_password') or '').strip()

                if count == 0:
                    if has_mail_cols:
                        cursor.execute('''
                            INSERT INTO general_settings (org_name, phone, address, inn, ogrn, logo_url, currency, country, default_warranty_days, timezone_offset,
                                mail_server, mail_port, mail_use_tls, mail_use_ssl, mail_username, mail_password, mail_default_sender, mail_timeout)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            payload.get('org_name', ''),
                            payload.get('phone', ''),
                            payload.get('address', ''),
                            payload.get('inn', ''),
                            payload.get('ogrn', ''),
                            payload.get('logo_url', ''),
                            payload.get('currency', 'RUB'),
                            payload.get('country', 'Россия'),
                            payload.get('default_warranty_days', 30),
                            payload.get('timezone_offset', 3),
                            payload.get('mail_server', ''),
                            _mail_port(),
                            1 if _mail_bool('mail_use_tls', True) else 0,
                            1 if _mail_bool('mail_use_ssl', False) else 0,
                            payload.get('mail_username', ''),
                            mail_password,
                            payload.get('mail_default_sender', ''),
                            _mail_timeout(),
                        ))
                    else:
                        cursor.execute('''
                            INSERT INTO general_settings (org_name, phone, address, inn, ogrn, logo_url, currency, country, default_warranty_days, timezone_offset)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            payload.get('org_name', ''),
                            payload.get('phone', ''),
                            payload.get('address', ''),
                            payload.get('inn', ''),
                            payload.get('ogrn', ''),
                            payload.get('logo_url', ''),
                            payload.get('currency', 'RUB'),
                            payload.get('country', 'Россия'),
                            payload.get('default_warranty_days', 30),
                            payload.get('timezone_offset', 3),
                        ))

                # При существующей записи всегда обновляем базовые поля (название, адрес, телефон и т.д.)
                if count > 0:
                    if has_mail_cols:
                        if mail_password == '':
                            cursor.execute('SELECT mail_password FROM general_settings WHERE id = 1')
                            row = cursor.fetchone()
                            if row and row[0]:
                                mail_password = row[0]
                        cursor.execute('''
                            UPDATE general_settings 
                            SET org_name = ?, phone = ?, address = ?, inn = ?, ogrn = ?, logo_url = ?, currency = ?, country = ?, default_warranty_days = ?, timezone_offset = ?,
                                mail_server = ?, mail_port = ?, mail_use_tls = ?, mail_use_ssl = ?, mail_username = ?, mail_password = ?, mail_default_sender = ?, mail_timeout = ?
                            WHERE id = 1
                        ''', (
                            payload.get('org_name', ''),
                            payload.get('phone', ''),
                            payload.get('address', ''),
                            payload.get('inn', ''),
                            payload.get('ogrn', ''),
                            payload.get('logo_url', ''),
                            payload.get('currency', 'RUB'),
                            payload.get('country', 'Россия'),
                            payload.get('default_warranty_days', 30),
                            payload.get('timezone_offset', 3),
                            payload.get('mail_server', ''),
                            _mail_port(),
                            1 if _mail_bool('mail_use_tls', True) else 0,
                            1 if _mail_bool('mail_use_ssl', False) else 0,
                            payload.get('mail_username', ''),
                            mail_password,
                            payload.get('mail_default_sender', ''),
                            _mail_timeout(),
                        ))
                    else:
                        cursor.execute('''
                            UPDATE general_settings 
                            SET org_name = ?, phone = ?, address = ?, inn = ?, ogrn = ?, logo_url = ?, currency = ?, country = ?, default_warranty_days = ?, timezone_offset = ?
                            WHERE id = 1
                        ''', (
                            payload.get('org_name', ''),
                            payload.get('phone', ''),
                            payload.get('address', ''),
                            payload.get('inn', ''),
                            payload.get('ogrn', ''),
                            payload.get('logo_url', ''),
                            payload.get('currency', 'RUB'),
                            payload.get('country', 'Россия'),
                            payload.get('default_warranty_days', 30),
                            payload.get('timezone_offset', 3),
                        ))

                if has_automation_cols and count > 0:
                    close_print_mode = str(payload.get('close_print_mode') or 'choice')
                    if close_print_mode not in ('choice', 'sales_receipt', 'work_act', 'both', 'none'):
                        close_print_mode = 'choice'
                    if has_director_cols:
                        cursor.execute(
                            '''
                            UPDATE general_settings
                            SET close_print_mode = ?,
                                auto_email_order_accepted = ?,
                                auto_email_status_update = ?,
                                auto_email_order_ready = ?,
                                auto_email_order_closed = ?,
                                director_email = ?,
                                auto_email_director_order_accepted = ?,
                                auto_email_director_order_closed = ?,
                                sms_enabled = ?,
                                telegram_enabled = ?,
                                signature_name = ?,
                                signature_position = ?
                            WHERE id = 1
                            ''',
                            (
                                close_print_mode,
                                1 if _mail_bool('auto_email_order_accepted', True) else 0,
                                1 if _mail_bool('auto_email_status_update', True) else 0,
                                1 if _mail_bool('auto_email_order_ready', True) else 0,
                                1 if _mail_bool('auto_email_order_closed', True) else 0,
                                payload.get('director_email', ''),
                                1 if _mail_bool('auto_email_director_order_accepted', True) else 0,
                                1 if _mail_bool('auto_email_director_order_closed', True) else 0,
                                1 if _mail_bool('sms_enabled', False) else 0,
                                1 if _mail_bool('telegram_enabled', False) else 0,
                                payload.get('signature_name', ''),
                                payload.get('signature_position', ''),
                            )
                        )
                    else:
                        cursor.execute(
                            '''
                            UPDATE general_settings
                            SET close_print_mode = ?,
                                auto_email_order_accepted = ?,
                                auto_email_status_update = ?,
                                auto_email_order_ready = ?,
                                auto_email_order_closed = ?,
                                sms_enabled = ?,
                                telegram_enabled = ?,
                                signature_name = ?,
                                signature_position = ?
                            WHERE id = 1
                            ''',
                            (
                                close_print_mode,
                                1 if _mail_bool('auto_email_order_accepted', True) else 0,
                                1 if _mail_bool('auto_email_status_update', True) else 0,
                                1 if _mail_bool('auto_email_order_ready', True) else 0,
                                1 if _mail_bool('auto_email_order_closed', True) else 0,
                                1 if _mail_bool('sms_enabled', False) else 0,
                                1 if _mail_bool('telegram_enabled', False) else 0,
                                payload.get('signature_name', ''),
                                payload.get('signature_position', ''),
                            )
                        )

                # Всегда сохраняем параметры печати/логотипа в system_settings:
                # это работает и для старых схем без колонок в general_settings.
                logo_max_width = int(payload.get('logo_max_width') or 320)
                logo_max_height = int(payload.get('logo_max_height') or 120)
                print_page_size = str(payload.get('print_page_size') or 'A4').strip() or 'A4'
                print_margin_mm = int(payload.get('print_margin_mm') or 3)
                SettingsService._upsert_system_settings(
                    cursor,
                    [
                        ('logo_max_width', str(logo_max_width), 'Максимальная ширина логотипа в печати (px)'),
                        ('logo_max_height', str(logo_max_height), 'Максимальная высота логотипа в печати (px)'),
                        ('print_page_size', print_page_size, 'Формат печати'),
                        ('print_margin_mm', str(print_margin_mm), 'Поля печати (мм)'),
                    ],
                )
                
                conn.commit()
                
                # Очищаем кэш настроек
                clear_cache(key_prefix='settings')

                # Логируем изменение настроек
                try:
                    from flask_login import current_user
                    current_user_id = None
                    current_username = None
                    try:
                        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                            current_user_id = current_user.id
                            current_username = current_user.username
                    except Exception:
                        pass

                    ActionLogService.log_action(
                        user_id=current_user_id,
                        username=current_username,
                        action_type='update',
                        entity_type='general_settings',
                        entity_id=1,  # Всегда ID=1 для общих настроек
                        description="Обновлены общие настройки организации",
                        details={
                            'org_name': payload.get('org_name', ''),
                            'currency': payload.get('currency', 'RUB'),
                            'country': payload.get('country', 'Россия'),
                            'default_warranty_days': payload.get('default_warranty_days', 30)
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать изменение общих настроек: {e}")

                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при сохранении настроек: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
    
    @staticmethod
    @cache_result(timeout=3600, key_prefix='vat_settings')
    def get_vat_settings() -> Dict:
        """
        Получает настройки НДС для расчета зарплаты.
        
        Returns:
            Словарь с настройками НДС
        """
        default_settings = {
            'vat_enabled': False,
            'vat_rate': 0.0
        }
        
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM system_settings WHERE key IN ('vat_enabled', 'vat_rate')")
                rows = cursor.fetchall()
                
                if rows:
                    settings = {}
                    for row in rows:
                        key = row['key']
                        value = row['value']
                        if key == 'vat_enabled':
                            settings['vat_enabled'] = bool(int(value))
                        elif key == 'vat_rate':
                            settings['vat_rate'] = float(value)
                    return settings
        except sqlite3.OperationalError as e:
            logger.warning(f"Ошибка при получении настроек НДС: {e}")
        
        return default_settings

    @staticmethod
    @cache_result(timeout=3600, key_prefix='payment_method_settings')
    def get_payment_method_settings() -> Dict:
        """Получает подписи способов оплаты из system_settings."""
        defaults = {
            'cash_label': 'Наличные',
            'transfer_label': 'Перевод',
            'custom_methods': [],
        }
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT key, value
                    FROM system_settings
                    WHERE key IN ('payment_method_cash_label', 'payment_method_transfer_label', 'payment_method_custom_methods')
                    """
                )
                rows = cursor.fetchall() or []
                data = dict(defaults)
                for row in rows:
                    key = row['key']
                    value = (row['value'] or '').strip()
                    if key == 'payment_method_cash_label':
                        data['cash_label'] = value if value else defaults['cash_label']
                    elif key == 'payment_method_transfer_label':
                        data['transfer_label'] = value if value else defaults['transfer_label']
                    elif key == 'payment_method_custom_methods':
                        try:
                            parsed = json.loads(value) if value else []
                            if isinstance(parsed, list):
                                data['custom_methods'] = [str(v).strip() for v in parsed if str(v).strip()]
                        except Exception:
                            data['custom_methods'] = [v.strip() for v in value.split(',') if v.strip()]
                data['card_label'] = ''  # способ «Карта» удалён, для совместимости шаблонов
                return data
        except Exception as e:
            logger.warning(f"Ошибка при получении подписей способов оплаты: {e}")
            return defaults

    @staticmethod
    def save_payment_method_settings(
        cash_label: str,
        transfer_label: str,
        custom_methods: Optional[list] = None,
    ) -> bool:
        """Сохраняет подписи способов оплаты в system_settings (Наличные, Перевод, доп. способы). Способ «Карта» удалён из системы."""
        cash_label = (cash_label or '').strip() or 'Наличные'
        transfer_label = (transfer_label or '').strip() or 'Перевод'
        custom_methods = [str(v).strip() for v in (custom_methods or []) if str(v).strip()]
        custom_methods_json = json.dumps(custom_methods, ensure_ascii=False)
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                SettingsService._upsert_system_settings(
                    cursor,
                    [
                        ('payment_method_cash_label', cash_label, 'Подпись способа оплаты cash'),
                        ('payment_method_transfer_label', transfer_label, 'Подпись способа оплаты transfer'),
                        ('payment_method_custom_methods', custom_methods_json, 'Дополнительные способы оплаты (JSON)'),
                        ('payment_method_card_label', '', 'Удалён'),
                    ],
                )
                conn.commit()
                clear_cache(key_prefix='payment_method_settings')
                return True
        except Exception as e:
            logger.exception(f"Ошибка при сохранении подписей способов оплаты: {e}")
            raise DatabaseError(f"Не удалось сохранить подписи способов оплаты: {e}")
    
    @staticmethod
    def save_vat_settings(vat_enabled: bool, vat_rate: float) -> bool:
        """
        Сохраняет настройки НДС.
        
        Args:
            vat_enabled: Включен ли НДС
            vat_rate: Ставка НДС в процентах
            
        Returns:
            True если успешно сохранено
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Обновляем или создаем настройки
                SettingsService._upsert_system_settings(
                    cursor,
                    [
                        ('vat_enabled', str(int(vat_enabled)), 'Учитывать НДС в расчете зарплаты (1 = да, 0 = нет)'),
                        ('vat_rate', str(vat_rate), 'Ставка НДС в процентах (по умолчанию 0%)'),
                    ],
                )
                
                conn.commit()
                
                # Очищаем кэш
                clear_cache(key_prefix='vat_settings')

                # Логируем изменение настроек НДС
                try:
                    from flask_login import current_user
                    current_user_id = None
                    current_username = None
                    try:
                        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                            current_user_id = current_user.id
                            current_username = current_user.username
                    except Exception:
                        pass

                    ActionLogService.log_action(
                        user_id=current_user_id,
                        username=current_username,
                        action_type='update',
                        entity_type='vat_settings',
                        entity_id=None,
                        description=f"Обновлены настройки НДС: {'включен' if vat_enabled else 'отключен'} ({vat_rate}%)",
                        details={
                            'vat_enabled': vat_enabled,
                            'vat_rate': vat_rate
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать изменение настроек НДС: {e}")

                return True
        except Exception as e:
            logger.exception(f"Ошибка при сохранении настроек НДС: {e}")
            raise DatabaseError(f"Не удалось сохранить настройки НДС: {e}")
    
    @staticmethod
    def _get_print_template_impl(template_type: str) -> Optional[Dict]:
        """Чтение шаблона печати из БД без кэша (для страницы заказа — всегда актуальный из настроек)."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM print_templates WHERE template_type = ?", (template_type,))
                template = cursor.fetchone()
                if template:
                    return dict(template)
                return None
        except sqlite3.OperationalError as e:
            logger.warning(f"Ошибка при получении шаблона печати: {e}")
            return None

    @staticmethod
    @cache_result(timeout=3600, key_prefix='print_template')  # Кэш на 1 час
    def get_print_template(template_type: str = 'customer') -> Optional[Dict]:
        """
        Получает шаблон печати с кэшированием (для страницы настроек).
        
        Args:
            template_type: Тип шаблона ('customer' или 'master')
            
        Returns:
            Словарь с данными шаблона или None
        """
        return SettingsService._get_print_template_impl(template_type)

    @staticmethod
    def get_print_template_fresh(template_type: str = 'customer') -> Optional[Dict]:
        """
        Получает шаблон печати из БД без кэша. Использовать на странице заказа,
        чтобы всегда подхватывать шаблон из настроек «Формы для печати».
        """
        return SettingsService._get_print_template_impl(template_type)
    
    @staticmethod
    def save_print_template(template_type: str, html_content: str, name: Optional[str] = None) -> bool:
        """
        Сохраняет шаблон печати.
        
        Args:
            template_type: Тип шаблона ('customer' или 'master')
            html_content: HTML содержимое шаблона
            name: Название шаблона (опционально)
            
        Returns:
            True если успешно сохранено
            
        Raises:
            DatabaseError: Если произошла ошибка БД
        """
        try:
            # Санитизация HTML контента (если установлен bleach)
            try:
                from bleach import clean
                cleaned_content = clean(
                    html_content,
                    tags=['p', 'table', 'tbody', 'tr', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                          'strong', 'em', 'u', 'ol', 'ul', 'li', 'br', 'img', 'span', 'div', 'var-inline'],
                    attributes={'*': ['style', 'class', 'width', 'height', 'border', 'colspan', 'rowspan',
                                     'data-var', 'data-for', 'src', 'alt', 'data-file-id']},
                    strip=False
                )
            except ImportError:
                # Если bleach не установлен, используем оригинальный контент
                cleaned_content = html_content
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли уже шаблон
                cursor.execute("SELECT id FROM print_templates WHERE template_type = ?", (template_type,))
                existing = cursor.fetchone()
                
                if name is None:
                    default_names = {
                        'customer': 'Квитанция для клиента',
                        'sales_receipt': 'Товарный чек',
                        'work_act': 'Акт выполненных работ',
                        'master': 'Техническая информация для мастера',
                    }
                    name = default_names.get(template_type, f'Шаблон печати ({template_type})')
                
                if existing:
                    cursor.execute('''
                        UPDATE print_templates 
                        SET name = ?, html_content = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE template_type = ?
                    ''', (name, cleaned_content, template_type))
                else:
                    cursor.execute('''
                        INSERT INTO print_templates (name, template_type, html_content)
                        VALUES (?, ?, ?)
                    ''', (name, template_type, cleaned_content))
                
                conn.commit()
                
                # Очищаем кэш шаблонов
                clear_cache(key_prefix='print_template')

                # Логируем изменение шаблона печати
                try:
                    from flask_login import current_user
                    current_user_id = None
                    current_username = None
                    try:
                        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                            current_user_id = current_user.id
                            current_username = current_user.username
                    except Exception:
                        pass

                    action = 'create' if not existing else 'update'
                    ActionLogService.log_action(
                        user_id=current_user_id,
                        username=current_username,
                        action_type=action,
                        entity_type='print_template',
                        entity_id=None,  # Используем template_type как идентификатор
                        description=f"{'Создан' if not existing else 'Обновлен'} шаблон печати: {name} ({template_type})",
                        details={
                            'template_type': template_type,
                            'name': name,
                            'content_length': len(cleaned_content)
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать изменение шаблона печати: {e}")

                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при сохранении шаблона печати: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")

    @staticmethod
    @cache_result(timeout=3600, key_prefix='email_template')
    def get_email_template(template_type: str) -> Optional[Dict]:
        """
        Получает email-шаблон из таблицы print_templates по template_type.
        Хранение сделано по тому же принципу, что и для печатных форм.
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM print_templates WHERE template_type = ?", (template_type,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.OperationalError as e:
            logger.warning(f"Ошибка при получении email шаблона '{template_type}': {e}")
            return None

    @staticmethod
    def save_email_template(template_type: str, html_content: str, name: Optional[str] = None) -> bool:
        """
        Сохраняет email-шаблон в print_templates (template_type = email event key).
        """
        try:
            # Для email оставляем мягкую санитизацию, аналогично печатным шаблонам.
            try:
                from bleach import clean
                cleaned_content = clean(
                    html_content,
                    tags=[
                        'p', 'table', 'tbody', 'tr', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                        'strong', 'em', 'u', 'ol', 'ul', 'li', 'br', 'img', 'span', 'div', 'a', 'var-inline'
                    ],
                    attributes={
                        '*': ['style', 'class', 'width', 'height', 'border', 'colspan', 'rowspan', 'data-var', 'src', 'alt', 'href', 'target', 'rel']
                    },
                    strip=False
                )
            except ImportError:
                cleaned_content = html_content

            default_names = {
                'order_accepted': 'Email: Заказ принят',
                'order_status_update': 'Email: Смена статуса',
                'order_ready': 'Email: Заказ готов',
                'order_closed_thanks': 'Email: Заказ закрыт + Спасибо',
                'director_order_accepted': 'Директор: Заказ принят',
                'director_order_closed_report': 'Директор: Заказ закрыт (отчет)',
            }
            template_name = name or default_names.get(template_type, f'Email шаблон ({template_type})')

            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM print_templates WHERE template_type = ?", (template_type,))
                existing = cursor.fetchone()
                if existing:
                    cursor.execute(
                        '''
                        UPDATE print_templates
                        SET name = ?, html_content = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE template_type = ?
                        ''',
                        (template_name, cleaned_content, template_type)
                    )
                    action = 'update'
                else:
                    cursor.execute(
                        '''
                        INSERT INTO print_templates (name, template_type, html_content)
                        VALUES (?, ?, ?)
                        ''',
                        (template_name, template_type, cleaned_content)
                    )
                    action = 'create'

                conn.commit()
                clear_cache(key_prefix='email_template')

                try:
                    from flask_login import current_user
                    uid = current_user.id if getattr(current_user, 'is_authenticated', False) else None
                    uname = current_user.username if getattr(current_user, 'is_authenticated', False) else None
                    ActionLogService.log_action(
                        user_id=uid,
                        username=uname,
                        action_type=action,
                        entity_type='email_template',
                        entity_id=None,
                        description=f"{'Создан' if action == 'create' else 'Обновлен'} email-шаблон: {template_name} ({template_type})",
                        details={'template_type': template_type, 'name': template_name, 'content_length': len(cleaned_content)},
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать изменение email шаблона: {e}")

                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при сохранении email шаблона: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")

