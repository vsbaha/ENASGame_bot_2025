"""
Обработчики регистрации и выбора языка/региона
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from database.repositories.user_repository import UserRepository
from utils.localization import Localization
from utils.message_utils import safe_edit_message
from utils.keyboards import (
    get_language_keyboard,
    get_region_keyboard,
    get_main_menu_keyboard
)
from settings import config
from .states import UserStates

# Создаем роутер для регистрации
registration_router = Router()


@registration_router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user = await UserRepository.get_by_telegram_id(message.from_user.id)
    
    # Инициализируем локализацию
    localization = Localization()
    
    if not user:
        # Новый пользователь - создаем с настройками по умолчанию
        # TODO: В будущем вернуть выбор языка - пока только русский
        user = await UserRepository.create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip(),
            language="ru",  # Временно захардкожен русский
            region=config.DEFAULT_REGION
        )
        
        # Устанавливаем язык для текущей сессии
        localization.set_language(user.language)
        
        # Приветствуем нового пользователя и сразу показываем главное меню
        welcome_text = localization.get_text("start.welcome")
        
        await message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(localization)
        )
        await state.set_state(UserStates.main_menu)
    else:
        # Существующий пользователь - показываем главное меню
        localization.set_language(user.language)
        
        welcome_text = localization.get_text("start.welcome")
        await message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(localization)
        )
        await state.set_state(UserStates.main_menu)


@registration_router.callback_query(F.data.startswith("lang:"), StateFilter(UserStates.choosing_language))
async def process_language_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора языка"""
    language = callback.data.split(":")[1]
    
    # Обновляем язык пользователя в базе данных
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    if user:
        await UserRepository.update_language(callback.from_user.id, language)
    
    # Обновляем локализацию
    localization = Localization()
    localization.set_language(language)
    
    # Показываем выбор региона
    region_text = localization.get_text("start.choose_region")
    await safe_edit_message(
        callback.message,
        region_text,
        reply_markup=get_region_keyboard()
    )
    await state.set_state(UserStates.choosing_region)


@registration_router.callback_query(F.data.startswith("region:"), StateFilter(UserStates.choosing_region))
async def process_region_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора региона"""
    region = callback.data.split(":")[1]
    
    # Обновляем регион пользователя в базе данных
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    if user:
        await UserRepository.update_region(callback.from_user.id, region)
    
    # Обновляем локализацию
    localization = Localization()
    localization.set_language(user.language)
    
    # Завершаем настройку
    setup_complete_text = localization.get_text("start.setup_complete")
    await safe_edit_message(callback.message, setup_complete_text)
    
    # Показываем главное меню
    await callback.message.answer(
        localization.get_text("menu.tournaments"),
        reply_markup=get_main_menu_keyboard(localization)
    )
    await state.set_state(UserStates.main_menu)