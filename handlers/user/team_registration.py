"""
Обработчики регистрации команды - часть 2: добавление игроков
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database.repositories.user_repository import UserRepository
from database.repositories.team_repository import TeamRepository
from database.repositories.player_repository import PlayerRepository
from database.models import TeamStatus
from utils.message_utils import safe_edit_message
from handlers.user.states import UserStates

# Создаем роутер
team_registration_router = Router()
logger = logging.getLogger(__name__)


# ========== СОЗДАНИЕ КОМАНДЫ - ШАГ 3: ЛОГОТИП (ОБЯЗАТЕЛЬНО) ==========

@team_registration_router.message(StateFilter(UserStates.registering_team_uploading_logo), F.photo)
async def process_team_logo(message: Message, state: FSMContext):
    """Обработка логотипа команды"""
    try:
        # Берём самое большое фото
        photo = message.photo[-1]
        
        # Проверка размера (5 МБ = 5242880 байт)
        if photo.file_size > 5242880:
            await message.answer("❌ Файл слишком большой. Максимальный размер: 5 МБ.\n\nПопробуйте другой файл:")
            return
        
        # Проверяем что лого квадратное (допуск ±10%)
        width = photo.width
        height = photo.height
        ratio = width / height if height > 0 else 0
        
        if ratio < 0.9 or ratio > 1.1:  # Не квадратное (допуск 10%)
            await message.answer(
                f"⚠️ Логотип должен быть квадратным!\n\n"
                f"Текущее соотношение: {width}x{height}\n"
                f"Пожалуйста, загрузите квадратное изображение (например, 512x512, 1024x1024)."
            )
            return
        
        # Сохраняем file_id
        await state.update_data(logo_file_id=photo.file_id)
        
        text = "✅ Логотип сохранён!\n\nПереходим к добавлению игроков..."
        await message.answer(text)
        
        # Переходим к добавлению игроков
        await start_adding_main_players_message(message, state)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки логотипа: {e}")
        await message.answer("❌ Ошибка загрузки. Попробуйте ещё раз.")


# ========== СОЗДАНИЕ КОМАНДЫ - ШАГ 4: ДОБАВЛЕНИЕ ОСНОВНЫХ ИГРОКОВ ==========

async def start_adding_main_players(callback: CallbackQuery, state: FSMContext):
    """Начало добавления основных игроков"""
    data = await state.get_data()
    max_players = data.get('max_players', 5)
    
    # Инициализируем список игроков
    await state.update_data(main_players=[], substitutes=[])
    
    text = f"""➕ **Добавление игроков**

**Шаг 4/5:** Основной состав (0/{max_players})

Добавьте основных игроков вашей команды.

**Формат сообщения:**
`Никнейм | Game ID`

**Пример:**
`ProPlayer | 123456789`

Никнейм - игровое имя
Game ID - внутриигровой ID"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="⏭️ К запасным игрокам",
                callback_data="team:to_substitutes"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="menu:my_teams"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(UserStates.registering_team_adding_main_players)
    await callback.answer()


