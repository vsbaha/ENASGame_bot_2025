"""
Клавиатуры для Telegram бота турниров
"""

from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.localization import Localization


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка"""
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки для каждого поддерживаемого языка
    builder.button(text="🇷🇺 Русский", callback_data="lang:ru")
    builder.button(text="🇰🇬 Кыргызча", callback_data="lang:ky")
    builder.button(text="🇰🇿 Қазақша", callback_data="lang:kk")
    
    builder.adjust(1)
    return builder.as_markup()


def get_region_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора региона"""
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки для каждого поддерживаемого региона
    builder.button(text="🇰🇬 Кыргызстан", callback_data="region:kg")
    builder.button(text="🇰🇿 Казахстан", callback_data="region:kz")
    builder.button(text="🇷🇺 Россия", callback_data="region:ru")
    
    builder.adjust(1)
    return builder.as_markup()


def get_main_menu_keyboard(localization: Localization) -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    
    tournaments_text = localization.get_text("menu.tournaments")
    my_teams_text = localization.get_text("menu.my_teams")
    profile_text = localization.get_text("menu.profile")
    support_text = localization.get_text("menu.support")
    
    builder.button(text=tournaments_text, callback_data="menu:tournaments")
    builder.button(text=my_teams_text, callback_data="menu:my_teams")
    builder.button(text=profile_text, callback_data="menu:profile")
    builder.button(text=support_text, callback_data="menu:support")
    
    builder.adjust(2, 2)
    return builder.as_markup()


def get_tournaments_keyboard(tournaments: List, localization: Localization) -> InlineKeyboardMarkup:
    """Клавиатура со списком турниров"""
    builder = InlineKeyboardBuilder()
    
    for tournament in tournaments:
        builder.button(
            text=f"🏆 {tournament.name}",
            callback_data=f"tournament:{tournament.id}"
        )
    
    back_text = localization.get_text("buttons.back")
    builder.button(text=back_text, callback_data="back_to_menu")
    
    builder.adjust(1)
    return builder.as_markup()


def get_tournament_details_keyboard(tournament_id: int, localization: Localization) -> InlineKeyboardMarkup:
    """Клавиатура действий с турниром"""
    builder = InlineKeyboardBuilder()
    
    view_details_text = localization.get_text("tournaments.view_details")
    register_team_text = localization.get_text("tournaments.register_team")
    back_text = localization.get_text("buttons.back")
    
    builder.button(
        text=view_details_text,
        callback_data=f"tournament_details:{tournament_id}"
    )
    builder.button(
        text=register_team_text,
        callback_data=f"register_team:{tournament_id}"
    )
    builder.button(text=back_text, callback_data="menu:tournaments")
    
    builder.adjust(1)
    return builder.as_markup()


def get_back_keyboard(localization: Localization) -> InlineKeyboardMarkup:
    """Простая кнопка Назад"""
    builder = InlineKeyboardBuilder()
    
    back_text = localization.get_text("buttons.back")
    builder.button(text=back_text, callback_data="back_to_menu")
    
    return builder.as_markup()


def get_confirm_cancel_keyboard(localization: Localization, confirm_data: str = "confirm", cancel_data: str = "cancel") -> InlineKeyboardMarkup:
    """Кнопки Подтвердить и Отмена"""
    builder = InlineKeyboardBuilder()
    
    confirm_text = localization.get_text("buttons.confirm")
    cancel_text = localization.get_text("buttons.cancel")
    
    builder.button(text=confirm_text, callback_data=confirm_data)
    builder.button(text=cancel_text, callback_data=cancel_data)
    
    builder.adjust(2)
    return builder.as_markup()


def get_yes_no_keyboard(localization: Localization, yes_data: str = "yes", no_data: str = "no") -> InlineKeyboardMarkup:
    """Кнопки Да и Нет"""
    builder = InlineKeyboardBuilder()
    
    yes_text = localization.get_text("buttons.yes")
    no_text = localization.get_text("buttons.no")
    
    builder.button(text=yes_text, callback_data=yes_data)
    builder.button(text=no_text, callback_data=no_data)
    
    builder.adjust(2)
    return builder.as_markup()


def get_team_management_keyboard(team_id: int, localization: Localization) -> InlineKeyboardMarkup:
    """Клавиатура управления командой"""
    builder = InlineKeyboardBuilder()
    
    view_text = localization.get_text("my_teams.view_team")
    edit_text = localization.get_text("my_teams.edit_team")
    delete_text = localization.get_text("my_teams.delete_team")
    back_text = localization.get_text("buttons.back")
    
    builder.button(text=view_text, callback_data=f"view_team:{team_id}")
    builder.button(text=edit_text, callback_data=f"edit_team:{team_id}")
    builder.button(text=delete_text, callback_data=f"delete_team:{team_id}")
    builder.button(text=back_text, callback_data="menu:my_teams")
    
    builder.adjust(1)
    return builder.as_markup()


def get_admin_menu_keyboard(localization: Localization) -> InlineKeyboardMarkup:
    """Админское меню"""
    builder = InlineKeyboardBuilder()
    
    create_tournament_text = localization.get_text("admin.create_tournament")
    manage_tournaments_text = localization.get_text("admin.manage_tournaments")
    moderate_teams_text = localization.get_text("admin.moderate_teams")
    manage_users_text = localization.get_text("admin.manage_users")
    statistics_text = localization.get_text("admin.statistics")
    back_text = localization.get_text("buttons.back")
    
    builder.button(text=create_tournament_text, callback_data="admin:create_tournament")
    builder.button(text=manage_tournaments_text, callback_data="admin:manage_tournaments")
    builder.button(text=moderate_teams_text, callback_data="admin:moderate_teams")
    builder.button(text=manage_users_text, callback_data="admin:manage_users")
    builder.button(text=statistics_text, callback_data="admin:statistics")
    builder.button(text=back_text, callback_data="back_to_menu")
    
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def get_moderation_keyboard(team_id: int, localization: Localization) -> InlineKeyboardMarkup:
    """Клавиатура модерации команды"""
    builder = InlineKeyboardBuilder()
    
    approve_text = localization.get_text("buttons.approve")
    reject_text = localization.get_text("buttons.reject")
    back_text = localization.get_text("buttons.back")
    
    builder.button(text=approve_text, callback_data=f"approve_team:{team_id}")
    builder.button(text=reject_text, callback_data=f"reject_team:{team_id}")
    builder.button(text=back_text, callback_data="admin:moderate_teams")
    
    builder.adjust(2, 1)
    return builder.as_markup()


def get_profile_keyboard(localization: Localization) -> InlineKeyboardMarkup:
    """Клавиатура для профиля с кнопками смены языка и региона"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки для смены языка и региона
    change_language_text = localization.get_text("profile.change_language")
    change_region_text = localization.get_text("profile.change_region")
    back_text = localization.get_text("buttons.back")
    
    builder.button(text=change_language_text, callback_data="profile:change_language")
    builder.button(text=change_region_text, callback_data="profile:change_region")
    builder.button(text=back_text, callback_data="back_to_menu")
    
    builder.adjust(2, 1)  # 2 кнопки в первом ряду, 1 во втором
    return builder.as_markup()