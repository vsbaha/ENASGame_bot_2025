"""
Клавиатуры для админских хендлеров
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню администратора"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="🏆 Управление турнирами",
                callback_data="admin:tournaments"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Модерация команд",
                callback_data="admin:teams"
            )
        ],
        [
            InlineKeyboardButton(
                text="👤 Управление пользователями",
                callback_data="admin:users"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Статистика",
                callback_data="admin:statistics"
            )
        ],
        [
            InlineKeyboardButton(
                text="📢 Рассылка",
                callback_data="admin:broadcast"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад в главное меню",
                callback_data="main_menu"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_tournament_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления турнирами"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="➕ Создать турнир",
                callback_data="admin:create_tournament"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Настройки турниров",
                callback_data="admin:tournament_settings"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎮 Добавить игру",
                callback_data="admin:add_game"
            ),
            InlineKeyboardButton(
                text="📋 Список игр",
                callback_data="admin:list_games"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏆 Управление форматами",
                callback_data="admin:manage_formats"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад в админ меню",
                callback_data="admin:main"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_team_moderation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура модерации команд"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="📋 Заявки на регистрацию",
                callback_data="admin:team_applications"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Активные команды",
                callback_data="admin:active_teams"
            )
        ],
        [
            InlineKeyboardButton(
                text="🚫 Заблокированные команды",
                callback_data="admin:blocked_teams"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔍 Поиск команды",
                callback_data="admin:search_team"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад в админ меню",
                callback_data="admin:main"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_team_action_keyboard(team_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с командой"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Одобрить",
                callback_data=f"admin:approve_team_{team_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"admin:reject_team_{team_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Редактировать",
                callback_data=f"admin:edit_team_{team_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🚫 Заблокировать",
                callback_data=f"admin:block_team_{team_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="admin:teams"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_user_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления пользователями"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="👤 Поиск пользователя",
                callback_data="admin:search_user"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Список пользователей",
                callback_data="admin:list_users"
            )
        ],
        [
            InlineKeyboardButton(
                text="👑 Администраторы",
                callback_data="admin:list_admins"
            )
        ],
        [
            InlineKeyboardButton(
                text="🚫 Заблокированные",
                callback_data="admin:blocked_users"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад в админ меню",
                callback_data="admin:main"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_user_action_keyboard(user_id: int, language: str = "ru", user_data: dict = None) -> InlineKeyboardMarkup:
    """Клавиатура действий с пользователем"""
    keyboard = []
    
    if user_data:
        is_admin = user_data.get('is_admin', False)
        is_blocked = user_data.get('is_blocked', False)
        
        # Админских функций (только если пользователь не заблокирован)
        if not is_blocked:
            if is_admin:
                # Если уже админ, показываем кнопку убрать админа
                keyboard.append([
                    InlineKeyboardButton(
                        text="👤 Убрать админа",
                        callback_data=f"admin:remove_admin_{user_id}"
                    )
                ])
            else:
                # Если обычный пользователь, показываем кнопку сделать админом
                keyboard.append([
                    InlineKeyboardButton(
                        text="👑 Сделать админом",
                        callback_data=f"admin:make_admin_{user_id}"
                    )
                ])
        
        # Блокировка (админов заблокировать нельзя)
        if not is_admin:
            if is_blocked:
                # Если заблокирован, показываем разблокировать
                keyboard.append([
                    InlineKeyboardButton(
                        text="✅ Разблокировать",
                        callback_data=f"admin:unblock_user_{user_id}"
                    )
                ])
            else:
                # Если активен, показываем заблокировать
                keyboard.append([
                    InlineKeyboardButton(
                        text="🚫 Заблокировать",
                        callback_data=f"admin:block_user_{user_id}"
                    )
                ])
    
    # Кнопка назад всегда есть
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="admin:users"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_statistics_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура статистики"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="📊 Общая статистика",
                callback_data="admin:general_stats"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏆 Турниры",
                callback_data="admin:tournament_stats"
            ),
            InlineKeyboardButton(
                text="👥 Команды",
                callback_data="admin:team_stats"
            )
        ],
        [
            InlineKeyboardButton(
                text="👤 Пользователи",
                callback_data="admin:user_stats"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Экспорт данных",
                callback_data="admin:export_data"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад в админ-панель",
                callback_data="admin:main"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для рассылки"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="📨 Всем пользователям",
                callback_data="admin:broadcast_all"
            )
        ],
        [
            InlineKeyboardButton(
                text="👑 Капитанам команд",
                callback_data="admin:broadcast_team_captains"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏆 Участникам турниров",
                callback_data="admin:broadcast_tournament_users"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎯 Выборочная рассылка",
                callback_data="admin:broadcast_selective"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад в админ-панель",
                callback_data="admin:main"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirmation_keyboard(action: str = "confirm") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действий"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"admin:confirm_{action}"
            ),
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data=f"admin:cancel_{action}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_selective_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выборочной рассылки"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="🆔 По списку ID",
                callback_data="admin:selective_by_ids"
            )
        ],
        [
            InlineKeyboardButton(
                text="🌍 По языку",
                callback_data="admin:selective_by_language"
            )
        ],
        [
            InlineKeyboardButton(
                text="🌍 По региону",
                callback_data="admin:selective_by_region"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к рассылке",
                callback_data="admin:broadcast"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_language_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора языка"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="🇷🇺 Русский",
                callback_data="admin:broadcast_lang_ru"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇰🇬 Кыргызча",
                callback_data="admin:broadcast_lang_ky"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇰🇿 Қазақша",
                callback_data="admin:broadcast_lang_kk"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к выборочной рассылке",
                callback_data="admin:broadcast_selective"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_region_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора региона"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="🇷🇺 Россия",
                callback_data="admin:broadcast_region_ru"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇰🇬 Кыргызстан",
                callback_data="admin:broadcast_region_kg"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇰🇿 Казахстан",
                callback_data="admin:broadcast_region_kz"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к выборочной рассылке",
                callback_data="admin:broadcast_selective"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_broadcast_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для возврата при создании рассылки"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="admin:broadcast"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_tournament_settings_keyboard(tournaments=None) -> InlineKeyboardMarkup:
    """Клавиатура настроек турниров с динамическим списком"""
    keyboard = []
    
    # Добавляем турниры в список кнопок
    if tournaments:
        for tournament in tournaments[:8]:  # Максимум 8 турниров чтобы поместились
            status_emoji = {
                'registration': '📝',
                'in_progress': '🏃',
                'completed': '✅',
                'cancelled': '❌'
            }.get(tournament.status, '❓')
            
            # Ограничиваем название до 25 символов
            name = tournament.name[:25] + "..." if len(tournament.name) > 25 else tournament.name
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} {name}",
                    callback_data=f"admin:manage_tournament_{tournament.id}"
                )
            ])
    
    # Кнопка назад
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад к турнирам",
            callback_data="admin:tournaments"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_tournament_action_keyboard(tournament_id: int, tournament_status: str) -> InlineKeyboardMarkup:
    """Клавиатура действий с конкретным турниром"""
    keyboard = []
    
    # Кнопки управления в зависимости от статуса
    if tournament_status == 'registration':
        keyboard.append([
            InlineKeyboardButton(
                text="🏁 Запустить турнир",
                callback_data=f"admin:start_tournament_{tournament_id}"
            )
        ])
    elif tournament_status == 'in_progress':
        keyboard.append([
            InlineKeyboardButton(
                text="⏸️ Приостановить",
                callback_data=f"admin:pause_tournament_{tournament_id}"
            )
        ])
    elif tournament_status == 'paused':
        keyboard.append([
            InlineKeyboardButton(
                text="▶️ Продолжить",
                callback_data=f"admin:resume_tournament_{tournament_id}"
            )
        ])
    
    # Генерация сетки (только для регистрации)
    if tournament_status == 'registration':
        keyboard.append([
            InlineKeyboardButton(
                text="🎯 Генерация сетки",
                callback_data=f"admin:generate_bracket_{tournament_id}"
            )
        ])
    
    # Управление матчами (только для активных турниров)
    if tournament_status in ['in_progress', 'paused']:
        keyboard.append([
            InlineKeyboardButton(
                text="🎮 Управление матчами",
                callback_data=f"admin:manage_matches_{tournament_id}"
            )
        ])
    
    # Всегда доступные действия
    keyboard.extend([
        [
            InlineKeyboardButton(
                text="📄 Получить регламент",
                callback_data=f"admin:get_tournament_rules_{tournament_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Редактировать",
                callback_data=f"admin:edit_tournament_details_{tournament_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Удалить турнир",
                callback_data=f"admin:confirm_delete_tournament_{tournament_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Статистика турнира",
                callback_data=f"admin:tournament_detailed_stats_{tournament_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к настройкам",
                callback_data="admin:tournament_settings"
            )
        ]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_game_selection_keyboard(games) -> InlineKeyboardMarkup:
    """Клавиатура выбора игры для турнира"""
    keyboard = []
    
    for game in games:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🎮 {game.name}",
                callback_data=f"select_game_{game.id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="admin:tournaments"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_tournament_format_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора формата турнира"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="🏆 Одиночное исключение",
                callback_data="format_single_elimination"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏆🏆 Двойное исключение", 
                callback_data="format_double_elimination"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Круговая система",
                callback_data="format_round_robin"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎯 Швейцарская система",
                callback_data="format_swiss"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="admin:tournaments"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirm_tournament_creation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения создания турнира"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Создать турнир",
                callback_data="confirm_create_tournament"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="cancel_create_tournament"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)