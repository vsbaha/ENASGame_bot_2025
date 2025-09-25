"""
Общие состояния для пользовательских хендлеров
"""

from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """Состояния пользователя"""
    choosing_language = State()
    choosing_region = State()
    main_menu = State()
    selecting_language_from_profile = State()
    selecting_region_from_profile = State()