"""
Основные админские хендлеры
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from database.repositories import UserRepository
from utils.message_utils import safe_edit_message, safe_answer_or_edit
from .states import AdminStates
from .keyboards import get_admin_main_keyboard

router = Router()
logger = logging.getLogger(__name__)

async def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    try:
        
        user = await UserRepository.get_by_telegram_id(user_id)
        if not user:
            return False
        from database.models import UserRole
        return user.role == UserRole.ADMIN.value
    except Exception as e:
        logger.error(f"Ошибка проверки прав администратора: {e}")
        return False

@router.message(Command("admin"))
async def admin_panel_command(message: Message, state: FSMContext):
    """Команда входа в админ-панель"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа к админ-панели", parse_mode="Markdown")
        return
    
    await state.clear()
    
    try:
        # Получаем статистику
        from database.repositories import TournamentRepository, TeamRepository
        
        users_count = await UserRepository.get_total_count()
        tournaments_count = await TournamentRepository.get_total_count()
        teams_count = await TeamRepository.get_total_count()
        
        text = f"""🛡️ Панель администратора

Добро пожаловать в админ-панель!
Выберите раздел для управления:

👥 Пользователей: {users_count}
🏆 Турниров: {tournaments_count}
👥 Команд: {teams_count}
"""
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        text = """🛡️ Панель администратора

Добро пожаловать в админ-панель!
Выберите раздел для управления:

👥 Пользователей: —
🏆 Турниров: —
👥 Команд: —
"""
    
    await message.answer(
        text, 
        reply_markup=get_admin_main_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin:main")
async def admin_main_menu(callback: CallbackQuery, state: FSMContext):
    """Главное меню администратора"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа")
        return
    
    await state.clear()
    
    try:
        # Получаем статистику
        from database.repositories import TournamentRepository, TeamRepository
        
        users_count = await UserRepository.get_total_count()
        tournaments_count = await TournamentRepository.get_total_count()
        teams_count = await TeamRepository.get_total_count()
        
        text = f"""🛡️ Панель администратора

Добро пожаловать в админ-панель!
Выберите раздел для управления:

👥 Пользователей: {users_count}
🏆 Турниров: {tournaments_count}
👥 Команд: {teams_count}
"""
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        text = """🛡️ Панель администратора

Добро пожаловать в админ-панель!
Выберите раздел для управления:

👥 Пользователей: —
🏆 Турниров: —
👥 Команд: —
"""
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_admin_main_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()