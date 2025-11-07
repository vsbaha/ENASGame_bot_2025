"""
Модуль управления турнирами - импортирует из подпапки tournaments
"""
from .tournaments import router

# Экспортируем router для обратной совместимости
__all__ = ['router']