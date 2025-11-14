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
    Автоматически определяет тип сообщения (текст/фото) и использует правильный метод.
    
    Args:
        message: Сообщение для редактирования
        text: Новый текст сообщения
        reply_markup: Новая клавиатура (опционально)
        parse_mode: Режим парсинга текста (опционально)
    
    Returns:
        bool: True если сообщение успешно отредактировано, False иначе
    """
    try:
        # Проверяем, содержит ли сообщение фото
        if message.photo:
            # Для фото сообщений не можем заменить на текст - нужно удалить и отправить новое
            await message.delete()
            await message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return True
        else:
            # Обычное текстовое сообщение - используем edit_text
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


async def safe_send_message(
    chat_id: Union[int, str, Message],
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None
) -> Optional[Message]:
    """
    Безопасная отправка сообщения с обработкой ошибок.
    
    Args:
        chat_id: ID чата для отправки или объект Message (для получения chat_id и bot)
        text: Текст сообщения
        reply_markup: Клавиатура (опционально)
        parse_mode: Режим парсинга текста (опционально)
    
    Returns:
        Message: Отправленное сообщение или None при ошибке
    """
    try:
        # Если передан объект Message, используем его метод answer
        if isinstance(chat_id, Message):
            sent_message = await chat_id.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return sent_message
        else:
            # Это старое использование, которое не поддерживается
            # Нужно всегда передавать Message объект
            logger.error("safe_send_message: передайте объект Message вместо chat_id")
            return None
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        return None