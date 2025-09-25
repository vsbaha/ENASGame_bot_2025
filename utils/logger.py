"""
Настройка логирования для бота
"""

import logging
import sys
from pathlib import Path
from loguru import logger

from config.settings import settings as config


def setup_logger():
    """Настройка системы логирования"""
    
    # Удаляем стандартный handler loguru
    logger.remove()
    
    # Настраиваем формат логов
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Добавляем вывод в консоль
    logger.add(
        sys.stdout,
        format=log_format,
        level=config.log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Добавляем вывод в файл
    # Создаем папку logs если её нет
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Определяем путь к основному лог-файлу
    log_file = logs_dir / "bot.log"
    
    logger.add(
        log_file,
        format=log_format,
        level=config.log_level,
        rotation="1 day",
        retention="1 month",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    # Добавляем отдельный файл для ошибок
    error_log_file = logs_dir / "errors.log"
    logger.add(
        error_log_file,
        format=log_format,
        level="ERROR",
        rotation="5 MB",
        retention="1 month",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    # Перенаправляем стандартное логирование Python в loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Получаем соответствующий уровень Loguru
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # Находим caller из которого был вызван лог
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # Настраиваем стандартное логирование Python
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Устанавливаем уровень для конкретных логгеров
    for logger_name in ["aiogram", "aiohttp", "sqlalchemy"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    logger.info("Система логирования настроена")


def get_logger(name: str):
    """Получить логгер с указанным именем"""
    return logger.bind(name=name)