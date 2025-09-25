"""
Обработчики поддержки
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter

from database.repositories.user_repository import UserRepository
from utils.localization import Localization
from utils.message_utils import safe_edit_message
from utils.keyboards import get_back_keyboard
from .states import UserStates

# Создаем роутер для поддержки
support_router = Router()


@support_router.callback_query(F.data == "menu:support", StateFilter(UserStates.main_menu))
async def show_support(callback: CallbackQuery):
    """Показать информацию о поддержке"""
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    localization = Localization()
    localization.set_language(user.language)
    
    support_text = (
        "🆘 **Поддержка**\n\n"
        "Если у вас возникли вопросы или проблемы:\n\n"
        "• Напишите администратору: @EnasSupport\n"
    )
    
    await safe_edit_message(
        callback.message,
        support_text,
        reply_markup=get_back_keyboard(localization),
        parse_mode="Markdown"
    )