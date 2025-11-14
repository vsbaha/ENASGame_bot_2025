"""
Проверка подписки пользователей на обязательные каналы
"""
import logging
from typing import List, Tuple
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

logger = logging.getLogger(__name__)


async def check_channel_subscription(bot: Bot, user_id: int, channel: str) -> bool:
    """
    Проверка подписки пользователя на один канал
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя Telegram
        channel: Username канала (@channel или channel)
    
    Returns:
        True если пользователь подписан, False если нет
    """
    try:
        # Убираем @ если есть
        channel_id = channel if not channel.startswith('@') else channel[1:]
        
        # Проверяем статус участника
        member = await bot.get_chat_member(f"@{channel_id}", user_id)
        
        # Статусы, при которых пользователь считается подписанным
        subscribed_statuses = ['creator', 'administrator', 'member']
        
        return member.status in subscribed_statuses
        
    except TelegramBadRequest as e:
        # Канал не найден или бот не имеет доступа
        logger.warning(f"Не удалось проверить канал {channel}: {e}")
        return False
    except TelegramForbiddenError as e:
        # Бот заблокирован или нет прав
        logger.warning(f"Нет доступа к каналу {channel}: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка проверки подписки на {channel}: {e}")
        return False


async def check_all_channels_subscription(
    bot: Bot, 
    user_id: int, 
    channels: List[str]
) -> Tuple[bool, List[str]]:
    """
    Проверка подписки пользователя на все обязательные каналы
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя Telegram
        channels: Список username'ов каналов
    
    Returns:
        Кортеж (все_подписан, список_неподписанных_каналов)
    """
    if not channels:
        return True, []
    
    # Логируем тип и содержимое для отладки
    logger.info(f"Проверка каналов: тип={type(channels)}, значение={channels}")
    
    # Проверяем что это действительно список
    if not isinstance(channels, list):
        logger.error(f"channels не является списком! Тип: {type(channels)}, значение: {channels}")
        # Пытаемся исправить если это строка JSON
        if isinstance(channels, str):
            import json
            try:
                channels = json.loads(channels)
                logger.info(f"Успешно распарсили JSON: {channels}")
            except Exception as e:
                logger.error(f"Не удалось распарсить JSON: {e}")
                return False, []
    
    unsubscribed = []
    
    for channel in channels:
        is_subscribed = await check_channel_subscription(bot, user_id, channel)
        if not is_subscribed:
            unsubscribed.append(channel)
    
    return len(unsubscribed) == 0, unsubscribed


def format_channel_url(channel: str) -> str:
    """
    Форматирование username канала в URL
    
    Args:
        channel: Username канала (@channel или channel)
    
    Returns:
        URL канала (https://t.me/channel)
    """
    # Убираем @ если есть
    clean_channel = channel[1:] if channel.startswith('@') else channel
    return f"https://t.me/{clean_channel}"


def format_channel_name(channel: str) -> str:
    """
    Форматирование username канала для отображения
    
    Args:
        channel: Username канала
    
    Returns:
        Отформатированное имя (@channel)
    """
    return f"@{channel}" if not channel.startswith('@') else channel
