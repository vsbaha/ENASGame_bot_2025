"""
Инициализация пользовательских хендлеров
"""

from aiogram import Router

from .registration import registration_router
from .profile import profile_router
from .tournaments import tournaments_router
from .teams import teams_router
from .support import support_router
from .navigation import navigation_router


def setup_user_handlers() -> Router:
    """Настройка всех пользовательских хендлеров"""
    user_router = Router()
    
    # Подключаем все роутеры в правильном порядке
    user_router.include_router(registration_router)
    user_router.include_router(profile_router)
    user_router.include_router(tournaments_router)
    user_router.include_router(teams_router)
    user_router.include_router(support_router)
    user_router.include_router(navigation_router)  # navigation должен быть последним для unknown_message
    
    return user_router


# Экспортируем основной роутер для обратной совместимости
user_router = setup_user_handlers()

__all__ = ['user_router', 'setup_user_handlers']