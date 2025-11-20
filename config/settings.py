import os
from typing import List
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


class Settings:
    """Настройки приложения"""
    
    def __init__(self):
        # Токен бота
        self.bot_token = os.getenv("BOT_TOKEN", "")
        
        # Админы (поддержка обоих вариантов названия)
        admin_ids_str = os.getenv("ADMIN_IDS") or os.getenv("ADMIN_USER_IDS", "")
        self.admin_ids: List[int] = []
        if admin_ids_str:
            self.admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
        
        # ID чата для уведомлений админов
        admin_chat_id_str = os.getenv("ADMIN_CHAT_ID", "")
        self.admin_chat_id = int(admin_chat_id_str) if admin_chat_id_str else None
        
        # Поддержка
        self.support_username = os.getenv("SUPPORT_USERNAME", "support")
        
        # База данных
        self.database_path = os.getenv("DATABASE_PATH", "tournament_bot.db")
        
        # Логирование
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Часовой пояс по умолчанию
        self.timezone_default = os.getenv("TIMEZONE_DEFAULT", "Asia/Bishkek")
        
        # Настройки по умолчанию для пользователей
        self.default_language = os.getenv("DEFAULT_LANGUAGE", "ru")
        self.default_region = os.getenv("DEFAULT_REGION", "kg")
        
        # Ограничения файлов
        self.max_file_size = 5 * 1024 * 1024  # 5 MB
        self.allowed_image_types = ["image/jpeg", "image/png", "image/webp"]
        
        # Настройки турниров
        self.max_team_name_length = 50
        self.max_player_nickname_length = 30
        self.max_channels_per_tournament = 10
        
        # Challonge OAuth2 API
        self.challonge_client_id = os.getenv("CHALLONGE_CLIENT_ID", "")
        self.challonge_client_secret = os.getenv("CHALLONGE_CLIENT_SECRET", "")
        self.challonge_username = os.getenv("CHALLONGE_USERNAME", "")


# Глобальный экземпляр настроек
settings = Settings()