"""
Сервис для работы с уведомлениями.
"""
from typing import Optional, Dict, List, Any
from email.utils import parseaddr
from app.database.connection import get_db_connection
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
import sqlite3
import logging
import json
import smtplib
import time
import socket
from datetime import datetime
from app.utils.datetime_utils import get_moscow_now_str

logger = logging.getLogger(__name__)


def _apply_mail_config_from_settings(app):
    """
    Подставляет настройки почты в app.config: из БД (general_settings), при пустых — из env.
    На сервере можно задать только переменные окружения (MAIL_SERVER, MAIL_PASSWORD и т.д.).
    """
    import os
    from app.services.settings_service import SettingsService
    gs = SettingsService.get_general_settings() or {}
    # Источники: сначала БД, затем env, затем текущий app.config
    def _get(key: str, env_key: str, default):
        val = gs.get(key)
        if val is not None and val != '':
            return val
        return os.environ.get(env_key) or app.config.get(key, default)
    app.config['MAIL_SERVER'] = _get('mail_server', 'MAIL_SERVER', '') or app.config.get('MAIL_SERVER', 'localhost')
    app.config['MAIL_PORT'] = int(_get('mail_port', 'MAIL_PORT', 587) or 587)
    app.config['MAIL_USE_TLS'] = bool(gs.get('mail_use_tls') if gs.get('mail_use_tls') is not None else (os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'))
    app.config['MAIL_USE_SSL'] = bool(gs.get('mail_use_ssl') if gs.get('mail_use_ssl') is not None else (os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'))
    app.config['MAIL_USERNAME'] = _get('mail_username', 'MAIL_USERNAME', '') or app.config.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = _get('mail_password', 'MAIL_PASSWORD', '') or app.config.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = _get('mail_default_sender', 'MAIL_DEFAULT_SENDER', '') or app.config.get('MAIL_DEFAULT_SENDER', '')
    app.config['MAIL_TIMEOUT'] = int(_get('mail_timeout', 'MAIL_TIMEOUT', 3) or 3)


def _resolve_sender_email(app) -> str:
    """
    Возвращает безопасный SMTP envelope sender (только email ASCII).
    Это предотвращает падение smtplib на не-ASCII имени отправителя.
    """
    raw_sender = (app.config.get('MAIL_DEFAULT_SENDER') or '').strip()
    _, parsed_email = parseaddr(raw_sender)
    parsed_email = (parsed_email or '').strip()

    if parsed_email and '@' in parsed_email:
        try:
            parsed_email.encode('ascii')
            return parsed_email
        except UnicodeEncodeError:
            pass

    username = (app.config.get('MAIL_USERNAME') or '').strip()
    if username and '@' in username:
        try:
            username.encode('ascii')
            return username
        except UnicodeEncodeError:
            return ''

    return ''


def _normalize_email_address(raw_value: str) -> str:
    """
    Нормализует email-адрес до ASCII mailbox без display name.
    Возвращает пустую строку, если адрес невалиден для SMTP envelope.
    """
    _, email_addr = parseaddr((raw_value or '').strip())
    email_addr = (email_addr or '').strip()
    if not email_addr or '@' not in email_addr:
        return ''
    try:
        email_addr.encode('ascii')
        return email_addr
    except UnicodeEncodeError:
        return ''


def _send_mail_with_retry(mail_client, message, app, max_attempts: int = 2) -> bool:
    """
    Отправка письма с повторной попыткой при временных SMTP-сбоях.
    """
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        timeout = int(app.config.get('MAIL_TIMEOUT') or 5)
        prev_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout)
            mail_client.send(message)
            return True
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, TimeoutError, OSError) as exc:
            if attempt >= max_attempts:
                raise
            logger.warning(
                f"SMTP временно недоступен ({exc}). Повторная попытка {attempt + 1}/{max_attempts}..."
            )
            try:
                _apply_mail_config_from_settings(app)
            except Exception:
                pass
            time.sleep(0.8)
        finally:
            socket.setdefaulttimeout(prev_timeout)
    return False


class NotificationService:
    """Сервис для работы с уведомлениями."""
    
    @staticmethod
    def create_notification(
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None
    ) -> int:
        """
        Создает уведомление в базе данных.
        
        Args:
            user_id: ID пользователя
            notification_type: Тип уведомления (email/push/in_app)
            title: Заголовок уведомления
            message: Текст уведомления
            entity_type: Тип связанной сущности (order, customer, etc.)
            entity_id: ID связанной сущности
            
        Returns:
            ID созданного уведомления
        """
        if notification_type not in ('email', 'push', 'in_app'):
            raise ValidationError("Неверный тип уведомления")
        
        if not title or not message:
            raise ValidationError("Заголовок и сообщение обязательны")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO notifications 
                    (user_id, type, title, message, entity_type, entity_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, notification_type, title, message, entity_type, entity_id))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при создании уведомления: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
    
    @staticmethod
    def send_email_notification(
        user_id: int,
        subject: str,
        body: str,
        notification_type: str = 'order_status_change',
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None
    ) -> bool:
        """
        Отправляет email уведомление.
        
        Args:
            user_id: ID пользователя
            subject: Тема письма
            body: Тело письма (HTML)
            entity_type: Тип связанной сущности
            entity_id: ID связанной сущности
            
        Returns:
            True если успешно отправлено
        """
        try:
            from flask import current_app
            from app.services.user_service import UserService
            
            # Проверяем доступность Flask-Mail
            try:
                from flask_mail import Message
                from app import mail, MAIL_AVAILABLE
                if not MAIL_AVAILABLE or mail is None:
                    logger.warning("Flask-Mail не установлен. Email уведомление не может быть отправлено.")
                    return False
            except ImportError:
                logger.warning("Flask-Mail не установлен. Email уведомление не может быть отправлено.")
                return False
            
            # Проверяем настройки пользователя
            if not NotificationService.is_notification_enabled(user_id, 'email', notification_type):
                logger.info(f"Email уведомления отключены для пользователя {user_id}")
                return False
            
            # Получаем email пользователя
            user = UserService.get_user_by_id(user_id)
            if not user:
                logger.warning(f"Пользователь {user_id} не найден для отправки email")
                return False
            
            email = _normalize_email_address(user.get('username') or '')
            if not email:
                logger.warning(f"Неверный email для пользователя {user_id}: {user.get('username')}")
                return False
            
            # Отправляем email через Flask-Mail
            with current_app.app_context():
                app = current_app._get_current_object()
                _apply_mail_config_from_settings(app)
                sender = _resolve_sender_email(app)
                if sender:
                    msg = Message(subject=subject, sender=sender, recipients=[email], html=body)
                    _send_mail_with_retry(mail, msg, app)
            
            # Создаем запись в БД
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='email',
                title=subject,
                message=body,
                entity_type=entity_type,
                entity_id=entity_id
            )
            
            logger.info(f"Email уведомление отправлено пользователю {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке email уведомления: {e}", exc_info=True)
            return False
    
    @staticmethod
    def send_push_notification(
        user_id: int,
        title: str,
        message: str,
        notification_type: str = 'order_status_change',
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None
    ) -> bool:
        """
        Отправляет push уведомление через WebSocket.
        
        Args:
            user_id: ID пользователя
            title: Заголовок уведомления
            message: Текст уведомления
            entity_type: Тип связанной сущности
            entity_id: ID связанной сущности
            
        Returns:
            True если успешно отправлено
        """
        try:
            from flask import current_app
            try:
                from flask_socketio import SocketIO
            except ImportError:
                logger.debug("flask_socketio не установлен — push-уведомления пропущены")
                return False

            # Проверяем настройки пользователя
            if not NotificationService.is_notification_enabled(user_id, 'push', notification_type):
                logger.info(f"Push уведомления отключены для пользователя {user_id}")
                return False

            # Отправляем через SocketIO
            with current_app.app_context():
                socketio = current_app.extensions.get('socketio')
                if socketio:
                    notification_data = {
                        'title': title,
                        'message': message,
                        'entity_type': entity_type,
                        'entity_id': entity_id,
                        'created_at': get_moscow_now_str()
                    }
                    socketio.emit('notification', notification_data, room=f'user_{user_id}')
            
            # Создаем запись в БД
            notification_id = NotificationService.create_notification(
                user_id=user_id,
                notification_type='push',
                title=title,
                message=message,
                entity_type=entity_type,
                entity_id=entity_id
            )
            
            logger.info(f"Push уведомление отправлено пользователю {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке push уведомления: {e}", exc_info=True)
            return False

    @staticmethod
    def notify_low_stock(part_id: int) -> bool:
        """
        Рассылает внутренние/почтовые уведомления о низком остатке товара.
        """
        try:
            from app.services.warehouse_service import WarehouseService
            from app.services.user_service import UserService

            part = WarehouseService.get_part_by_id(part_id)
            if not part:
                return False

            stock = int(part.get('stock_quantity') or 0)
            minimum = int(part.get('min_quantity') or 0)
            if minimum <= 0 or stock > minimum:
                return False

            # Простейшая защита от спама: не дублируем алерты по одному товару чаще раза в час.
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        '''
                        SELECT COUNT(*)
                        FROM notifications
                        WHERE entity_type = 'part'
                          AND entity_id = ?
                          AND title LIKE 'Низкий остаток%'
                          AND datetime(created_at) >= datetime('now', '-1 hour')
                        ''',
                        (part_id,)
                    )
                    recent = int((cur.fetchone() or [0])[0] or 0)
                    if recent > 0:
                        return False
            except Exception:
                pass

            users = UserService.get_all_users(include_inactive=False)
            if not users:
                return False

            part_name = str(part.get('name') or f"Товар #{part_id}")
            part_number = str(part.get('part_number') or '—')
            title = f"Низкий остаток: {part_name}"
            message = (
                f"Остаток товара «{part_name}» ({part_number}) ниже минимума: "
                f"{stock} шт. при минимуме {minimum} шт."
            )
            email_body = f"""
                <h3>Низкий остаток на складе</h3>
                <p><strong>Товар:</strong> {part_name}</p>
                <p><strong>Артикул:</strong> {part_number}</p>
                <p><strong>Остаток:</strong> {stock} шт.</p>
                <p><strong>Минимум:</strong> {minimum} шт.</p>
            """

            sent_any = False
            for user in users:
                user_id = int(user.get('id'))
                # Получатели low_stock: только сотрудники, у которых есть право управления складом.
                if not UserService.check_permission(user_id, 'manage_warehouse'):
                    continue
                if not NotificationService.is_notification_enabled(user_id, 'in_app', 'low_stock'):
                    continue

                NotificationService.send_in_app_notification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    entity_type='part',
                    entity_id=part_id
                )
                sent_any = True

                if NotificationService.is_notification_enabled(user_id, 'push', 'low_stock'):
                    NotificationService.send_push_notification(
                        user_id=user_id,
                        title=title,
                        message=message,
                        notification_type='low_stock',
                        entity_type='part',
                        entity_id=part_id
                    )
                if NotificationService.is_notification_enabled(user_id, 'email', 'low_stock'):
                    raw_login = str(user.get('username') or '')
                    if _normalize_email_address(raw_login):
                        NotificationService.send_email_notification(
                            user_id=user_id,
                            subject=title,
                            body=email_body,
                            notification_type='low_stock',
                            entity_type='part',
                            entity_id=part_id
                        )

            return sent_any
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомлений low_stock по товару {part_id}: {e}", exc_info=True)
            return False
    
    @staticmethod
    def send_in_app_notification(
        user_id: int,
        title: str,
        message: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None
    ) -> int:
        """
        Создает in-app уведомление.
        
        Args:
            user_id: ID пользователя
            title: Заголовок уведомления
            message: Текст уведомления
            entity_type: Тип связанной сущности
            entity_id: ID связанной сущности
            
        Returns:
            ID созданного уведомления
        """
        return NotificationService.create_notification(
            user_id=user_id,
            notification_type='in_app',
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id
        )

    @staticmethod
    def _render_html_template(html_content: str, values: Dict[str, Any]) -> str:
        """Простая подстановка переменных в форматах ##TAG## и <var-inline data-var=\"TAG\">...</var-inline>."""
        if not html_content:
            return ''

        rendered = str(html_content)

        # Подстановка var-inline
        try:
            import re
            def _replace_var_inline(m):
                var_name = (m.group(1) or '').strip()
                return str(values.get(var_name, values.get(var_name.upper(), '')))

            patterns = [
                r'<var-inline[^>]*\s+data-var\s*=\s*"([^"]+)"[^>]*>.*?</var-inline>',
                r"<var-inline[^>]*\s+data-var\s*=\s*'([^']+)'[^>]*>.*?</var-inline>",
            ]
            for pattern in patterns:
                prev = None
                while prev != rendered:
                    prev = rendered
                    rendered = re.sub(pattern, _replace_var_inline, rendered, flags=re.IGNORECASE | re.DOTALL)

            # Подстановка ##TAG##
            def _replace_hash(m):
                var_name = (m.group(1) or '').strip()
                return str(values.get(var_name, values.get(var_name.upper(), m.group(0))))

            rendered = re.sub(r'##([A-Z0-9_.-]+)##', _replace_hash, rendered, flags=re.IGNORECASE)
        except Exception:
            # Если regex по какой-то причине не отработал, просто возвращаем исходный html.
            return rendered

        return rendered

    @staticmethod
    def _get_default_email_template(template_type: str) -> str:
        defaults = {
            'order_accepted': """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #333;">Заказ принят</h2>
    <p>Здравствуйте, ##CLIENT_NAME##!</p>
    <p>Ваша заявка <strong>##ORDER_NUMBER##</strong> успешно принята в работу. Мы свяжемся с вами при необходимости и сообщим о готовности.</p>
    <p><strong>Данные для входа в личный кабинет:</strong><br>
    Логин: <strong>##PORTAL_LOGIN##</strong><br>
    Временный пароль: <strong>##PORTAL_TEMP_PASSWORD##</strong></p>
    <p>Рекомендуем сменить пароль после первого входа. В кабинете вы можете отслеживать статус заявки.</p>
    <p>Спасибо за обращение! С уважением,<br>сервисный центр «Ника».</p>
</div>
            """,
            'order_status_update': """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #333;">Обновление по заявке ##ORDER_NUMBER##</h2>
    <p>Здравствуйте, ##CLIENT_NAME##!</p>
    <p>Статус вашей заявки изменён: <strong>##STATUS_NAME##</strong>.</p>
    <p>Описание неисправности: ##DIAGNOSTIC##</p>
    <p>Добавлено фото в заявке: ##PHOTO_COUNT##</p>
    <p>Дата обновления: ##UPDATED_AT##</p>
    <p>Подробности вы можете посмотреть в личном кабинете. С уважением,<br>сервисный центр «Ника».</p>
</div>
            """,
            'order_ready': """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #333;">Заказ готов к выдаче</h2>
    <p>Здравствуйте, ##CLIENT_NAME##!</p>
    <p>Ваша заявка <strong>##ORDER_NUMBER##</strong> готова. Можете приезжать за устройством.</p>
    <p><strong>Напоминание по заявке:</strong><br>
    Устройство: ##ORDER_DEVICE_TYPE## ##ORDER_DEVICE_BRAND## ##ORDER_MODEL##<br>
    Неисправность: ##DIAGNOSTIC##<br>
    Выполненные работы: ##ORDER_WORK_DONE##</p>
    <p>Если у вас несколько заявок — это данные именно по заявке ##ORDER_NUMBER##.</p>
    <p>Ждём вас. С уважением,<br>сервисный центр «Ника».</p>
</div>
            """,
            'order_closed_thanks': """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #333;">Спасибо за обращение!</h2>
    <p>Здравствуйте, ##CLIENT_NAME##!</p>
    <p>Заявка <strong>##ORDER_NUMBER##</strong> закрыта. Надеемся, вы остались довольны результатом.</p>
    <p>Нам очень важна обратная связь. Если у вас найдётся минута — оставьте, пожалуйста, отзыв. Это поможет другим клиентам и нам становиться лучше.</p>
    <p><strong>Оставить отзыв:</strong><br>
    <a href="https://yandex.ru/maps/org/nika_servis/1708766332/">Яндекс.Карты — Ника, сервисный центр</a><br>
    <a href="https://2gis.ru/sochi/firm/4222652931807956">2ГИС — Ника, сервисный центр</a></p>
    <p>Напоминание: по заявке ##ORDER_NUMBER## было отремонтировано устройство ##ORDER_DEVICE_TYPE## ##ORDER_DEVICE_BRAND## ##ORDER_MODEL## (##DIAGNOSTIC##).</p>
    <p>Будем рады видеть вас снова. С уважением,<br>сервисный центр «Ника».</p>
</div>
            """,
            'director_order_accepted': """
<div style="font-family: Arial, sans-serif; max-width: 600px;">
<h2>Новая заявка принята</h2>
<table cellpadding="8" cellspacing="0" border="1" style="border-collapse: collapse; width: 100%; margin: 1em 0;">
<tr><th colspan="2" style="background: #f0f0f0;">Заявка ##ORDER_NUMBER## (##ORDER_UUID##)</th></tr>
<tr><td><strong>Дата создания</strong></td><td>##CREATED_AT##</td></tr>
<tr><td><strong>Статус</strong></td><td>##STATUS_NAME##</td></tr>
<tr><td><strong>Клиент</strong></td><td>##CLIENT_NAME##</td></tr>
<tr><td><strong>Телефон</strong></td><td>##CLIENT_PHONE##</td></tr>
<tr><td><strong>Email</strong></td><td>##CLIENT_EMAIL##</td></tr>
<tr><td><strong>Устройство</strong></td><td>##DEVICE_TYPE## ##DEVICE_BRAND## ##MODEL##</td></tr>
<tr><td><strong>Симптомы / описание</strong></td><td>##SYMPTOM_TAGS## ##COMMENT##</td></tr>
<tr><td><strong>Внешний вид</strong></td><td>##APPEARANCE##</td></tr>
<tr><td><strong>Менеджер</strong></td><td>##MANAGER_NAME##</td></tr>
<tr><td><strong>Мастер</strong></td><td>##MASTER_NAME##</td></tr>
<tr><td><strong>Предоплата</strong></td><td>##PREPAYMENT##</td></tr>
<tr><td><strong>Обновлено</strong></td><td>##UPDATED_AT##</td></tr>
</table>
</div>
            """,
            'director_order_closed_report': """
<div style="font-family: Arial, sans-serif; max-width: 600px;">
<h2>Заявка закрыта: финансовый отчёт</h2>
<table cellpadding="8" cellspacing="0" border="1" style="border-collapse: collapse; width: 100%; margin: 1em 0;">
<tr><th colspan="2" style="background: #f0f0f0;">Заявка ##ORDER_NUMBER## (##ORDER_UUID##)</th></tr>
<tr><td><strong>Клиент</strong></td><td>##CLIENT_NAME## (##CLIENT_PHONE##)</td></tr>
<tr><td><strong>Устройство</strong></td><td>##DEVICE_TYPE## ##DEVICE_BRAND## ##MODEL##</td></tr>
<tr><td><strong>Статус</strong></td><td>##STATUS_NAME##</td></tr>
<tr><td><strong>Менеджер</strong></td><td>##MANAGER_NAME##</td></tr>
<tr><td><strong>Мастер</strong></td><td>##MASTER_NAME##</td></tr>
</table>
<h3>Касса и выручка</h3>
<table cellpadding="8" cellspacing="0" border="1" style="border-collapse: collapse; width: 100%; margin: 1em 0;">
<tr><td><strong>Сумма заявки (итого)</strong></td><td>##ORDER_TOTAL##</td></tr>
<tr><td><strong>Поступило (оплачено)</strong></td><td>##TOTAL_PAID##</td></tr>
</table>
<h3>Расходы и прибыль</h3>
<table cellpadding="8" cellspacing="0" border="1" style="border-collapse: collapse; width: 100%; margin: 1em 0;">
<tr><td><strong>Себестоимость запчастей</strong></td><td>##COST_PARTS##</td></tr>
<tr><td><strong>Себестоимость услуг</strong></td><td>##COST_SERVICES##</td></tr>
<tr><td><strong>Общая себестоимость</strong></td><td>##TOTAL_COST##</td></tr>
<tr><td><strong>Списано со склада (запчасти)</strong></td><td>##WAREHOUSE_WRITEOFF##</td></tr>
<tr><td><strong>Начисленная зарплата</strong></td><td>##SALARY_AMOUNT##</td></tr>
<tr><td><strong>Прибыль</strong></td><td>##PROFIT_AMOUNT##</td></tr>
</table>
<p><strong>Обновлено:</strong> ##UPDATED_AT##</p>
</div>
            """,
        }
        return defaults.get(template_type, "<p>##ORDER_NUMBER##</p>")

    @staticmethod
    def _format_money(value: float) -> str:
        try:
            return f"{float(value):,.2f} ₽".replace(",", " ")
        except Exception:
            return "0.00 ₽"

    @staticmethod
    def _get_order_finance_summary(order_id: int) -> Dict[str, float]:
        """
        Собирает полную финансовую сводку по заявке для директорского письма.
        """
        total_paid = 0.0
        salary_amount = 0.0
        profit_amount = 0.0
        cost_parts = 0.0
        cost_services = 0.0
        total_cost = 0.0
        order_total = 0.0
        try:
            from app.services.salary_service import SalaryService
            from app.services.order_service import OrderService
            profit_data = SalaryService.calculate_order_profit(order_id)
            total_paid = float(profit_data.get('total_payments_cents', 0) or 0) / 100.0
            profit_amount = float(profit_data.get('profit_cents', 0) or 0) / 100.0
            cost_parts = float(profit_data.get('total_parts_cost_cents', 0) or 0) / 100.0
            cost_services = float(profit_data.get('total_services_cost_cents', 0) or 0) / 100.0
            total_cost = float(profit_data.get('total_cost_cents', 0) or 0) / 100.0
            if total_cost <= 0 and (cost_parts > 0 or cost_services > 0):
                total_cost = cost_parts + cost_services

            accruals = SalaryService.get_accruals_for_order(order_id)
            salary_amount = sum(float(a.get('amount_cents', 0) or 0) for a in accruals) / 100.0

            totals = OrderService.get_order_totals(order_id)
            order_total = float(totals.get('total', 0) or 0)
        except Exception as e:
            logger.debug(f"Не удалось собрать финсводку по заявке {order_id}: {e}")
        return {
            'total_paid': total_paid,
            'salary_amount': salary_amount,
            'profit_amount': profit_amount,
            'cost_parts': cost_parts,
            'cost_services': cost_services,
            'total_cost': total_cost,
            'order_total': order_total,
        }

    @staticmethod
    def send_customer_order_email(
        order_id: int,
        template_type: str,
        customer_id: Optional[int] = None,
        status_name: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
        override_recipient: Optional[str] = None,
    ) -> bool:
        """
        Отправка email клиенту по шаблону события заявки.
        override_recipient: если задан, письмо уйдёт на этот адрес вместо email клиента (для тестов).
        """
        try:
            from app.services.settings_service import SettingsService
            from app.services.order_service import OrderService
            from app.services.customer_service import CustomerService
            from app.services.customer_portal_service import CustomerPortalService
            from app.utils.datetime_utils import get_moscow_now_str

            order = OrderService.get_order(order_id)
            if not order:
                return False

            cid = customer_id or getattr(order, 'customer_id', None)
            if not cid:
                return False
            customer = CustomerService.get_customer(cid)
            if not customer:
                return False
            recipient_email = _normalize_email_address(override_recipient or getattr(customer, 'email', '') or '')
            if not recipient_email:
                return False

            settings = SettingsService.get_general_settings() or {}
            # При тестовой отправке (override_recipient) игнорируем feature_flags
            if not override_recipient:
                feature_flags = {
                    'order_accepted': bool(settings.get('auto_email_order_accepted', True)),
                    'order_status_update': bool(settings.get('auto_email_status_update', True)),
                    'order_ready': bool(settings.get('auto_email_order_ready', True)),
                    'order_closed_thanks': bool(settings.get('auto_email_order_closed', True)),
                }
                if feature_flags.get(template_type) is False:
                    return False
            tpl = SettingsService.get_email_template(template_type)
            html_content = (tpl or {}).get('html_content') if tpl else None
            if not html_content:
                html_content = NotificationService._get_default_email_template(template_type)

            portal_login = getattr(customer, 'phone', '') or ''
            portal_temp_password = ''
            if template_type == 'order_accepted':
                has_portal = bool(getattr(customer, 'portal_enabled', 0))
                has_password = bool(getattr(customer, 'portal_password_hash', None))
                if not has_portal or not has_password:
                    generated = CustomerPortalService.generate_and_set_portal_password(cid)
                    if generated:
                        portal_temp_password = generated

            # photo count из вложений комментариев по заявке
            photo_count = 0
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        '''
                        SELECT COUNT(*)
                        FROM comment_attachments a
                        INNER JOIN order_comments c ON c.id = a.comment_id
                        WHERE c.order_id = ?
                        ''',
                        (order_id,)
                    )
                    row = cur.fetchone()
                    photo_count = int(row[0]) if row and row[0] is not None else 0
            except Exception:
                photo_count = 0

            # Устройство и модель для писем «Заказ готов» / «Заказ закрыт»
            order_device_type = str(getattr(order, 'device_type_name', '') or '')
            order_device_brand = str(getattr(order, 'device_brand_name', '') or '')
            order_model = str(getattr(order, 'model', '') or '')
            order_work_done = ''
            try:
                services = OrderService.get_order_services(order_id)
                if services:
                    names = []
                    for s in services:
                        name = (s.get('service_name') or s.get('name') or '').strip()
                        if name:
                            names.append(name)
                    order_work_done = ', '.join(names) if names else ''
            except Exception:
                order_work_done = ''

            # Дата создания заявки (для писем)
            order_created_at = ''
            try:
                ct = getattr(order, 'created_at', None)
                if ct:
                    from datetime import datetime
                    if isinstance(ct, datetime):
                        order_created_at = ct.strftime('%d.%m.%Y %H:%M:%S')
                    else:
                        order_created_at = str(ct)[:19].replace('T', ' ')
            except Exception:
                order_created_at = ''

            values = {
                'ORDER_NUMBER': f"#{getattr(order, 'id', order_id)}",
                'ORDER_ID': str(getattr(order, 'id', order_id)),
                'ORDER_UUID': str(getattr(order, 'order_id', '') or ''),
                'CLIENT_NAME': str(getattr(customer, 'name', '') or ''),
                'CLIENT_PHONE': str(getattr(customer, 'phone', '') or ''),
                'CLIENT_EMAIL': str(getattr(customer, 'email', '') or ''),
                'STATUS_NAME': str(status_name or ''),
                'DIAGNOSTIC': str(getattr(order, 'symptom_tags', '') or ''),
                'PHOTO_COUNT': str(photo_count),
                'UPDATED_AT': get_moscow_now_str('%d.%m.%Y %H:%M:%S'),
                'PORTAL_LOGIN': portal_login,
                'PORTAL_TEMP_PASSWORD': portal_temp_password,
                'ORDER_DEVICE_TYPE': order_device_type,
                'ORDER_DEVICE_BRAND': order_device_brand,
                'ORDER_MODEL': order_model,
                'ORDER_WORK_DONE': order_work_done,
                'ORDER_CREATED_AT': order_created_at,
                'SERIAL_NUMBER': str(getattr(order, 'serial_number', '') or ''),
                'MANAGER_NAME': str(getattr(order, 'manager_name', '') or ''),
                'MASTER_NAME': str(getattr(order, 'master_name', '') or ''),
                'ORDER_COMMENT': str(getattr(order, 'comment', '') or ''),
                'ORDER_APPEARANCE': str(getattr(order, 'appearance', '') or ''),
            }
            if extra_context:
                values.update({str(k): v for k, v in extra_context.items()})

            html_body = NotificationService._render_html_template(html_content, values)

            subject_map = {
                'order_accepted': f"Заказ принят: #{getattr(order, 'id', order_id)}",
                'order_status_update': f"Изменение статуса: #{getattr(order, 'id', order_id)}",
                'order_ready': f"Заказ готов: #{getattr(order, 'id', order_id)}",
                'order_closed_thanks': f"Заказ закрыт: #{getattr(order, 'id', order_id)}",
            }
            subject = subject_map.get(template_type, f"Обновление заявки #{getattr(order, 'id', order_id)}")

            from flask import current_app
            try:
                from flask_mail import Message
                from app import mail, MAIL_AVAILABLE
                if not MAIL_AVAILABLE or mail is None:
                    return False
            except ImportError:
                return False

            with current_app.app_context():
                app = current_app._get_current_object()
                _apply_mail_config_from_settings(app)
                sender = _resolve_sender_email(app)
                if not sender or '@' not in sender:
                    logger.warning("Email клиенту: не задан корректный отправитель.")
                    return False
                msg = Message(
                    subject=subject,
                    sender=sender,
                    recipients=[recipient_email],
                    html=html_body
                )
                _send_mail_with_retry(mail, msg, app)
            return True
        except Exception as e:
            if isinstance(e, (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, TimeoutError, OSError)):
                logger.warning(
                    f"Не удалось отправить клиентский email ({template_type}) для заявки {order_id}: {e}"
                )
            else:
                logger.warning(
                    f"Не удалось отправить клиентский email ({template_type}) для заявки {order_id}: {e}",
                    exc_info=True
                )
            return False

    @staticmethod
    def send_director_order_email(
        order_id: int,
        template_type: str,
        status_name: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Отправка email директору по событиям заявки.
        """
        try:
            from app.services.settings_service import SettingsService
            from app.services.order_service import OrderService
            from app.services.customer_service import CustomerService
            from app.utils.datetime_utils import get_moscow_now_str

            settings = SettingsService.get_general_settings() or {}
            recipient_email = _normalize_email_address(settings.get('director_email', '') or '')
            if not recipient_email:
                logger.info(
                    f"Письмо директору ({template_type}) пропущено: не задан/невалиден director_email."
                )
                return False

            feature_flags = {
                'director_order_accepted': bool(settings.get('auto_email_director_order_accepted', True)),
                'director_order_closed_report': bool(settings.get('auto_email_director_order_closed', True)),
            }
            if feature_flags.get(template_type) is False:
                logger.info(f"Письмо директору ({template_type}) пропущено: авто-отправка отключена.")
                return False

            order = OrderService.get_order(order_id)
            if not order:
                logger.warning(f"Письмо директору ({template_type}) пропущено: заявка {order_id} не найдена.")
                return False
            customer = CustomerService.get_customer(getattr(order, 'customer_id', None))

            tpl = SettingsService.get_email_template(template_type)
            html_content = (tpl or {}).get('html_content') if tpl else None
            if not html_content:
                html_content = NotificationService._get_default_email_template(template_type)

            finance = NotificationService._get_order_finance_summary(order_id)

            def _fmt_dt(val):
                if val is None:
                    return ''
                if hasattr(val, 'strftime'):
                    return val.strftime('%d.%m.%Y %H:%M:%S')
                s = str(val or '')
                if len(s) >= 19:
                    return s[:10].replace('-', '.')[8:10] + '.' + s[5:7] + '.' + s[:4] + ' ' + s[11:19]
                return s

            values = {
                'ORDER_NUMBER': f"#{getattr(order, 'id', order_id)}",
                'ORDER_ID': str(getattr(order, 'id', order_id)),
                'ORDER_UUID': str(getattr(order, 'order_id', '') or ''),
                'CLIENT_NAME': str(getattr(customer, 'name', '') or '') if customer else '',
                'CLIENT_PHONE': str(getattr(customer, 'phone', '') or '') if customer else '',
                'CLIENT_EMAIL': str(getattr(customer, 'email', '') or '') if customer else '',
                'CLIENT_PHONE1': str(getattr(customer, 'phone', '') or '') if customer else '',
                'STATUS_NAME': str(status_name or getattr(order, 'status_name', '') or ''),
                'UPDATED_AT': get_moscow_now_str('%d.%m.%Y %H:%M:%S'),
                'CREATED_AT': _fmt_dt(getattr(order, 'created_at', None)),
                'DATE_TODAY': get_moscow_now_str('%d.%m.%Y'),
                'TIME_NOW': get_moscow_now_str('%H:%M:%S'),
                'MODEL': str(getattr(order, 'model', '') or ''),
                'DEVICE_TYPE': str(getattr(order, 'device_type_name', '') or ''),
                'DEVICE_BRAND': str(getattr(order, 'device_brand_name', '') or ''),
                'ORDER_DEVICE_TYPE': str(getattr(order, 'device_type_name', '') or ''),
                'ORDER_DEVICE_BRAND': str(getattr(order, 'device_brand_name', '') or ''),
                'ORDER_MODEL': str(getattr(order, 'model', '') or ''),
                'SYMPTOM_TAGS': str(getattr(order, 'symptom_tags', '') or ''),
                'APPEARANCE': str(getattr(order, 'appearance', '') or ''),
                'COMMENT': str(getattr(order, 'comment', '') or ''),
                'MASTER_NAME': str(getattr(order, 'master_name', '') or ''),
                'MANAGER_NAME': str(getattr(order, 'manager_name', '') or ''),
                'ENGINEER_NAME': str(getattr(order, 'master_name', '') or ''),
                'EMPLOYEE_NAME': str(getattr(order, 'master_name', '') or getattr(order, 'manager_name', '') or ''),
                'PREPAYMENT': NotificationService._format_money(float(getattr(order, 'prepayment', 0) or 0)),
                'PREPAYMENT_WORDS': '',
                'TOTAL_PAID': NotificationService._format_money(finance['total_paid']),
                'SALARY_AMOUNT': NotificationService._format_money(finance['salary_amount']),
                'PROFIT_AMOUNT': NotificationService._format_money(finance['profit_amount']),
                'ORDER_TOTAL': NotificationService._format_money(finance.get('order_total', 0)),
                'COST_PARTS': NotificationService._format_money(finance.get('cost_parts', 0)),
                'COST_SERVICES': NotificationService._format_money(finance.get('cost_services', 0)),
                'TOTAL_COST': NotificationService._format_money(finance.get('total_cost', 0)),
                'WAREHOUSE_WRITEOFF': NotificationService._format_money(finance.get('cost_parts', 0)),
            }
            if extra_context:
                values.update({str(k): v for k, v in extra_context.items()})

            html_body = NotificationService._render_html_template(html_content, values)
            subject_map = {
                'director_order_accepted': f"Директор: заявка принята #{getattr(order, 'id', order_id)}",
                'director_order_closed_report': f"Директор: заявка закрыта #{getattr(order, 'id', order_id)}",
            }
            subject = subject_map.get(template_type, f"Директор: событие по заявке #{getattr(order, 'id', order_id)}")

            from flask import current_app
            try:
                from flask_mail import Message
                from app import mail, MAIL_AVAILABLE
                if not MAIL_AVAILABLE or mail is None:
                    logger.warning("Письмо директору пропущено: Flask-Mail недоступен.")
                    return False
            except ImportError:
                logger.warning("Письмо директору пропущено: flask_mail не установлен.")
                return False

            with current_app.app_context():
                app = current_app._get_current_object()
                _apply_mail_config_from_settings(app)
                sender = _resolve_sender_email(app)
                if not sender or '@' not in sender:
                    logger.warning("Email директору: не задан корректный отправитель.")
                    return False
                msg = Message(
                    subject=subject,
                    sender=sender,
                    recipients=[recipient_email],
                    html=html_body
                )
                _send_mail_with_retry(mail, msg, app)
            return True
        except Exception as e:
            logger.warning(f"Не удалось отправить письмо директору ({template_type}) по заявке {order_id}: {e}")
            return False

    @staticmethod
    def send_director_test_email(recipient_email: str):
        """
        Отправляет тестовое письмо директору из настроек /settings.
        Returns:
            tuple: (success: bool, error_message: Optional[str]) — при успехе (True, None), при ошибке (False, "текст ошибки").
        """
        try:
            recipient = _normalize_email_address(recipient_email or '')
            if not recipient:
                logger.warning("Тест директору пропущен: невалидный email получателя.")
                return False, "Невалидный email получателя."

            from flask import current_app
            try:
                from flask_mail import Message
                from app import mail, MAIL_AVAILABLE
                if not MAIL_AVAILABLE or mail is None:
                    logger.warning("Тест директору пропущен: Flask-Mail недоступен.")
                    return False, "Flask-Mail не установлен или недоступен."
            except ImportError:
                logger.warning("Тест директору пропущен: flask_mail не установлен.")
                return False, "Модуль flask_mail не установлен. Установите: pip install flask-mail"

            with current_app.app_context():
                app = current_app._get_current_object()
                _apply_mail_config_from_settings(app)
                if not (app.config.get('MAIL_SERVER') or app.config.get('MAIL_SERVER') == 'localhost'):
                    return False, "Не задан SMTP-сервер (MAIL_SERVER в настройках или переменной окружения)."
                sender = _resolve_sender_email(app)
                if not sender or '@' not in sender:
                    logger.warning("Тест директору: не задан корректный отправитель.")
                    return False, "Не задан отправитель (MAIL_DEFAULT_SENDER или MAIL_USERNAME в формате email)."
                if not app.config.get('MAIL_PASSWORD'):
                    return False, "Не задан пароль SMTP (MAIL_PASSWORD). Задайте в настройках или переменной окружения."
                msg = Message(
                    subject="Тест уведомлений директору",
                    sender=sender,
                    recipients=[recipient],
                    html="""
                        <h3>Тестовая отправка</h3>
                        <p>Канал уведомлений директору настроен корректно.</p>
                    """
                )
                _send_mail_with_retry(mail, msg, app)
            return True, None
        except Exception as e:
            err_text = str(e).strip() or type(e).__name__
            logger.warning(f"Не удалось отправить тестовое письмо директору: {e}", exc_info=True)
            return False, err_text

    @staticmethod
    def send_director_dashboard_report(
        preset: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        recipient_email: Optional[str] = None,
    ) -> tuple:
        """
        Отправляет сводный отчёт по компании на email директора.
        Использует director_email из настроек, если recipient_email не передан.
        Returns:
            (success: bool, error_message: Optional[str])
        """
        try:
            from app.services.settings_service import SettingsService
            from app.services.dashboard_service import DashboardService
            from app.services.finance_service import FinanceService
            from flask import current_app, render_template

            settings = SettingsService.get_general_settings() or {}
            recipient = _normalize_email_address(
                (recipient_email or settings.get('director_email') or '').strip()
            )
            if not recipient:
                return False, "Не задан email директора. Укажите в настройках «Уведомления директору»."

            try:
                data = DashboardService.get_full_dashboard(
                    preset=preset,
                    date_from=date_from,
                    date_to=date_to,
                )
                # Не мутируем объект из кеша DashboardService.
                data = dict(data or {})
            except Exception as e:
                logger.warning(f"Ошибка получения данных dashboard для письма: {e}")
                return False, f"Не удалось сформировать отчёт: {e}"

            # Добавляем в письмо состояние кассы (как на странице /finance/cash):
            # остатки на конец периода по способам оплаты + подсказку «доложить в наличку».
            period = data.get("period") or {}
            period_from = period.get("current_from") or date_from
            period_to = period.get("current_to") or date_to
            payment_method_settings = SettingsService.get_payment_method_settings() or {}
            cash_label = (payment_method_settings.get("cash_label") or "Наличные").strip()
            transfer_label = (payment_method_settings.get("transfer_label") or "Перевод").strip()
            try:
                cash_summary = FinanceService.get_cash_summary(
                    date_from=period_from,
                    date_to=period_to,
                ) or {}
            except Exception as e:
                logger.warning(f"Ошибка расчёта состояния кассы для письма директору: {e}")
                cash_summary = {}

            balance_by_method = cash_summary.get("balance_by_method") or {}
            cash_balance_end = float(balance_by_method.get("cash", 0) or 0)
            transfer_balance_end = float(balance_by_method.get("transfer", 0) or 0)
            data["cash_state"] = {
                "cash_label": cash_label,
                "transfer_label": transfer_label,
                "cash_balance_end": cash_balance_end,
                "transfer_balance_end": transfer_balance_end,
                "cash_topup_needed": max(0.0, -cash_balance_end),
                "by_payment_method": cash_summary.get("by_payment_method") or {},
                "opening_balance_by_method": cash_summary.get("opening_balance_by_method") or {},
            }

            with current_app.app_context():
                html_body = render_template('email/dashboard_report.html', data=data)
            period_label = " — ".join(
                filter(None, [date_from, date_to])
            ) or (preset or "текущий период")
            subject = f"Сводный отчёт по компании ({period_label})"

            try:
                from flask_mail import Message
                from app import mail, MAIL_AVAILABLE
                if not MAIL_AVAILABLE or mail is None:
                    return False, "Flask-Mail недоступен."
            except ImportError:
                return False, "Модуль flask_mail не установлен."

            with current_app.app_context():
                app = current_app._get_current_object()
                _apply_mail_config_from_settings(app)
                sender = _resolve_sender_email(app)
                if not sender or '@' not in sender:
                    return False, "Не задан отправитель в настройках почты."
                msg = Message(
                    subject=subject,
                    sender=sender,
                    recipients=[recipient],
                    html=html_body,
                )
                _send_mail_with_retry(mail, msg, app)
            return True, None
        except Exception as e:
            err_text = str(e).strip() or type(e).__name__
            logger.warning(f"Отправка сводного отчёта директору: {e}", exc_info=True)
            return False, err_text

    @staticmethod
    def notify_order_status_change(
        order_id: int,
        new_status: str,
        customer_id: Optional[int] = None,
        changed_by_user_id: Optional[int] = None
    ):
        """
        Отправляет уведомления о смене статуса заявки.
        
        Кто получает уведомления:
        - Мастер заявки (если у мастера привязан user_id) — in_app + push
        - Менеджер заявки (если у менеджера привязан user_id) — in_app
        - Пользователь, изменивший статус (changed_by_user_id) — in_app (чтобы всегда видеть подтверждение в колокольчике)
        
        Args:
            order_id: ID заявки
            new_status: Новый статус
            customer_id: ID клиента (опционально)
            changed_by_user_id: ID пользователя, изменившего статус (ему тоже создаётся in_app уведомление)
        """
        try:
            from app.services.order_service import OrderService
            from app.services.customer_service import CustomerService
            from app.services.master_service import MasterService
            from app.services.manager_service import ManagerService
            
            order = OrderService.get_order(order_id)
            if not order:
                return
            oid = getattr(order, 'id', order_id)
            master_id = getattr(order, 'master_id', None)
            manager_id = getattr(order, 'manager_id', None)
            
            notified_user_ids = set()
            
            # Уведомляем пользователя, изменившего статус (всегда видит подтверждение в колокольчике)
            if changed_by_user_id:
                title = f"Статус заявки #{oid} изменён"
                message = f"Вы изменили статус заявки #{oid} на: {new_status}"
                NotificationService.send_in_app_notification(
                    user_id=changed_by_user_id,
                    title=title,
                    message=message,
                    entity_type='order',
                    entity_id=oid
                )
                notified_user_ids.add(changed_by_user_id)
            
            # Уведомляем мастера (если привязан user_id и это не тот же пользователь)
            if master_id:
                master = MasterService.get_master_by_id(master_id)
                if master and master.get('user_id'):
                    uid = master['user_id']
                    if uid not in notified_user_ids:
                        title = f"Изменен статус заявки #{oid}"
                        message = f"Статус заявки #{oid} изменен на: {new_status}"
                        NotificationService.send_in_app_notification(
                            user_id=uid,
                            title=title,
                            message=message,
                            entity_type='order',
                            entity_id=oid
                        )
                        NotificationService.send_push_notification(
                            user_id=uid,
                            title=title,
                            message=message,
                            entity_type='order',
                            entity_id=oid
                        )
                        notified_user_ids.add(uid)
            
            # Уведомляем менеджера (если привязан user_id и это не тот же пользователь)
            if manager_id:
                manager = ManagerService.get_manager_by_id(manager_id)
                if manager and manager.get('user_id'):
                    uid = manager['user_id']
                    if uid not in notified_user_ids:
                        title = f"Изменен статус заявки #{oid}"
                        message = f"Статус заявки #{oid} изменен на: {new_status}"
                        NotificationService.send_in_app_notification(
                            user_id=uid,
                            title=title,
                            message=message,
                            entity_type='order',
                            entity_id=oid
                        )
                        notified_user_ids.add(uid)
            
            # Уведомляем клиента по email (шаблонные письма)
            if customer_id:
                status_norm = (new_status or '').strip().lower()
                if status_norm in ('готово', 'ready', 'completed'):
                    NotificationService.send_customer_order_email(
                        order_id=order_id,
                        template_type='order_ready',
                        customer_id=customer_id,
                        status_name=new_status,
                    )
                elif status_norm in ('закрыта', 'закрыт', 'closed'):
                    NotificationService.send_customer_order_email(
                        order_id=order_id,
                        template_type='order_closed_thanks',
                        customer_id=customer_id,
                        status_name=new_status,
                    )
                else:
                    # Для промежуточных статусов отправляем универсальное письмо о смене статуса.
                    # Для "Готово"/"Закрыта" отправляются отдельные специализированные шаблоны.
                    NotificationService.send_customer_order_email(
                        order_id=order_id,
                        template_type='order_status_update',
                        customer_id=customer_id,
                        status_name=new_status,
                        extra_context={'STATUS_NAME': new_status},
                    )

            # Отдельное уведомление директору при закрытии заявки
            status_norm = (new_status or '').strip().lower()
            if status_norm in ('закрыта', 'закрыт', 'closed'):
                NotificationService.send_director_order_email(
                    order_id=order_id,
                    template_type='director_order_closed_report',
                    status_name=new_status,
                )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомлений о смене статуса: {e}", exc_info=True)
    
    @staticmethod
    def get_user_notifications(
        user_id: int,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict]:
        """
        Получает уведомления пользователя.
        
        Args:
            user_id: ID пользователя
            unread_only: Только непрочитанные
            limit: Лимит записей
            
        Returns:
            Список уведомлений
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                query = '''
                    SELECT id, type, title, message, entity_type, entity_id, 
                           read_at, created_at
                    FROM notifications
                    WHERE user_id = ?
                '''
                params = [user_id]
                
                if unread_only:
                    query += ' AND read_at IS NULL'
                
                query += ' ORDER BY created_at DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении уведомлений: {e}", exc_info=True)
            return []
    
    @staticmethod
    def mark_as_read(notification_id: int, user_id: int) -> bool:
        """
        Отмечает уведомление как прочитанное.
        
        Args:
            notification_id: ID уведомления
            user_id: ID пользователя (для проверки прав)
            
        Returns:
            True если успешно
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE notifications
                    SET read_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                ''', (notification_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при отметке уведомления как прочитанного: {e}")
            return False
    
    @staticmethod
    def mark_all_as_read(user_id: int) -> int:
        """
        Отмечает все уведомления пользователя как прочитанные.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество обновленных уведомлений
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE notifications
                    SET read_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND read_at IS NULL
                ''', (user_id,))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Ошибка при отметке всех уведомлений как прочитанных: {e}")
            return 0
    
    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """
        Получает количество непрочитанных уведомлений.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество непрочитанных уведомлений
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM notifications
                    WHERE user_id = ? AND read_at IS NULL
                ''', (user_id,))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Ошибка при получении количества непрочитанных уведомлений: {e}")
            return 0
    
    @staticmethod
    def is_notification_enabled(
        user_id: int,
        channel: str,
        notification_type: str
    ) -> bool:
        """
        Проверяет, включены ли уведомления для пользователя.
        
        Args:
            user_id: ID пользователя
            channel: Канал (email/push)
            notification_type: Тип уведомления (order_status_change, low_stock, etc.)
            
        Returns:
            True если уведомления включены
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT enabled, email_enabled, push_enabled
                    FROM notification_preferences
                    WHERE user_id = ? AND notification_type = ?
                ''', (user_id, notification_type))
                row = cursor.fetchone()
                
                if not row:
                    # По умолчанию все включено
                    return True
                
                enabled, email_enabled, push_enabled = row
                
                if not enabled:
                    return False
                
                if channel == 'email':
                    return email_enabled == 1
                elif channel == 'push':
                    return push_enabled == 1
                
                return True
        except Exception as e:
            logger.error(f"Ошибка при проверке настроек уведомлений: {e}")
            return True  # По умолчанию включено
    
    @staticmethod
    def set_notification_preference(
        user_id: int,
        notification_type: str,
        enabled: bool = True,
        email_enabled: bool = True,
        push_enabled: bool = True
    ) -> bool:
        """
        Устанавливает настройки уведомлений для пользователя.
        
        Args:
            user_id: ID пользователя
            notification_type: Тип уведомления
            enabled: Включены ли уведомления
            email_enabled: Включены ли email уведомления
            push_enabled: Включены ли push уведомления
            
        Returns:
            True если успешно
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO notification_preferences 
                    (user_id, notification_type, enabled, email_enabled, push_enabled, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, notification_type) DO UPDATE SET
                        enabled = excluded.enabled,
                        email_enabled = excluded.email_enabled,
                        push_enabled = excluded.push_enabled,
                        updated_at = CURRENT_TIMESTAMP
                ''', (user_id, notification_type, int(enabled), int(email_enabled), int(push_enabled)))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при установке настроек уведомлений: {e}")
            return False
    
    @staticmethod
    def get_notification_preferences(user_id: int) -> Dict[str, Dict]:
        """
        Получает все настройки уведомлений пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь {notification_type: {enabled, email_enabled, push_enabled}}
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT notification_type, enabled, email_enabled, push_enabled
                    FROM notification_preferences
                    WHERE user_id = ?
                ''', (user_id,))
                rows = cursor.fetchall()
                return {
                    row['notification_type']: {
                        'enabled': bool(row['enabled']),
                        'email_enabled': bool(row['email_enabled']),
                        'push_enabled': bool(row['push_enabled'])
                    }
                    for row in rows
                }
        except Exception as e:
            logger.error(f"Ошибка при получении настроек уведомлений: {e}")
            return {}