async def start_adding_main_players_message(message: Message, state: FSMContext):
    """Начало добавления основных игроков (через message)"""
    data = await state.get_data()
    max_players = data.get('max_players', 5)
    
    # Инициализируем список игроков
    await state.update_data(main_players=[], substitutes=[])
    
    text = f"""➕ **Добавление игроков**

**Шаг 4/5:** Основной состав (0/{max_players})

Добавьте основных игроков вашей команды.

**Формат сообщения:**
`Никнейм | Game ID`

**Пример:**
`ProPlayer | 123456789`

Никнейм - игровое имя
Game ID - внутриигровой ID"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="⏭️ К запасным игрокам",
                callback_data="team:to_substitutes"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="menu:my_teams"
            )
        ]
    ]
    
    await message.answer(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(UserStates.registering_team_adding_main_players)


@team_registration_router.message(StateFilter(UserStates.registering_team_adding_main_players))
async def add_main_player(message: Message, state: FSMContext):
    """Добавление основного игрока"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение.")
        return
    
    try:
        # Парсим данные игрока
        parts = [p.strip() for p in message.text.split("|")]
        
        if len(parts) != 2:
            await message.answer(
                "❌ Неверный формат!\n\n"
                "Используйте формат: `Никнейм | Game ID`\n"
                "Пример: `ProPlayer | 123456789`",
                parse_mode="Markdown"
            )
            return
        
        nickname, game_id = parts
        
        # Валидация
        if len(nickname) < 2 or len(nickname) > 30:
            await message.answer("❌ Никнейм должен быть от 2 до 30 символов.")
            return
        
        if len(game_id) < 3 or len(game_id) > 50:
            await message.answer("❌ Game ID должен быть от 3 до 50 символов.")
            return
        
        data = await state.get_data()
        main_players = data.get('main_players', [])
        max_players = data.get('max_players', 5)
        
        # Проверка лимита
        if len(main_players) >= max_players:
            await message.answer(f"❌ Достигнут максимум основных игроков ({max_players}).")
            return
        
        # Проверка дубликатов никнейма
        if any(p['nickname'].lower() == nickname.lower() for p in main_players):
            await message.answer(f"❌ Игрок с никнеймом '{nickname}' уже добавлен.")
            return
        
        # Проверка дубликатов Game ID
        if any(p['game_id'] == game_id for p in main_players):
            await message.answer(f"❌ Игрок с Game ID '{game_id}' уже добавлен.")
            return
        
        # Проверка что игрок не занят в другой команде турнира
        tournament_id = data.get('tournament_id')
        if tournament_id:
            is_taken = await PlayerRepository.is_game_id_taken_in_tournament(tournament_id, game_id)
            if is_taken:
                await message.answer(
                    f"❌ Игрок с Game ID '{game_id}' уже зарегистрирован в другой команде этого турнира!\n\n"
                    "Один игрок может участвовать только в одной команде турнира."
                )
                return
        
        # Добавляем игрока
        main_players.append({
            'nickname': nickname,
            'game_id': game_id,
            'position': len(main_players) + 1
        })
        
        await state.update_data(main_players=main_players)
        
        # Формируем список добавленных игроков
        players_list = "\n".join([
            f"{i}. {p['nickname']} (`{p['game_id']}`)"
            for i, p in enumerate(main_players, 1)
        ])
        
        text = f"""✅ **Игрок добавлен!**

**Основной состав** ({len(main_players)}/{max_players}):
{players_list}

{"✅ Состав полный! Можете перейти к запасным игрокам." if len(main_players) == max_players else "Добавьте ещё игроков или перейдите к запасным."}"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить последнего",
                    callback_data="team:remove_last_main"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏭️ К запасным игрокам",
                    callback_data="team:to_substitutes"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить регистрацию",
                    callback_data="menu:my_teams"
                )
            ]
        ]
        
        await message.answer(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка добавления игрока: {e}")
        await message.answer("❌ Ошибка добавления игрока.")


@team_registration_router.callback_query(F.data == "team:remove_last_main")
async def remove_last_main_player(callback: CallbackQuery, state: FSMContext):
    """Удаление последнего добавленного основного игрока"""
    try:
        data = await state.get_data()
        main_players = data.get('main_players', [])
        
        if not main_players:
            await callback.answer("❌ Нет игроков для удаления", show_alert=True)
            return
        
        removed_player = main_players.pop()
        await state.update_data(main_players=main_players)
        
        await callback.answer(f"✅ Игрок {removed_player['nickname']} удалён")
        
        # Обновляем сообщение
        max_players = data.get('max_players', 5)
        
        if main_players:
            players_list = "\n".join([
                f"{i}. {p['nickname']} (`{p['game_id']}`)"
                for i, p in enumerate(main_players, 1)
            ])
        else:
            players_list = "Нет игроков"
        
        text = f"""➕ **Основной состав** ({len(main_players)}/{max_players})

{players_list}

