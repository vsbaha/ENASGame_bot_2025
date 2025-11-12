"""
Модуль управления матчами турниров
"""
from aiogram import Router

from .match_manager import router as match_router

# Создаем главный роутер для матчей
router = Router()
router.include_router(match_router)

__all__ = ["router"]
