"""
Хендлеры для управления турнирами
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database.repositories import UserRepository, TournamentRepository
from utils.message_utils import safe_edit_message
from .states import AdminStates
from .keyboards import get_tournament_management_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "admin:tournaments")
async def tournament_management_menu(callback: CallbackQuery, state: FSMContext):
    """Меню управления турнирами"""
    await state.clear()
    
    # Получаем статистику турниров
    try:
        total_tournaments = await TournamentRepository.get_total_count()
        active_tournaments = await TournamentRepository.get_active_count()
    except Exception as e:
        logger.error(f"Ошибка получения статистики турниров: {e}")
        total_tournaments = 0
        active_tournaments = 0
    
    text = f"""🏆 Управление турнирами

📊 Статистика:
📋 Всего турниров: {total_tournaments}
🏃 Активных: {active_tournaments}

Выберите действие:"""
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=get_tournament_management_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:create_tournament")
async def start_tournament_creation(callback: CallbackQuery, state: FSMContext):
    """Начало создания турнира - запрос названия"""
    await state.clear()
    
    text = """➕ Создание турнира

📝 **Шаг 1 из 8: Название турнира**

Введите название турнира:

▪️ Минимум 3 символа
▪️ Максимум 100 символов
▪️ Избегайте специальных символов

**Пример:** Championship 2025"""
    
    # Создаем кнопку отмены
    keyboard = [[
        InlineKeyboardButton(
            text="❌ Отменить создание",
            callback_data="admin:cancel_tournament_creation"
        )
    ]]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_name)
    await callback.answer()


@router.callback_query(F.data == "admin:cancel_tournament_creation")
async def cancel_tournament_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания турнира"""
    await state.clear()
    
    text = """❌ Создание турнира отменено

Возвращаемся в меню управления турнирами."""
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=get_tournament_management_keyboard()
    )
    await callback.answer()


def validate_tournament_name(name: str) -> tuple[bool, str]:
    """Валидация названия турнира"""
    if not name or not name.strip():
        return False, "❌ Название не может быть пустым"
    
    name = name.strip()
    
    if len(name) < 3:
        return False, "❌ Название слишком короткое (минимум 3 символа)"
    
    if len(name) > 100:
        return False, "❌ Название слишком длинное (максимум 100 символов)"
    
    # Проверяем на запрещенные символы
    forbidden_chars = ['<', '>', '&', '"', "'", '`']
    for char in forbidden_chars:
        if char in name:
            return False, f"❌ Символ '{char}' запрещен в названии"
    
    return True, ""


@router.message(StateFilter(AdminStates.creating_tournament_name))
async def process_tournament_name(message: Message, state: FSMContext):
    """Обработка ввода названия турнира"""
    if not message.text:
        await message.answer(
            "❌ Пожалуйста, отправьте текстовое сообщение с названием турнира.",
            parse_mode="Markdown"
        )
        return
    
    tournament_name = message.text.strip()
    
    # Валидация названия
    is_valid, error_message = validate_tournament_name(tournament_name)
    
    if not is_valid:
        await message.answer(
            f"{error_message}\n\nПопробуйте ещё раз:",
            parse_mode="Markdown"
        )
        return
    
    # Сохраняем название в состояние
    await state.update_data(tournament_name=tournament_name)
    
    # Переходим к следующему шагу - ввод описания
    text = f"""✅ **Название принято:** {tournament_name}

📝 **Шаг 2 из 8: Описание турнира**

Введите описание турнира:

▪️ Максимум 1000 символов
▪️ Опишите цели, правила, призы
▪️ Можете добавить эмодзи

**Пример:** Ежегодный турнир для начинающих игроков 🏆"""
    
    # Создаем кнопки навигации
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад к названию", 
                callback_data="admin:edit_tournament_name"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить создание",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await message.answer(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_description)


@router.callback_query(F.data == "admin:edit_tournament_name")
async def edit_tournament_name(callback: CallbackQuery, state: FSMContext):
    """Возврат к редактированию названия турнира"""
    text = """📝 **Шаг 1 из 8: Название турнира**

Введите название турнира:

▪️ Минимум 3 символа
▪️ Максимум 100 символов
▪️ Избегайте специальных символов

**Пример:** Championship 2025"""
    
    # Создаем кнопку отмены
    keyboard = [[
        InlineKeyboardButton(
            text="❌ Отменить создание",
            callback_data="admin:cancel_tournament_creation"
        )
    ]]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_name)
    await callback.answer()


def validate_tournament_description(description: str) -> tuple[bool, str]:
    """Валидация описания турнира"""
    if not description or not description.strip():
        return False, "❌ Описание не может быть пустым"
    
    description = description.strip()
    
    if len(description) > 1000:
        return False, "❌ Описание слишком длинное (максимум 1000 символов)"
    
    return True, ""


