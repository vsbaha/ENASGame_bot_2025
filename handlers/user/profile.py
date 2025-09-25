"""
Обработчики профиля и настроек пользователя
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database.repositories.user_repository import UserRepository
from utils.localization import Localization
from utils.message_utils import safe_edit_message
from utils.keyboards import (
    get_language_keyboard,
    get_region_keyboard,
    get_profile_keyboard
)
from .states import UserStates

# Создаем роутер для профиля
profile_router = Router()


@profile_router.callback_query(F.data == "menu:profile", StateFilter(UserStates.main_menu))
async def show_profile(callback: CallbackQuery):
    """Показать профиль пользователя"""
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    localization = Localization()
    localization.set_language(user.language)
    
    # Формируем информацию о профиле
    profile_text = localization.get_text("profile.your_profile") + "\n\n"
    profile_text += localization.get_text("profile.user_id", id=user.id) + "\n"
    
    if user.username:
        profile_text += localization.get_text("profile.username", username=user.username) + "\n"
    
    # Отображаем регион
    region_name = localization.get_text(f"regions.{user.region}")
    
    profile_text += localization.get_text("profile.region", region=region_name) + "\n"
    profile_text += localization.get_text("profile.registered", date=user.created_at.strftime("%d.%m.%Y"))
    
    await safe_edit_message(
        callback.message,
        profile_text,
        reply_markup=get_profile_keyboard(localization)
    )


@profile_router.callback_query(F.data == "profile:change_language", StateFilter(UserStates.main_menu))
async def change_language_from_profile(callback: CallbackQuery, state: FSMContext):
    """Смена языка из профиля"""
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    localization = Localization()
    localization.set_language(user.language)
    
    text = localization.get_text("start.choose_language")
    
    await safe_edit_message(
        callback.message,
        text,
        reply_markup=get_language_keyboard()
    )
    
    await state.set_state(UserStates.selecting_language_from_profile)


@profile_router.callback_query(F.data == "profile:change_region", StateFilter(UserStates.main_menu))
async def change_region_from_profile(callback: CallbackQuery, state: FSMContext):
    """Смена региона из профиля"""
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    localization = Localization()
    localization.set_language(user.language)
    
    text = localization.get_text("start.choose_region")
    
    await safe_edit_message(
        callback.message,
        text,
        reply_markup=get_region_keyboard()
    )
    
    await state.set_state(UserStates.selecting_region_from_profile)


@profile_router.callback_query(F.data.startswith("lang:"), StateFilter(UserStates.selecting_language_from_profile))
async def process_language_change_from_profile(callback: CallbackQuery, state: FSMContext):
    """Обработка смены языка из профиля"""
    language = callback.data.split(":")[1]
    
    # Обновляем язык пользователя в базе данных
    await UserRepository.update_language(callback.from_user.id, language)
    
    # Обновляем локализацию
    localization = Localization()
    localization.set_language(language)
    
    # Возвращаемся к профилю с обновленным языком
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    # Формируем информацию о профиле
    profile_text = localization.get_text("profile.your_profile") + "\n\n"
    profile_text += localization.get_text("profile.user_id", id=user.id) + "\n"
    
    if user.username:
        profile_text += localization.get_text("profile.username", username=user.username) + "\n"
    
    # Отображаем регион
    region_name = localization.get_text(f"regions.{user.region}")
    profile_text += localization.get_text("profile.region", region=region_name) + "\n"
    profile_text += localization.get_text("profile.registered", date=user.created_at.strftime("%d.%m.%Y"))
    
    await safe_edit_message(
        callback.message,
        profile_text,
        reply_markup=get_profile_keyboard(localization)
    )
    await state.set_state(UserStates.main_menu)


@profile_router.callback_query(F.data.startswith("region:"), StateFilter(UserStates.selecting_region_from_profile))
async def process_region_change_from_profile(callback: CallbackQuery, state: FSMContext):
    """Обработка смены региона из профиля"""
    region = callback.data.split(":")[1]
    
    # Обновляем регион пользователя в базе данных
    await UserRepository.update_region(callback.from_user.id, region)
    
    # Получаем пользователя с обновленными данными
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    localization = Localization()
    localization.set_language(user.language)
    
    # Формируем информацию о профиле
    profile_text = localization.get_text("profile.your_profile") + "\n\n"
    profile_text += localization.get_text("profile.user_id", id=user.id) + "\n"
    
    if user.username:
        profile_text += localization.get_text("profile.username", username=user.username) + "\n"
    
    # Отображаем обновленный регион
    region_name = localization.get_text(f"regions.{user.region}")
    profile_text += localization.get_text("profile.region", region=region_name) + "\n"
    profile_text += localization.get_text("profile.registered", date=user.created_at.strftime("%d.%m.%Y"))
    
    await safe_edit_message(
        callback.message,
        profile_text,
        reply_markup=get_profile_keyboard(localization)
    )
    await state.set_state(UserStates.main_menu)