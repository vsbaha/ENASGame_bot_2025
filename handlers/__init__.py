"""
Инициализация хендлеров
"""

from aiogram import Router

from .user import user_router
from .admin import setup_admin_handlers


def setup_handlers() -> Router:
    """Настройка всех хендлеров"""
    main_router = Router()
    
    # ВАЖНО: Админские хендлеры должны быть ПЕРВЫМИ
    # чтобы они обрабатывались раньше общего обработчика в navigation.py
    admin_router = setup_admin_handlers()
    main_router.include_router(admin_router)
    
    # Добавляем пользовательские хендлеры
    main_router.include_router(user_router)
    
    return main_router


__all__ = ["setup_handlers", "user_router"]