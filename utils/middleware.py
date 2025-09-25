from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TelegramUser, Update

from database.repositories.user_repository import UserRepository
from database.models import User, UserRole
from config.settings import settings


class UserMiddleware(BaseMiddleware):
    """Middleware для работы с пользователями"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Обработка события"""
        
        # Получаем пользователя из события
        telegram_user: TelegramUser = data.get("event_from_user")
        if not telegram_user:
            return await handler(event, data)
        
        # Проверяем, есть ли пользователь в базе данных
        user = await UserRepository.get_by_telegram_id(telegram_user.id)
        
        if user:
            # Обновляем информацию о пользователе
            if (user.username != telegram_user.username or 
                user.full_name != telegram_user.full_name):
                await UserRepository.update_user_info(
                    telegram_user.id,
                    telegram_user.username,
                    telegram_user.full_name
                )
                # Обновляем объект пользователя
                user.username = telegram_user.username
                user.full_name = telegram_user.full_name
        else:
            # Создаем нового пользователя
            user = await UserRepository.create_user(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                full_name=telegram_user.full_name
            )
        
        # Проверяем, является ли пользователь администратором
        is_admin = telegram_user.id in settings.admin_ids
        if is_admin and user.role != UserRole.ADMIN.value:
            await UserRepository.set_admin_role(telegram_user.id, True)
            user.role = UserRole.ADMIN.value
        
        # Проверяем блокировку
        if user.is_blocked:
            # Если пользователь заблокирован, не обрабатываем событие
            return
        
        # Добавляем пользователя в данные для handlers
        data["user"] = user
        data["is_admin"] = is_admin
        
        return await handler(event, data)