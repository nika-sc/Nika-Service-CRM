"""
Утилиты для работы с датой и временем.
Все функции возвращают время в часовом поясе, настроенном в конфиге (по умолчанию UTC+3 для Москвы).
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from flask import current_app


def _get_timezone_offset() -> int:
    """
    Получает смещение часового пояса от UTC в часах.
    Сначала пытается получить из настроек БД, затем из конфига, затем использует значение по умолчанию 3 (Москва).
    
    Returns:
        Смещение в часах от UTC (например, 3 для Москвы)
    """
    # Сначала пытаемся получить из настроек БД
    try:
        from app.services.settings_service import SettingsService
        settings = SettingsService.get_general_settings()
        timezone_offset = settings.get('timezone_offset')
        if timezone_offset is not None:
            # Преобразуем в int, если это строка или число
            try:
                return int(timezone_offset)
            except (ValueError, TypeError):
                # Если не удалось преобразовать, используем значение по умолчанию
                pass
    except Exception:
        # Если не удалось получить из БД, продолжаем
        pass
    
    # Если не удалось получить из БД, пытаемся получить из конфига Flask приложения
    try:
        if current_app:
            return current_app.config.get('TIMEZONE_OFFSET', 3)
    except RuntimeError:
        # Приложение не инициализировано, используем значение по умолчанию
        pass
    
    # Если не удалось получить из конфига, используем значение по умолчанию
    # или пытаемся загрузить из модуля конфига
    try:
        from app.config import Config
        return Config.TIMEZONE_OFFSET
    except (ImportError, AttributeError):
        return 3  # По умолчанию Москва (UTC+3)


def _get_app_timezone():
    """
    Получает объект timezone для приложения.
    Предпочитает ZoneInfo('Europe/Moscow') при offset=3 (более надёжно).
    
    Returns:
        timezone объект с настроенным смещением
    """
    offset = _get_timezone_offset()
    if offset == 3:
        try:
            from zoneinfo import ZoneInfo
            return ZoneInfo("Europe/Moscow")
        except ImportError:
            pass
    return timezone(timedelta(hours=offset))


# Московский часовой пояс (UTC+3) - используется как значение по умолчанию
# Для получения текущего часового пояса используйте _get_app_timezone()
MOSCOW_TZ = timezone(timedelta(hours=3))


def get_moscow_now() -> datetime:
    """
    Возвращает текущее время в часовом поясе, настроенном в приложении.
    По умолчанию московское время (UTC+3).
    
    Returns:
        datetime объект с временем в настроенном часовом поясе (timezone-aware)
    """
    app_tz = _get_app_timezone()
    return datetime.now(app_tz)


def get_moscow_now_str(format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Возвращает текущее время в настроенном часовом поясе в виде строки.
    По умолчанию московское время (UTC+3).
    
    Args:
        format: Формат строки (по умолчанию '%Y-%m-%d %H:%M:%S')
        
    Returns:
        Строка с текущим временем в настроенном часовом поясе
    """
    return get_moscow_now().strftime(format)


def get_moscow_now_naive() -> datetime:
    """
    Возвращает текущее время в настроенном часовом поясе без информации о timezone (naive datetime).
    Используется для сохранения в базу данных, где время хранится как строка без timezone.
    По умолчанию московское время (UTC+3).
    
    Returns:
        datetime объект без timezone (naive), но с временем в настроенном часовом поясе
    """
    return get_moscow_now().replace(tzinfo=None)


def get_moscow_now_iso() -> str:
    """
    Возвращает текущее время в настроенном часовом поясе в ISO формате.
    По умолчанию московское время (UTC+3).
    
    Returns:
        Строка в формате ISO (например, YYYY-MM-DDTHH:MM:SS+03:00)
    """
    return get_moscow_now().isoformat()


def convert_to_moscow(dt: datetime) -> datetime:
    """
    Конвертирует datetime в часовой пояс, настроенный в приложении.
    По умолчанию московское время (UTC+3).
    
    Args:
        dt: datetime объект (может быть naive или timezone-aware)
        
    Returns:
        datetime объект в настроенном часовом поясе
    """
    app_tz = _get_app_timezone()
    if dt.tzinfo is None:
        # Если naive, считаем что это уже время в настроенном поясе
        return dt.replace(tzinfo=app_tz)
    else:
        # Если есть timezone, конвертируем в настроенный часовой пояс
        return dt.astimezone(app_tz)


def parse_datetime_to_moscow(date_str: str, format: Optional[str] = None) -> datetime:
    """
    Парсит строку с датой и временем и возвращает datetime в московском часовом поясе.
    
    Args:
        date_str: Строка с датой и временем
        format: Формат для парсинга (если None, пробует стандартные форматы)
        
    Returns:
        datetime объект в московском часовом поясе
    """
    if format:
        dt = datetime.strptime(date_str, format)
    else:
        # Пробуем стандартные форматы
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z'
        ]
        dt = None
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        
        if dt is None:
            raise ValueError(f"Не удалось распарсить дату: {date_str}")
    
    # Если datetime naive, считаем что это время в настроенном поясе
    app_tz = _get_app_timezone()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=app_tz)
    else:
        # Если есть timezone, конвертируем в настроенный часовой пояс
        return dt.astimezone(app_tz)
