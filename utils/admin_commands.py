"""
Утилиты для управления командами администраторов
"""

import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

logger = logging.getLogger(__name__)


# Команды для обычных пользователей
USER_COMMANDS = [
    BotCommand(command="start", description="Запуск бота"),
    BotCommand(command="help", description="Помощь"),
    BotCommand(command="menu", description="Главное меню")
]

# Команды для администраторов
ADMIN_COMMANDS = [
    BotCommand(command="start", description="Запуск бота"),
    BotCommand(command="help", description="Помощь"),
    BotCommand(command="menu", description="Главное меню"),
    BotCommand(command="admin", description="Админ-панель")
]


async def set_admin_commands(bot: Bot, user_id: int) -> bool:
    """
    Устанавливает команды администратора для пользователя
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя в Telegram
        
    Returns:
        bool: True если команды установлены успешно, False в случае ошибки
    """
    try:
        await bot.set_my_commands(
            ADMIN_COMMANDS,
            scope=BotCommandScopeChat(chat_id=user_id)
        )
        logger.info(f"Команды администратора установлены для пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка установки команд администратора для пользователя {user_id}: {e}")
        return False


async def remove_admin_commands(bot: Bot, user_id: int) -> bool:
    """
    Убирает команды администратора для пользователя (возвращает к обычным командам)
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя в Telegram
        
    Returns:
        bool: True если команды удалены успешно, False в случае ошибки
    """
    try:
        await bot.set_my_commands(
            USER_COMMANDS,
            scope=BotCommandScopeChat(chat_id=user_id)
        )
        logger.info(f"Команды администратора удалены для пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления команд администратора для пользователя {user_id}: {e}")
        return False


async def update_all_admin_commands(bot: Bot) -> None:
    """
    Обновляет команды для всех администраторов в системе
    
    Args:
        bot: Экземпляр бота
    """
    try:
        from database.repositories.user_repository import UserRepository
        
        user_repo = UserRepository()
        admin_users = await user_repo.get_admins()
        
        success_count = 0
        for admin_user in admin_users:
            if await set_admin_commands(bot, admin_user.telegram_id):
                success_count += 1
        
        logger.info(f"Команды обновлены для {success_count} из {len(admin_users)} администраторов")
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении команд для всех администраторов: {e}")