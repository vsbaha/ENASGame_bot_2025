"""
Главный модуль управления турнирами - координирует все подмодули
"""
import logging
from aiogram import Router

# Импортируем все подмодули
from . import tournament_management
from . import tournament_creation  
from . import tournament_editing
from . import tournament_statistics
from . import tournament_dates
from . import tournament_rules
from . import tournament_logo

# Создаем основной роутер и включаем все подроутеры
router = Router()
router.include_router(tournament_management.router)
router.include_router(tournament_creation.router)
router.include_router(tournament_editing.router) 
router.include_router(tournament_statistics.router)
router.include_router(tournament_dates.router)
router.include_router(tournament_rules.router)
router.include_router(tournament_logo.router)

logger = logging.getLogger(__name__)

# Экспортируем все необходимые компоненты для обратной совместимости
__all__ = ['router']