Добавьте ещё игроков или перейдите к запасным."""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить последнего",
                    callback_data="team:remove_last_main"
                )
            ] if main_players else [],
            [
                InlineKeyboardButton(
                    text="⏭️ К запасным игрокам",
                    callback_data="team:to_substitutes"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="menu:my_teams"
                )
            ]
        ]
        
        # Убираем пустые списки
        keyboard = [row for row in keyboard if row]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка удаления игрока: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ========== СОЗДАНИЕ КОМАНДЫ - ШАГ 5: ДОБАВЛЕНИЕ ЗАПАСНЫХ ==========

@team_registration_router.callback_query(F.data == "team:to_substitutes")
async def start_adding_substitutes(callback: CallbackQuery, state: FSMContext):
    """Переход к добавлению запасных игроков"""
    try:
        data = await state.get_data()
        main_players = data.get('main_players', [])
        max_players = data.get('max_players', 5)
        max_substitutes = data.get('max_substitutes', 0)
        
        # Проверка что добавлен хотя бы один основной игрок
        if not main_players:
            await callback.answer(
                "❌ Добавьте хотя бы одного основного игрока!",
                show_alert=True
            )
            return
        
        # Если запасных не предусмотрено, сразу к подтверждению
        if max_substitutes == 0:
            await callback.answer("ℹ️ Запасные игроки не предусмотрены")
            await show_team_confirmation(callback, state)
            return
        
        text = f"""➕ **Добавление запасных**

**Шаг 5/5:** Запасные игроки (0/{max_substitutes})

Добавьте запасных игроков (опционально).

**Формат сообщения:**
`Никнейм | Game ID`

**Пример:**
`SubPlayer | 987654321`"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⏭️ Пропустить и завершить",
                    callback_data="team:confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад к основному составу",
                    callback_data="team:back_to_main"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="menu:my_teams"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(UserStates.registering_team_adding_substitutes)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка перехода к запасным: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@team_registration_router.callback_query(F.data == "team:back_to_main")
async def back_to_main_players(callback: CallbackQuery, state: FSMContext):
    """Возврат к добавлению основных игроков"""
    await state.set_state(UserStates.registering_team_adding_main_players)
    
    data = await state.get_data()
    main_players = data.get('main_players', [])
    max_players = data.get('max_players', 5)
    
    players_list = "\n".join([
        f"{i}. {p['nickname']} (`{p['game_id']}`)"
        for i, p in enumerate(main_players, 1)
    ]) if main_players else "Нет игроков"
    
    text = f"""➕ **Основной состав** ({len(main_players)}/{max_players})

{players_list}

Добавьте ещё игроков или перейдите к запасным."""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="🗑️ Удалить последнего",
                callback_data="team:remove_last_main"
            )
        ] if main_players else [],
        [
            InlineKeyboardButton(
                text="⏭️ К запасным игрокам",
                callback_data="team:to_substitutes"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="menu:my_teams"
            )
        ]
    ]
    
    # Убираем пустые списки
    keyboard = [row for row in keyboard if row]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@team_registration_router.message(StateFilter(UserStates.registering_team_adding_substitutes))
async def add_substitute_player(message: Message, state: FSMContext):
    """Добавление запасного игрока"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение.")
        return
    
    try:
        # Парсим данные игрока
        parts = [p.strip() for p in message.text.split("|")]
        
        if len(parts) != 2:
            await message.answer(
                "❌ Неверный формат!\n\n"
                "Используйте формат: `Никнейм | Game ID`\n"
                "Пример: `SubPlayer | 987654321`",
                parse_mode="Markdown"
            )
            return
        
        nickname, game_id = parts
        
        # Валидация
        if len(nickname) < 2 or len(nickname) > 30:
            await message.answer("❌ Никнейм должен быть от 2 до 30 символов.")
            return
        
        if len(game_id) < 3 or len(game_id) > 50:
            await message.answer("❌ Game ID должен быть от 3 до 50 символов.")
            return
        
        data = await state.get_data()
        main_players = data.get('main_players', [])
        substitutes = data.get('substitutes', [])
        max_substitutes = data.get('max_substitutes', 0)
        
        # Проверка лимита
        if len(substitutes) >= max_substitutes:
            await message.answer(f"❌ Достигнут максимум запасных игроков ({max_substitutes}).")
            return
        
        # Проверка дубликатов в основном составе
        if any(p['nickname'].lower() == nickname.lower() for p in main_players):
            await message.answer(f"❌ Игрок с никнеймом '{nickname}' уже в основном составе.")
            return
        
        if any(p['game_id'] == game_id for p in main_players):
            await message.answer(f"❌ Игрок с Game ID '{game_id}' уже в основном составе.")
            return
        
        # Проверка дубликатов в запасных
        if any(p['nickname'].lower() == nickname.lower() for p in substitutes):
            await message.answer(f"❌ Игрок с никнеймом '{nickname}' уже в запасных.")
            return
        
        if any(p['game_id'] == game_id for p in substitutes):
            await message.answer(f"❌ Игрок с Game ID '{game_id}' уже в запасных.")
            return
        
        # Проверка что игрок не занят в другой команде турнира
        tournament_id = data.get('tournament_id')
        if tournament_id:
            is_taken = await PlayerRepository.is_game_id_taken_in_tournament(tournament_id, game_id)
            if is_taken:
                await message.answer(
                    f"❌ Игрок с Game ID '{game_id}' уже зарегистрирован в другой команде этого турнира!\n\n"
                    "Один игрок может участвовать только в одной команде турнира."
                )
                return
        
        # Добавляем игрока
        substitutes.append({
            'nickname': nickname,
            'game_id': game_id,
            'position': len(substitutes) + 1
        })
        
        await state.update_data(substitutes=substitutes)
        
        # Формируем список
        subs_list = "\n".join([
            f"{i}. {p['nickname']} (`{p['game_id']}`)"
            for i, p in enumerate(substitutes, 1)
        ])
        
        text = f"""✅ **Запасной игрок добавлен!**

