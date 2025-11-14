"""
Основной файл Telegram бота для турниров
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import TelegramObject, BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from settings import config
from database.db_manager import init_database
from database.repositories.user_repository import UserRepository
from database.models import UserRole
from utils.admin_commands import USER_COMMANDS, update_all_admin_commands
from handlers import setup_handlers
from utils.logger import setup_logger
from middlewares import ErrorHandlerMiddleware


class UserMiddleware(BaseMiddleware):
    """Middleware для работы с пользователями"""
    
    async def __call__(
        self,
        handler,
        event: TelegramObject,
        data: dict
    ):
        # Добавляем информацию о пользователе в данные
        if hasattr(event, 'from_user') and event.from_user:
            data["user_id"] = event.from_user.id
            data["username"] = event.from_user.username
            data["first_name"] = event.from_user.first_name
            data["last_name"] = event.from_user.last_name
        
        return await handler(event, data)


async def on_startup(bot: Bot) -> None:
    """Действия при запуске бота"""
    logger = logging.getLogger(__name__)
    
    try:
        # Удаляем webhook и очищаем ожидающие обновления
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook удален, старые обновления очищены")
        
        # Инициализируем базу данных
        await init_database()
        logger.info("База данных инициализирована")
        
        # Устанавливаем команды для обычных пользователей
        await bot.set_my_commands(USER_COMMANDS, scope=BotCommandScopeDefault())
        
        # Устанавливаем команды для всех администраторов
        await update_all_admin_commands(bot)
        
        logger.info("Команды бота установлены")
        
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        logger.info(f"Бот запущен: @{bot_info.username}")
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise


async def on_shutdown(bot: Bot) -> None:
    """Действия при остановке бота"""
    logger = logging.getLogger(__name__)
    logger.info("Бот остановлен")


async def main():
    """Основная функция запуска бота"""
    
    # Настраиваем логирование
    setup_logger()
    logger = logging.getLogger(__name__)
    
    try:
        # Проверяем конфигурацию
        config.validate()
        logger.info("Конфигурация проверена успешно")
        
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        return
    
    # Создаем бота
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )
    
    # Создаем диспетчер с хранилищем состояний в памяти
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрируем middleware
    dp.message.middleware(ErrorHandlerMiddleware())
    dp.callback_query.middleware(ErrorHandlerMiddleware())
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())
    
    # Регистрируем хендлеры
    main_router = setup_handlers()
    dp.include_router(main_router)
    
    # Регистрируем события запуска и остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запускаем бота
    logger.info("Запускаем бота...")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query", "inline_query"],
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await bot.session.close()
        logger.info("Сессия бота закрыта")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()