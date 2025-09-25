"""
Обработчики навигации и общие функции
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.repositories.user_repository import UserRepository
from utils.localization import Localization
from utils.message_utils import safe_edit_message
from utils.keyboards import get_main_menu_keyboard
from .states import UserStates

# Создаем роутер для навигации
navigation_router = Router()


@navigation_router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    localization = Localization()
    localization.set_language(user.language)
    
    menu_text = localization.get_text("start.welcome")
    await safe_edit_message(
        callback.message,
        menu_text,
        reply_markup=get_main_menu_keyboard(localization)
    )
    await state.set_state(UserStates.main_menu)


@navigation_router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню (из админки)"""
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    localization = Localization()
    localization.set_language(user.language)
    
    menu_text = localization.get_text("start.welcome")
    await safe_edit_message(
        callback.message,
        menu_text,
        reply_markup=get_main_menu_keyboard(localization)
    )
    await state.set_state(UserStates.main_menu)
    await callback.answer()


@navigation_router.message(~F.text.startswith('/'))
async def unknown_message(message: Message):
    """Обработка неизвестных сообщений (не команд)"""
    user = await UserRepository.get_by_telegram_id(message.from_user.id)
    
    if user:
        localization = Localization()
        localization.set_language(user.language)
        error_text = localization.get_text("errors.unknown_command")
    else:
        error_text = "❓ Я не понимаю эту команду. Используйте /start для начала работы."
    
    await message.answer(error_text)