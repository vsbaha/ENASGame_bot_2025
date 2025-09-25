"""
Обработчики команд пользователя
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter

from database.repositories.user_repository import UserRepository
from database.repositories.team_repository import TeamRepository
from utils.localization import Localization
from utils.message_utils import safe_edit_message
from utils.keyboards import get_back_keyboard
from .states import UserStates

# Создаем роутер для команд
teams_router = Router()


@teams_router.callback_query(F.data == "menu:my_teams", StateFilter(UserStates.main_menu))
async def show_my_teams(callback: CallbackQuery):
    """Показать мои команды"""
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    localization = Localization()
    localization.set_language(user.language)
    
    # Получаем команды пользователя
    teams = await TeamRepository.get_teams_by_captain(user.id)
    
    if not teams:
        no_teams_text = localization.get_text("my_teams.no_teams")
        await safe_edit_message(
            callback.message,
            no_teams_text,
            reply_markup=get_back_keyboard(localization)
        )
        return
    
    # Формируем список команд
    teams_text = localization.get_text("my_teams.title") + "\n\n"
    
    for team in teams:
        teams_text += f"👥 **{team.name}**\n"
        teams_text += f"🏆 {team.tournament.name}\n"
        
        # Статус команды
        if team.status == "pending":
            status_text = localization.get_text("my_teams.team_status_pending")
        elif team.status == "approved":
            status_text = localization.get_text("my_teams.team_status_approved")
        else:
            status_text = localization.get_text("my_teams.team_status_rejected")
        
        teams_text += f"📊 {status_text}\n\n"
    
    await safe_edit_message(
        callback.message,
        teams_text,
        reply_markup=get_back_keyboard(localization),
        parse_mode="Markdown"
    )