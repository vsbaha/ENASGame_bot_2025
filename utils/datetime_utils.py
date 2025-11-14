"""
Утилиты для работы с датами и временными зонами
"""
from datetime import datetime
from typing import Optional
import pytz


def format_datetime_for_user(
    dt: datetime,
    user_timezone: str = "Asia/Bishkek",
    format_str: str = "%d.%m.%Y %H:%M"
) -> str:
    """
    Форматирует datetime для отображения пользователю в его timezone
    
    Args:
        dt: Datetime объект (должен быть в UTC)
        user_timezone: Timezone пользователя (default: Asia/Bishkek)
        format_str: Формат строки (default: ДД.ММ.ГГГГ ЧЧ:ММ)
    
    Returns:
        str: Отформатированная строка с датой и временем
    """
    try:
        # Убеждаемся что datetime в UTC
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        elif dt.tzinfo != pytz.utc:
            dt = dt.astimezone(pytz.utc)
        
        # Конвертируем в timezone пользователя
        user_tz = pytz.timezone(user_timezone)
        local_dt = dt.astimezone(user_tz)
        
        return local_dt.strftime(format_str)
    except Exception as e:
        # Если что-то пошло не так, возвращаем как есть
        return dt.strftime(format_str)


def get_timezone_offset(timezone_str: str = "Asia/Bishkek") -> str:
    """
    Получить строковое представление смещения timezone
    
    Args:
        timezone_str: Название timezone
    
    Returns:
        str: Смещение в формате "UTC+6" или "UTC-5"
    """
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        offset = now.strftime('%z')
        
        # Форматируем offset как UTC+X
        hours = int(offset[:3])
        if hours >= 0:
            return f"UTC+{hours}"
        else:
            return f"UTC{hours}"
    except Exception:
        return "UTC"


def get_user_datetime_with_timezone(
    dt: datetime,
    user_timezone: str = "Asia/Bishkek"
) -> str:
    """
    Получить отформатированную дату с указанием timezone
    
    Args:
        dt: Datetime объект
        user_timezone: Timezone пользователя
    
    Returns:
        str: "ДД.ММ.ГГГГ ЧЧ:ММ (UTC+6)"
    """
    formatted_time = format_datetime_for_user(dt, user_timezone)
    timezone_offset = get_timezone_offset(user_timezone)
    return f"{formatted_time} ({timezone_offset})"
