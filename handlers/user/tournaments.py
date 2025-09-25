"""
Обработчики турниров
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter

from database.repositories.user_repository import UserRepository
from database.repositories.tournament_repository import TournamentRepository
from utils.localization import Localization
from utils.message_utils import safe_edit_message
from utils.keyboards import get_tournaments_keyboard, get_back_keyboard
from .states import UserStates

# Создаем роутер для турниров
tournaments_router = Router()


@tournaments_router.callback_query(F.data == "menu:tournaments", StateFilter(UserStates.main_menu))
async def show_tournaments(callback: CallbackQuery):
    """Показать список турниров"""
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    localization = Localization()
    localization.set_language(user.language)
    
    # Получаем активные турниры для региона пользователя
    tournaments = await TournamentRepository.get_active_tournaments(user.region)
    
    if not tournaments:
        no_tournaments_text = localization.get_text("tournaments.no_active")
        await safe_edit_message(
            callback.message,
            no_tournaments_text,
            reply_markup=get_back_keyboard(localization)
        )
        return
    
    # Формируем список турниров
    tournaments_text = localization.get_text("tournaments.active_tournaments") + "\n\n"
    
    for tournament in tournaments:
        tournaments_text += f"🏆 **{tournament.name}**\n"
        tournaments_text += f"🎮 {tournament.game.name}\n"
        
        if tournament.registration_open:
            tournaments_text += localization.get_text("tournaments.registration_open") + "\n"
        
        tournaments_text += localization.get_text(
            "tournaments.max_teams", 
            count=tournament.max_teams
        ) + "\n"
        
        # Считаем зарегистрированные команды
        registered_count = len(tournament.teams)
        tournaments_text += localization.get_text(
            "tournaments.registered_teams",
            count=registered_count
        ) + "\n\n"
    
    await safe_edit_message(
        callback.message,
        tournaments_text,
        reply_markup=get_tournaments_keyboard(tournaments, localization),
        parse_mode="Markdown"
    )