**Запасные игроки** ({len(substitutes)}/{max_substitutes}):
{subs_list}

{"✅ Все запасные добавлены! Можете завершить регистрацию." if len(substitutes) == max_substitutes else "Добавьте ещё запасных или завершите регистрацию."}"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить последнего",
                    callback_data="team:remove_last_sub"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Завершить регистрацию",
                    callback_data="team:confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 К основному составу",
                    callback_data="team:back_to_main"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="menu:my_teams"
                )
            ]
        ]
        
        await message.answer(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка добавления запасного: {e}")
        await message.answer("❌ Ошибка добавления игрока.")


@team_registration_router.callback_query(F.data == "team:remove_last_sub")
async def remove_last_substitute(callback: CallbackQuery, state: FSMContext):
    """Удаление последнего запасного игрока"""
    try:
        data = await state.get_data()
        substitutes = data.get('substitutes', [])
        
        if not substitutes:
            await callback.answer("❌ Нет запасных для удаления", show_alert=True)
            return
        
        removed_player = substitutes.pop()
        await state.update_data(substitutes=substitutes)
        
        await callback.answer(f"✅ Игрок {removed_player['nickname']} удалён")
        
        # Обновляем сообщение
        max_substitutes = data.get('max_substitutes', 0)
        
        if substitutes:
            subs_list = "\n".join([
                f"{i}. {p['nickname']} (`{p['game_id']}`)"
                for i, p in enumerate(substitutes, 1)
            ])
        else:
            subs_list = "Нет запасных"
        
        text = f"""➕ **Запасные игроки** ({len(substitutes)}/{max_substitutes})

{subs_list}

Добавьте запасных или завершите регистрацию."""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить последнего",
                    callback_data="team:remove_last_sub"
                )
            ] if substitutes else [],
            [
                InlineKeyboardButton(
                    text="✅ Завершить регистрацию",
                    callback_data="team:confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="menu:my_teams"
                )
            ]
        ]
        
        # Убираем пустые списки
        keyboard = [row for row in keyboard if row]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка удаления запасного: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ========== ПОДТВЕРЖДЕНИЕ И СОЗДАНИЕ КОМАНДЫ ==========