@router.message(StateFilter(AdminStates.creating_tournament_description))
async def process_tournament_description(message: Message, state: FSMContext):
    """Обработка ввода описания турнира"""
    if not message.text:
        await message.answer(
            "❌ Пожалуйста, отправьте текстовое сообщение с описанием турнира.",
            parse_mode="Markdown"
        )
        return
    
    tournament_description = message.text.strip()
    
    # Валидация описания
    is_valid, error_message = validate_tournament_description(tournament_description)
    
    if not is_valid:
        await message.answer(
            f"{error_message}\n\nПопробуйте ещё раз:",
            parse_mode="Markdown"
        )
        return
    
    # Сохраняем описание в состояние
    await state.update_data(tournament_description=tournament_description)
    
    # Получаем данные для показа прогресса
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    
    # Переходим к следующему шагу - выбор игры
    # Сначала получим список доступных игр
    try:
        from database.repositories import GameRepository
        games = await GameRepository.get_all_active()
        
        if not games:
            await message.answer(
                "❌ В системе нет доступных игр. Обратитесь к администратору.",
                parse_mode="Markdown"
            )
            return
        
        text = f"""✅ **Описание принято**

📝 **Шаг 3 из 8: Выбор игры**

**Турнир:** {tournament_name}
**Описание:** {tournament_description[:100]}{"..." if len(tournament_description) > 100 else ""}

🎮 Выберите игру для турнира:"""
        
        # Создаем клавиатуру с играми
        keyboard = []
        for game in games:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🎮 {game.name}",
                    callback_data=f"admin:select_game_{game.id}"
                )
            ])
        
        # Добавляем навигационные кнопки
        keyboard.extend([
            [
                InlineKeyboardButton(
                    text="🔙 Назад к описанию", 
                    callback_data="admin:edit_tournament_description"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить создание",
                    callback_data="admin:cancel_tournament_creation"
                )
            ]
        ])
        
        await message.answer(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.creating_tournament_game)
        
    except Exception as e:
        logger.error(f"Ошибка получения списка игр: {e}")
        await message.answer(
            "❌ Ошибка при получении списка игр. Попробуйте позже.",
            parse_mode="Markdown"
        )


@router.callback_query(F.data == "admin:edit_tournament_description")
async def edit_tournament_description(callback: CallbackQuery, state: FSMContext):
    """Возврат к редактированию описания турнира"""
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    
    text = f"""✅ **Название:** {tournament_name}

📝 **Шаг 2 из 8: Описание турнира**

Введите описание турнира:

▪️ Максимум 1000 символов
▪️ Опишите цели, правила, призы
▪️ Можете добавить эмодзи

**Пример:** Ежегодный турнир для начинающих игроков 🏆"""
    
    # Создаем кнопки навигации
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад к названию", 
                callback_data="admin:edit_tournament_name"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить создание",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_description)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:select_game_"))
async def process_game_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора игры для турнира"""
    game_id = callback.data.split("_")[-1]  # admin:select_game_123 -> 123
    
    try:
        from database.repositories import GameRepository
        game = await GameRepository.get_by_id(int(game_id))
        
        if not game:
            await callback.answer("❌ Игра не найдена")
            return
        
        # Сохраняем игру в состояние
        await state.update_data(tournament_game_id=game.id, tournament_game_name=game.name)
        
        # Получаем данные для показа прогресса
        data = await state.get_data()
        tournament_name = data.get('tournament_name', '')
        tournament_description = data.get('tournament_description', '')
        
        # Переходим к следующему шагу - выбор формата
        text = f"""✅ **Игра выбрана:** {game.name}

📝 **Шаг 4 из 8: Формат турнира**

**Турнир:** {tournament_name}
**Игра:** {game.name}

🏆 Выберите формат турнира:"""
        
        # Создаем клавиатуру с форматами
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🏁 Single Elimination",
                    callback_data="admin:select_format_single"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Double Elimination", 
                    callback_data="admin:select_format_double"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚡ Round Robin",
                    callback_data="admin:select_format_round_robin"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад к выбору игры",
                    callback_data="admin:edit_tournament_game"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить создание",
                    callback_data="admin:cancel_tournament_creation"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.creating_tournament_format)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при выборе игры: {e}")
        await callback.answer("❌ Ошибка при выборе игры")


@router.callback_query(F.data == "admin:edit_tournament_game")  
async def edit_tournament_game(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору игры"""
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    tournament_description = data.get('tournament_description', '')
    
    try:
        from database.repositories import GameRepository
        games = await GameRepository.get_all_active()
        
        text = f"""✅ **Описание принято**

📝 **Шаг 3 из 8: Выбор игры**

**Турнир:** {tournament_name}
**Описание:** {tournament_description[:100]}{"..." if len(tournament_description) > 100 else ""}

🎮 Выберите игру для турнира:"""
        
        # Создаем клавиатуру с играми
        keyboard = []
        for game in games:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🎮 {game.name}",
                    callback_data=f"admin:select_game_{game.id}"
                )
            ])
        
        # Добавляем навигационные кнопки
        keyboard.extend([
            [
                InlineKeyboardButton(
                    text="🔙 Назад к описанию", 
                    callback_data="admin:edit_tournament_description"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить создание",
                    callback_data="admin:cancel_tournament_creation"
                )
            ]
        ])
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.creating_tournament_game)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения списка игр: {e}")
        await callback.answer("❌ Ошибка при получении списка игр")


