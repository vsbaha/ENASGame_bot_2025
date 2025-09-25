"""
Middleware для обработки ошибок Telegram API
"""

import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, ErrorEvent
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseMiddleware):
    """Middleware для обработки ошибок API Telegram"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                logger.debug(f"Сообщение не изменилось, игнорируем ошибку: {e}")
                return None
            elif "message to edit not found" in str(e):
                logger.debug(f"Сообщение для редактирования не найдено: {e}")
                return None
            elif "Bad Request: message can't be edited" in str(e):
                logger.debug(f"Сообщение нельзя редактировать: {e}")
                return None
            else:
                logger.error(f"Ошибка Telegram API: {e}")
                raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка в обработчике: {e}")
            raise