@team_registration_router.callback_query(F.data == "team:confirm")
async def show_team_confirmation(callback: CallbackQuery, state: FSMContext):
    """Показ подтверждения регистрации команды"""
    try:
        data = await state.get_data()
        
        # Логируем данные для отладки
        logger.info(f"Подтверждение команды, данные state: {data.keys()}")
        logger.info(f"tournament_id={data.get('tournament_id')}, team_name={data.get('team_name')}")
        
        team_name = data.get('team_name')
        tournament_name = data.get('tournament_name')
        game_name = data.get('game_name')
        main_players = data.get('main_players', [])
        substitutes = data.get('substitutes', [])
        
        # Формируем списки игроков
        main_list = "\n".join([
            f"{i}. {p['nickname']} (`{p['game_id']}`)"
            for i, p in enumerate(main_players, 1)
        ]) if main_players else "Нет игроков"
        
        subs_list = "\n".join([
            f"{i}. {p['nickname']} (`{p['game_id']}`)"
            for i, p in enumerate(substitutes, 1)
        ]) if substitutes else "Нет запасных"
        
        text = f"""📋 **Подтверждение регистрации**

**Команда:** {team_name}
**Турнир:** {tournament_name}
**Игра:** {game_name}

**Основной состав** ({len(main_players)}):
{main_list}

**Запасные игроки** ({len(substitutes)}):
{subs_list}

Всё верно? Подтвердите регистрацию."""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить и зарегистрировать",
                    callback_data="team:final_confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Изменить запасных",
                    callback_data="team:to_substitutes"
                ),
                InlineKeyboardButton(
                    text="🔙 Изменить состав",
                    callback_data="team:back_to_main"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить регистрацию",
                    callback_data="menu:my_teams"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(UserStates.registering_team_confirmation)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка показа подтверждения: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@team_registration_router.callback_query(F.data == "team:final_confirm")
async def create_team_final(callback: CallbackQuery, state: FSMContext):
    """Финальное создание команды в БД"""
    try:
        user = await UserRepository.get_by_telegram_id(callback.from_user.id)
        data = await state.get_data()
        
        # Детальное логирование для отладки
        logger.info(f"Финальное создание команды, все данные state: {data}")
        
        tournament_id = data.get('tournament_id')
        team_name = data.get('team_name')
        logo_file_id = data.get('logo_file_id')
        main_players = data.get('main_players', [])
        substitutes = data.get('substitutes', [])
        
        # Проверяем что tournament_id не None
        if not tournament_id:
            logger.error(f"tournament_id is None! Full state data: {data}")
            await callback.answer("❌ Ошибка: турнир не найден. Начните регистрацию заново.", show_alert=True)
            await state.clear()
            return
        
        # Проверяем что у капитана еще нет команды на этот турнир
        is_already_registered = await TeamRepository.is_captain_registered(user.id, tournament_id)
        if is_already_registered:
            await callback.answer(
                "❌ Вы уже зарегистрировали команду на этот турнир!\n\n"
                "Один капитан может зарегистрировать только одну команду на турнир.",
                show_alert=True
            )
            await state.clear()
            return
        
        # Создаём команду
        team = await TeamRepository.create_team(
            tournament_id=tournament_id,
            name=team_name,
            captain_id=user.id,
            logo_file_id=logo_file_id
        )
        
        if not team:
            await callback.answer("❌ Ошибка создания команды", show_alert=True)
            return
        
        # Добавляем основных игроков
        for player_data in main_players:
            await PlayerRepository.add_player(
                team_id=team.id,
                nickname=player_data['nickname'],
                game_id=player_data['game_id'],
                is_substitute=False,
                position=player_data['position']
            )
        
        # Добавляем запасных
        for player_data in substitutes:
            await PlayerRepository.add_player(
                team_id=team.id,
                nickname=player_data['nickname'],
                game_id=player_data['game_id'],
                is_substitute=True,
                position=player_data['position']
            )
        
        # Успешное создание
        text = f"""✅ **Команда успешно зарегистрирована!**

**{team_name}** зарегистрирована на турнир **{data.get('tournament_name')}**

📊 Статус: ⏳ Ожидает модерации

Администраторы проверят вашу заявку.
Вы получите уведомление о результатах.

**Состав:**
▪️ Основных игроков: {len(main_players)}
▪️ Запасных игроков: {len(substitutes)}"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="👁️ Просмотреть команду",
                    callback_data=f"team:view_{team.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Создать ещё команду",
                    callback_data="team:create"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="main_menu"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        await state.clear()
        logger.info(f"Команда создана: {team.name} (ID: {team.id}) пользователем {user.telegram_id}")
        await callback.answer("✅ Команда создана!", show_alert=True)
        
        # Отправляем уведомление в админ-чат о новой команде
        from config.settings import settings
        from utils.text_formatting import escape_html
        
        tournament_name_escaped = escape_html(data.get('tournament_name', 'Неизвестный турнир'))
        team_name_escaped = escape_html(team_name)
        captain_name = escape_html(user.full_name or user.username or 'Unknown')
        
        admin_text = f"""🔔 <b>Новая заявка на участие!</b>

👥 <b>Команда:</b> {team_name_escaped}
🏆 <b>Турнир:</b> {tournament_name_escaped}
👤 <b>Капитан:</b> {captain_name}

<b>Состав:</b>
▪️ Основных игроков: {len(main_players)}
▪️ Запасных игроков: {len(substitutes)}

⏳ <b>Ожидает проверки администратором</b>"""
        
        admin_keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"admin:approve_team_{team.id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"admin:reject_team_{team.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👁️ Подробнее",
                    callback_data=f"admin:review_team_{team.id}"
                )
            ]
        ]
        
        # Отправляем в админ-чат (если настроен) или всем админам
        if settings.admin_chat_id:
            try:
                # Если есть логотип команды, отправляем с ним
                if team.logo_file_id:
                    await callback.bot.send_photo(
                        chat_id=settings.admin_chat_id,
                        photo=team.logo_file_id,
                        caption=admin_text,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=admin_keyboard)
                    )
                else:
                    await callback.bot.send_message(
                        chat_id=settings.admin_chat_id,
                        text=admin_text,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=admin_keyboard)
                    )
                logger.info(f"Уведомление о команде {team.id} отправлено в админ-чат {settings.admin_chat_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления в админ-чат: {e}")
        else:
            # Резервный вариант - отправка каждому админу
            for admin_id in settings.admin_ids:
                try:
                    await callback.bot.send_message(
                        chat_id=admin_id,
                        text=admin_text,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=admin_keyboard)
                    )
                    logger.info(f"Уведомление о команде {team.id} отправлено админу {admin_id}")
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления админу {admin_id}: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка финального создания команды: {e}")
        await callback.answer("❌ Критическая ошибка создания команды", show_alert=True)


# ========== УДАЛЕНИЕ КОМАНДЫ ==========

@team_registration_router.callback_query(F.data.startswith("team:delete_confirm_"))
async def confirm_team_deletion(callback: CallbackQuery, state: FSMContext):
    """Подтверждение удаления команды"""
    try:
        team_id = int(callback.data.split("_")[2])
        team = await TeamRepository.get_by_id(team_id)
        
        if not team:
            await callback.answer("❌ Команда не найдена", show_alert=True)
            return
        
        user = await UserRepository.get_by_telegram_id(callback.from_user.id)
        if team.captain_id != user.id:
            await callback.answer("❌ Это не ваша команда", show_alert=True)
            return
        
        text = f"""⚠️ **Подтверждение удаления**

Вы действительно хотите удалить команду **{team.name}**?

⚠️ Это действие необратимо!
⚠️ Все данные команды будут удалены!"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить команду",
                    callback_data=f"team:delete_final_{team_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"team:view_{team_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка подтверждения удаления: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@team_registration_router.callback_query(F.data.startswith("team:delete_final_"))
async def delete_team_final(callback: CallbackQuery, state: FSMContext):
    """Финальное удаление команды"""
    try:
        team_id = int(callback.data.split("_")[2])
        team = await TeamRepository.get_by_id(team_id)
        
        if not team:
            await callback.answer("❌ Команда не найдена", show_alert=True)
            return
        
        user = await UserRepository.get_by_telegram_id(callback.from_user.id)
        if team.captain_id != user.id:
            await callback.answer("❌ Это не ваша команда", show_alert=True)
            return
        
        team_name = team.name
        success = await TeamRepository.delete_team(team_id)
        
        if success:
            text = f"""✅ **Команда удалена**

Команда **{team_name}** была успешно удалена."""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="👥 Мои команды",
                        callback_data="menu:my_teams"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏠 Главное меню",
                        callback_data="main_menu"
                    )
                ]
            ]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            await state.clear()
            logger.info(f"Команда удалена: {team_name} (ID: {team_id})")
        else:
            await callback.answer("❌ Ошибка удаления", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка финального удаления: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
