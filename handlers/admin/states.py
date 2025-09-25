"""
Состояния для админских хендлеров
"""
from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Состояния для админских операций"""
    # Создание турнира
    creating_tournament_name = State()
    creating_tournament_description = State()
    creating_tournament_game = State()
    creating_tournament_format = State()
    creating_tournament_max_teams = State()
    creating_tournament_registration_start = State()
    creating_tournament_registration_end = State()
    creating_tournament_start_date = State()
    creating_tournament_rules = State()
    creating_tournament_confirmation = State()
    
    # Управление турниром
    selecting_tournament_to_manage = State()
    editing_tournament_name = State()
    editing_tournament_description = State()
    editing_tournament_settings = State()
    
    # Модерация команд
    moderating_team = State()
    reviewing_team_application = State()
    rejecting_team = State()
    blocking_team = State()
    searching_team = State()
    
    # Управление пользователями
    selecting_user_to_manage = State()
    viewing_user_details = State()
    editing_user_role = State()
    
    # Статистика
    generating_report = State()
    selecting_report_period = State()
    
    # Рассылка сообщений
    creating_broadcast_message = State()
    broadcast_adding_attachment = State()
    selecting_broadcast_target = State()
    confirming_broadcast = State()
    
    # Выборочная рассылка
    selective_broadcast_choosing_criteria = State()
    selective_broadcast_entering_ids = State()
    selective_broadcast_choosing_language = State()
    selective_broadcast_choosing_region = State()
    selective_broadcast_entering_message = State()
    selective_broadcast_adding_attachment = State()