@router.callback_query(F.data.startswith("admin:select_format_"))
async def process_format_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора формата турнира"""
    format_type = callback.data.split("_")[-1]  # admin:select_format_single -> single
    
    format_names = {
        "single": "Single Elimination",
        "double": "Double Elimination", 
        "round": "Round Robin"  # from round_robin
    }
    
    if format_type == "robin":  # для round_robin
        format_type = "round_robin"
        format_display = "Round Robin"
    else:
        format_display = format_names.get(format_type, format_type)
    
    # Сохраняем формат в состояние
    await state.update_data(tournament_format=format_type, tournament_format_display=format_display)
    
    # Получаем данные для показа прогресса
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    tournament_game_name = data.get('tournament_game_name', '')
    
    # Переходим к следующему шагу - ввод количества команд
    text = f"""✅ **Формат выбран:** {format_display}

📝 **Шаг 5 из 8: Количество команд**

**Турнир:** {tournament_name}
**Игра:** {tournament_game_name}
**Формат:** {format_display}

👥 Введите максимальное количество команд:

▪️ Минимум: 2 команды
▪️ Максимум: 128 команд
▪️ Только числа

**Пример:** 16"""
    
    # Создаем кнопки навигации
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад к формату",
                callback_data="admin:edit_tournament_format"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить создание",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_max_teams)
    await callback.answer()


@router.callback_query(F.data == "admin:edit_tournament_format")
async def edit_tournament_format(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору формата"""
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    tournament_game_name = data.get('tournament_game_name', '')
    
    text = f"""📝 **Шаг 4 из 8: Формат турнира**

**Турнир:** {tournament_name}
**Игра:** {tournament_game_name}

🏆 Выберите формат турнира:"""
    
    # Создаем клавиатуру с форматами
    keyboard = [
        [
            InlineKeyboardButton(
                text="🏁 Single Elimination",
                callback_data="admin:select_format_single"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Double Elimination", 
                callback_data="admin:select_format_double"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚡ Round Robin",
                callback_data="admin:select_format_round_robin"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к выбору игры",
                callback_data="admin:edit_tournament_game"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить создание",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_format)
    await callback.answer()


def validate_team_count(count_str: str) -> tuple[bool, str, int]:
    """Валидация количества команд"""
    try:
        count = int(count_str.strip())
        
        if count < 2:
            return False, "❌ Минимальное количество команд: 2", 0
        
        if count > 128:
            return False, "❌ Максимальное количество команд: 128", 0
        
        return True, "", count
    except ValueError:
        return False, "❌ Введите корректное число", 0


@router.message(StateFilter(AdminStates.creating_tournament_max_teams))
async def process_tournament_max_teams(message: Message, state: FSMContext):
    """Обработка ввода максимального количества команд"""
    if not message.text:
        await message.answer(
            "❌ Пожалуйста, отправьте число команд.",
            parse_mode="Markdown"
        )
        return
    
    # Валидация количества команд
    is_valid, error_message, team_count = validate_team_count(message.text)
    
    if not is_valid:
        await message.answer(
            f"{error_message}\n\nПопробуйте ещё раз:",
            parse_mode="Markdown"
        )
        return
    
    # Сохраняем количество команд в состояние
    await state.update_data(tournament_max_teams=team_count)
    
    # Получаем данные для показа прогресса
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    tournament_game_name = data.get('tournament_game_name', '')
    tournament_format_display = data.get('tournament_format_display', '')
    
    # Переходим к следующему шагу - дата начала регистрации
    text = f"""✅ **Количество команд:** {team_count}

📝 **Шаг 6 из 8: Даты турнира**

**Турнир:** {tournament_name}
**Игра:** {tournament_game_name}
**Формат:** {tournament_format_display}
**Команд:** {team_count}

📅 Введите дату начала регистрации:

▪️ Формат: ДД.ММ.ГГГГ ЧЧ:ММ
▪️ Пример: 01.12.2024 10:00
▪️ Или: завтра 15:00"""
    
    # Создаем кнопки навигации
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад к количеству команд",
                callback_data="admin:edit_tournament_max_teams"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить создание",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await message.answer(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_registration_start)


@router.callback_query(F.data == "admin:edit_tournament_max_teams")
async def edit_tournament_max_teams(callback: CallbackQuery, state: FSMContext):
    """Возврат к вводу количества команд"""
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    tournament_game_name = data.get('tournament_game_name', '')
    tournament_format_display = data.get('tournament_format_display', '')
    
    text = f"""📝 **Шаг 5 из 8: Количество команд**

**Турнир:** {tournament_name}
**Игра:** {tournament_game_name}
**Формат:** {tournament_format_display}

👥 Введите максимальное количество команд:

▪️ Минимум: 2 команды
▪️ Максимум: 128 команд
▪️ Только числа

**Пример:** 16"""
    
    # Создаем кнопки навигации
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад к формату",
                callback_data="admin:edit_tournament_format"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить создание",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_max_teams)
    await callback.answer()