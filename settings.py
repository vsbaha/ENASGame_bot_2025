"""
Конфигурация приложения
"""

import os
from typing import List
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


class Config:
    """Класс конфигурации приложения"""
    
    # Telegram Bot Settings
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Database Settings
    DB_URL: str = os.getenv("DB_URL", "sqlite+aiosqlite:///./tournament_bot.db")
    
    # Admin Settings
    ADMIN_USER_IDS: List[int] = [
        int(user_id.strip()) 
        for user_id in os.getenv("ADMIN_USER_IDS", "").split(",") 
        if user_id.strip().isdigit()
    ]
    
    # Bot Settings
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "ru")
    DEFAULT_REGION: str = os.getenv("DEFAULT_REGION", "ru")
    
    # File Upload Settings
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "5"))
    ALLOWED_IMAGE_FORMATS: List[str] = [
        fmt.strip().lower() 
        for fmt in os.getenv("ALLOWED_IMAGE_FORMATS", "jpg,jpeg,png,gif,webp").split(",")
    ]
    
    # Logging Settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "bot.log")
    
    # Supported languages and regions
    SUPPORTED_LANGUAGES = ["ru", "ky", "kk"]
    SUPPORTED_REGIONS = ["ru", "kg", "kz"]
    
    @classmethod
    def validate(cls) -> bool:
        """Проверяем корректность конфигурации"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в .env файле")
        
        if cls.DEFAULT_LANGUAGE not in cls.SUPPORTED_LANGUAGES:
            raise ValueError(f"DEFAULT_LANGUAGE должен быть одним из: {cls.SUPPORTED_LANGUAGES}")
        
        if cls.DEFAULT_REGION not in cls.SUPPORTED_REGIONS:
            raise ValueError(f"DEFAULT_REGION должен быть одним из: {cls.SUPPORTED_REGIONS}")
        
        return True


# Создаем экземпляр конфигурации
config = Config()