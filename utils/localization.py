import json
from pathlib import Path
from typing import Dict, Any, Optional


class Localization:
    """Система локализации"""
    
    def __init__(self):
        self.locales: Dict[str, Dict[str, Any]] = {}
        self.default_language = "ru"
        self.current_language = "ru"
        self.supported_languages = ["ru", "ky", "kk"]
        self._load_locales()
    
    def _load_locales(self):
        """Загрузка локалей из файлов"""
        locales_dir = Path("locales")
        
        for lang in self.supported_languages:
            locale_file = locales_dir / f"{lang}.json"
            if locale_file.exists():
                try:
                    with open(locale_file, "r", encoding="utf-8") as f:
                        self.locales[lang] = json.load(f)
                except Exception as e:
                    print(f"Ошибка загрузки локали {lang}: {e}")
                    self.locales[lang] = {}
            else:
                print(f"Файл локали {lang} не найден")
                self.locales[lang] = {}
    
    def get_text(self, key: str, language: str = None, **kwargs) -> str:
        """Получение локализованного текста"""
        if language is None:
            language = self.current_language
        
        if language not in self.supported_languages:
            language = self.default_language
        
        # Разбиваем ключ на части (например, "start.welcome")
        keys = key.split(".")
        text = self.locales.get(language, {})
        
        try:
            for k in keys:
                text = text[k]
        except (KeyError, TypeError):
            # Если перевод не найден, пробуем дефолтный язык
            if language != self.default_language:
                return self.get_text(key, self.default_language, **kwargs)
            else:
                return f"[{key}]"  # Возвращаем ключ если перевод не найден
        
        # Подставляем параметры
        if isinstance(text, str) and kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text
        
        return text
    
    def set_language(self, language: str) -> None:
        """Установка текущего языка"""
        if language in self.supported_languages:
            self.current_language = language
    
    def get_language_name(self, language: str) -> str:
        """Получение названия языка"""
        return self.get_text(f"languages.{language}", language)
    
    def get_region_name(self, region: str, language: str = None) -> str:
        """Получение названия региона"""
        return self.get_text(f"regions.{region}", language)
    
    def is_supported_language(self, language: str) -> bool:
        """Проверка поддержки языка"""
        return language in self.supported_languages


# Глобальный экземпляр локализации
localization = Localization()


def _(key: str, language: str = None, **kwargs) -> str:
    """Краткая функция для получения перевода"""
    return localization.get_text(key, language, **kwargs)