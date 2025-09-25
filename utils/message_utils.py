"""
Утилиты для безопасной работы с сообщениями Telegram
"""

import logging
from typing import Optional, Union
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


async def safe_edit_message(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None
) -> bool:
    """
    Безопасное редактирование сообщения с обработкой ошибок.
    
    Args:
        message: Сообщение для редактирования
        text: Новый текст сообщения
        reply_markup: Новая клавиатура (опционально)
        parse_mode: Режим парсинга текста (опционально)
    
    Returns:
        bool: True если сообщение успешно отредактировано, False иначе
    """
    try:
        await message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.debug(f"Сообщение не изменилось, пропускаем редактирование: {e}")
            return False
        else:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при редактировании сообщения: {e}")
        raise


async def safe_answer_or_edit(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None,
    force_new_message: bool = False
) -> Message:
    """
    Безопасная отправка нового сообщения или редактирование существующего.
    
    Args:
        message: Сообщение для попытки редактирования
        text: Текст сообщения
        reply_markup: Клавиатура (опционально)
        parse_mode: Режим парсинга текста (опционально)
        force_new_message: Принудительно отправить новое сообщение
    
    Returns:
        Message: Отредактированное или новое сообщение
    """
    if not force_new_message:
        # Сначала пытаемся отредактировать
        edit_success = await safe_edit_message(
            message=message,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        
        if edit_success:
            return message
    
    # Если редактирование не удалось или принудительно нужно новое сообщение
    new_message = await message.answer(
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode
    )
    
    # Удаляем старое сообщение, если это возможно
    try:
        await message.delete()
    except Exception as e:
        logger.debug(f"Не удалось удалить старое сообщение: {e}")
    
    return new_message