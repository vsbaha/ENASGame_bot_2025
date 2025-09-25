import sys
from pathlib import Path
from loguru import logger

from config.settings import settings


def setup_logger():
    """Настройка системы логирования"""
    
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Создаем папку для логов если её нет
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Консольный вывод
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )
    
    # Файл для всех логов
    logger.add(
        logs_dir / "bot.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    # Файл только для ошибок
    logger.add(
        logs_dir / "errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="5 MB",
        retention="30 days",
        compression="zip"
    )
    
    # Файл для действий пользователей
    logger.add(
        logs_dir / "user_actions.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {extra[user_id]} | {extra[action]} | {message}",
        level="INFO",
        rotation="20 MB",
        retention="30 days",
        compression="zip",
        filter=lambda record: "user_action" in record["extra"]
    )
    
    logger.info("Система логирования настроена")