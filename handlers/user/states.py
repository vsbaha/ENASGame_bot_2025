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
    
    # Регистрация команды
    registering_team_selecting_tournament = State()
    registering_team_entering_name = State()
    registering_team_uploading_logo = State()
    registering_team_adding_main_players = State()
    registering_team_adding_substitutes = State()
    registering_team_confirmation = State()
    
    # Редактирование игрока
    editing_player_nickname = State()
    editing_player_game_id = State()
    
    # Просмотр команд
    viewing_team = State()
    viewing_team_list = State()