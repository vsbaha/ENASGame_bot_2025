"""
Инициализация админских хендлеров
"""
from aiogram import Router


def setup_admin_handlers() -> Router:
    """Настройка всех админских роутеров"""
    admin_router = Router()
    
    # Импортируем и добавляем роутеры по одному
    from .main import router as admin_main_router
    admin_router.include_router(admin_main_router)
    
    from .tournaments import router as admin_tournaments_router
    admin_router.include_router(admin_tournaments_router)
    
    from .teams import router as admin_teams_router
    admin_router.include_router(admin_teams_router)
    
    from .users import router as admin_users_router
    admin_router.include_router(admin_users_router)
    
    from .statistics import router as admin_statistics_router
    admin_router.include_router(admin_statistics_router)
    
    from .broadcast import router as admin_broadcast_router
    admin_router.include_router(admin_broadcast_router)
    
    return admin_router