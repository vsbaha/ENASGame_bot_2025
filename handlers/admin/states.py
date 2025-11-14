"""
Состояния для админских хендлеров
"""
from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Состояния для админских операций"""
    # Создание турнира
    creating_tournament_name = State()
    creating_tournament_description = State()
    creating_tournament_logo = State()
    creating_tournament_game = State()
    creating_tournament_format = State()
    creating_tournament_max_teams = State()
    creating_tournament_registration_start = State()
    creating_tournament_registration_end = State()
    creating_tournament_start_date = State()
    creating_tournament_rules = State()
    creating_tournament_rules_file = State()
    creating_tournament_required_channels = State()  # Новое состояние
    creating_tournament_confirmation = State()
    confirming_tournament_creation = State()
    
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
    
    # Управление играми
    adding_game_name = State()
    adding_game_max_players = State()
    adding_game_max_substitutes = State()
    adding_game_icon = State()
    editing_game = State()
    editing_game_name = State()
    editing_game_short_name = State()
    editing_game_max_players = State()
    editing_game_max_substitutes = State()
    editing_game_icon = State()
    
    # Редактирование турнира
    editing_tournament_name = State()
    editing_tournament_description = State()
    editing_tournament_logo = State()
    editing_tournament_game = State()
    editing_tournament_format = State()
    editing_tournament_max_teams = State()
    editing_tournament_registration_start = State()
    editing_tournament_registration_end = State()
    editing_tournament_start_date = State()
    editing_tournament_rules = State()
    editing_tournament_rules_file = State()
    editing_tournament_required_channels = State()  # Новое состояние
    
    # Управление форматами
    editing_format_settings = State()
    adding_custom_format = State()
    
    # Управление матчами
    entering_match_score = State()
    entering_team1_score = State()
    entering_team2_score = State()
    confirming_match_result = State()
    editing_match_details = State()