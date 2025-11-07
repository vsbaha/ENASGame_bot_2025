"""
Обработчики для управления играми
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database.repositories import GameRepository
from utils.message_utils import safe_edit_message
from .states import AdminStates
from .keyboards import get_tournament_management_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "admin:add_game")
async def start_add_game(callback: CallbackQuery, state: FSMContext):
    """Начало добавления новой игры"""
    await state.clear()
    
    text = """🎮 **Добавление новой игры**

📝 Введите название игры:

▪️ Минимум 2 символа
▪️ Максимум 50 символов
▪️ Должно быть уникальным

**Примеры:** CS:GO, Dota 2, League of Legends"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="admin:tournaments"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.adding_game_name)
    await callback.answer()


@router.message(StateFilter(AdminStates.adding_game_name))
async def process_game_name(message: Message, state: FSMContext):
    """Обработка названия игры"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение с названием игры.")
        return
    
    game_name = message.text.strip()
    
    # Валидация названия
    if len(game_name) < 2:
        await message.answer("❌ Название слишком короткое (минимум 2 символа).\n\nПопробуйте ещё раз:")
        return
    
    if len(game_name) > 50:
        await message.answer("❌ Название слишком длинное (максимум 50 символов).\n\nПопробуйте ещё раз:")
        return
    
    # Проверяем уникальность
    try:
        existing_game = await GameRepository.get_by_name(game_name)
        if existing_game:
            await message.answer(f"❌ Игра '{game_name}' уже существует.\n\nВведите другое название:")
            return
        
        # Сохраняем название в состояние
        await state.update_data(game_name=game_name)
        
        # Переходим к максимальному количеству игроков
        text = f"""✅ **Название принято:** {game_name}

� Введите максимальное количество игроков в команде:

▪️ Минимум: 1 игрок
▪️ Максимум: 20 игроков
▪️ Только целые числа

**Примеры:** 5 (CS:GO), 11 (FIFA), 6 (Valorant)"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="admin:tournaments"
                )
            ]
        ]
        
        await message.answer(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.adding_game_max_players)
        
    except Exception as e:
        logger.error(f"Ошибка проверки уникальности игры: {e}")
        await message.answer("❌ Ошибка при проверке игры. Попробуйте позже.")


@router.message(StateFilter(AdminStates.adding_game_max_players))
async def process_game_max_players(message: Message, state: FSMContext):
    """Обработка максимального количества игроков"""
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите число от 1 до 20.")
        return
    
    max_players = int(message.text.strip())
    
    if max_players < 1 or max_players > 20:
        await message.answer("❌ Количество игроков должно быть от 1 до 20.\n\nПопробуйте ещё раз:")
        return
    
    # Сохраняем количество игроков в состояние
    await state.update_data(max_players=max_players)
    
    # Переходим к запасным игрокам
    text = f"""✅ **Максимум игроков:** {max_players}

👥 Введите максимальное количество запасных игроков:

▪️ Минимум: 0 запасных
▪️ Максимум: 10 запасных
▪️ Только целые числа

**Примеры:** 0 (без запасных), 2 (обычно), 5 (много запасных)"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="0️⃣ Без запасных",
                callback_data="admin:set_substitutes_zero"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="admin:tournaments"
            )
        ]
    ]
    
    await message.answer(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.adding_game_max_substitutes)


@router.callback_query(F.data == "admin:set_substitutes_zero")
async def set_substitutes_zero(callback: CallbackQuery, state: FSMContext):
    """Установка 0 запасных игроков"""
    await state.update_data(max_substitutes=0)
    await show_game_confirmation(callback, state)


@router.message(StateFilter(AdminStates.adding_game_max_substitutes))
async def process_game_max_substitutes(message: Message, state: FSMContext):
    """Обработка максимального количества запасных игроков"""
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите число от 0 до 10.")
        return
    
    max_substitutes = int(message.text.strip())
    
    if max_substitutes < 0 or max_substitutes > 10:
        await message.answer("❌ Количество запасных должно быть от 0 до 10.\n\nПопробуйте ещё раз:")
        return
    
    # Сохраняем количество запасных в состояние
    await state.update_data(max_substitutes=max_substitutes)
    
    # Переходим к подтверждению
    await show_game_confirmation_as_message(message, state)


async def show_game_confirmation(callback: CallbackQuery, state: FSMContext):
    """Показ подтверждения игры через callback"""
    data = await state.get_data()
    
    text = f"""📋 **Подтверждение добавления игры**

**📝 Название:** {data.get('game_name', '')}
**� Максимум игроков:** {data.get('max_players', 0)}
**🔄 Запасные игроки:** {data.get('max_substitutes', 0)}

Добавить эту игру в систему?"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Добавить игру",
                callback_data="admin:confirm_add_game"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Редактировать",
                callback_data="admin:edit_game_data"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="admin:tournaments"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


async def show_game_confirmation_as_message(message: Message, state: FSMContext):
    """Показ подтверждения игры через message"""
    data = await state.get_data()
    
    text = f"""📋 **Подтверждение добавления игры**

**📝 Название:** {data.get('game_name', '')}
**� Максимум игроков:** {data.get('max_players', 0)}
**🔄 Запасные игроки:** {data.get('max_substitutes', 0)}

Добавить эту игру в систему?"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Добавить игру",
                callback_data="admin:confirm_add_game"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Редактировать",
                callback_data="admin:edit_game_data"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="admin:tournaments"
            )
        ]
    ]
    
    await message.answer(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data == "admin:confirm_add_game")
async def confirm_add_game(callback: CallbackQuery, state: FSMContext):
    """Подтверждение добавления игры"""
    data = await state.get_data()
    
    try:
        # Создаем игру в базе данных
        game = await GameRepository.create_game(
            name=data.get('game_name'),
            short_name=data.get('game_name')[:20],  # Короткое название из первых 20 символов
            max_players=data.get('max_players', 5),
            max_substitutes=data.get('max_substitutes', 0),
            icon_file_id=None
        )
        
        # Успешное создание
        success_text = f"""✅ **Игра успешно добавлена!**

**📝 Название:** {game.name}
**🆔 ID:** {game.id}
**� Короткое название:** {game.short_name}
**👥 Макс. игроков:** {game.max_players}

Игра готова для использования в турнирах!"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="➕ Добавить ещё игру",
                    callback_data="admin:add_game"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Список игр",
                    callback_data="admin:list_games"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 К управлению турнирами",
                    callback_data="admin:tournaments"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, success_text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        await state.clear()
        logger.info(f"Игра добавлена: ID={game.id}, название={game.name}")
        
    except Exception as e:
        logger.error(f"Ошибка добавления игры: {e}")
        
        error_text = f"""❌ **Ошибка добавления игры**

Произошла ошибка при добавлении игры:
{str(e)[:200]}

Попробуйте добавить игру заново."""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔄 Попробовать снова",
                    callback_data="admin:add_game"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 К турнирам",
                    callback_data="admin:tournaments"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, error_text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


# ========== СПИСОК И РЕДАКТИРОВАНИЕ ИГР ==========

@router.callback_query(F.data == "admin:list_games")
async def list_games(callback: CallbackQuery, state: FSMContext):
    """Показ списка всех игр"""
    await state.clear()
    
    try:
        games = await GameRepository.get_all_games()
        
        if not games:
            text = """🎮 **Список игр**

❌ Игры пока не добавлены.

Добавьте первую игру для создания турниров!"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="➕ Добавить игру",
                        callback_data="admin:add_game"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="admin:tournaments"
                    )
                ]
            ]
        else:
            text = f"""🎮 **Список игр ({len(games)})**

Выберите игру для просмотра или редактирования:"""
            
            keyboard = []
            
            # Добавляем кнопки с играми
            for game in games:
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"🎮 {game.name} ({game.max_players}👥)",
                        callback_data=f"admin:view_game_{game.id}"
                    )
                ])
            
            # Кнопки управления
            keyboard.extend([
                [
                    InlineKeyboardButton(
                        text="➕ Добавить игру",
                        callback_data="admin:add_game"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="admin:tournaments"
                    )
                ]
            ])
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения списка игр: {e}")
        await callback.answer("❌ Ошибка загрузки игр", show_alert=True)


@router.callback_query(F.data.startswith("admin:view_game_"))
async def view_game(callback: CallbackQuery, state: FSMContext):
    """Просмотр информации об игре"""
    try:
        game_id = int(callback.data.split("_")[-1])
        game = await GameRepository.get_by_id(game_id)
        
        if not game:
            await callback.answer("❌ Игра не найдена", show_alert=True)
            return
        
        text = f"""🎮 **{game.name}**

**📋 Информация:**
▪️ ID: `{game.id}`
▪️ Короткое название: `{game.short_name}`
▪️ Максимум игроков: **{game.max_players}** 👥
▪️ Запасных игроков: **{game.max_substitutes}** 🔄
▪️ Иконка: {"✅ Установлена" if game.icon_file_id else "❌ Не установлена"}

**Действия:**"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📝 Изменить название",
                    callback_data=f"admin:edit_game_name_{game_id}"
                ),
                InlineKeyboardButton(
                    text="🔤 Короткое имя",
                    callback_data=f"admin:edit_game_short_name_{game_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Изменить макс. игроков",
                    callback_data=f"admin:edit_game_max_players_{game_id}"
                ),
                InlineKeyboardButton(
                    text="🔄 Изменить запасных",
                    callback_data=f"admin:edit_game_substitutes_{game_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼️ Установить иконку",
                    callback_data=f"admin:edit_game_icon_{game_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить игру",
                    callback_data=f"admin:confirm_delete_game_{game_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 К списку игр",
                    callback_data="admin:list_games"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка просмотра игры: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ========== РЕДАКТИРОВАНИЕ НАЗВАНИЯ ИГРЫ ==========

@router.callback_query(F.data.startswith("admin:edit_game_name_"))
async def start_edit_game_name(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования названия игры"""
    try:
        game_id = int(callback.data.split("_")[-1])
        game = await GameRepository.get_by_id(game_id)
        
        if not game:
            await callback.answer("❌ Игра не найдена", show_alert=True)
            return
        
        await state.update_data(editing_game_id=game_id)
        
        text = f"""📝 **Редактирование названия игры**

**Текущее название:** {game.name}

Введите новое название:

▪️ Минимум 2 символа
▪️ Максимум 50 символов
▪️ Должно быть уникальным"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"admin:view_game_{game_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.editing_game_name)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала редактирования названия: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(AdminStates.editing_game_name))
async def process_edit_game_name(message: Message, state: FSMContext):
    """Обработка нового названия игры"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение.")
        return
    
    new_name = message.text.strip()
    
    # Валидация
    if len(new_name) < 2:
        await message.answer("❌ Название слишком короткое (минимум 2 символа).\n\nПопробуйте ещё раз:")
        return
    
    if len(new_name) > 50:
        await message.answer("❌ Название слишком длинное (максимум 50 символов).\n\nПопробуйте ещё раз:")
        return
    
    try:
        data = await state.get_data()
        game_id = data.get('editing_game_id')
        
        # Проверка уникальности
        existing_game = await GameRepository.get_by_name(new_name)
        if existing_game and existing_game.id != game_id:
            await message.answer(f"❌ Игра с названием '{new_name}' уже существует.\n\nВведите другое название:")
            return
        
        # Обновляем название
        success = await GameRepository.update_game(game_id, name=new_name)
        
        if success:
            text = f"""✅ **Название успешно изменено!**

**Новое название:** {new_name}"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="👁️ Просмотр игры",
                        callback_data=f"admin:view_game_{game_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 К списку игр",
                        callback_data="admin:list_games"
                    )
                ]
            ]
            
            await message.answer(
                text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            await state.clear()
        else:
            await message.answer("❌ Ошибка обновления игры. Попробуйте позже.")
            
    except Exception as e:
        logger.error(f"Ошибка обновления названия игры: {e}")
        await message.answer("❌ Произошла ошибка при обновлении.")


# ========== РЕДАКТИРОВАНИЕ КОРОТКОГО НАЗВАНИЯ ==========

@router.callback_query(F.data.startswith("admin:edit_game_short_name_"))
async def start_edit_game_short_name(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования короткого названия"""
    try:
        game_id = int(callback.data.split("_")[-1])
        game = await GameRepository.get_by_id(game_id)
        
        if not game:
            await callback.answer("❌ Игра не найдена", show_alert=True)
            return
        
        await state.update_data(editing_game_id=game_id)
        
        text = f"""🔤 **Редактирование короткого названия**

**Текущее:** {game.short_name}

Введите новое короткое название:

▪️ Минимум 2 символа
▪️ Максимум 20 символов
▪️ Используется в компактных интерфейсах"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"admin:view_game_{game_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.editing_game_short_name)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала редактирования короткого названия: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(AdminStates.editing_game_short_name))
async def process_edit_game_short_name(message: Message, state: FSMContext):
    """Обработка нового короткого названия"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение.")
        return
    
    new_short_name = message.text.strip()
    
    # Валидация
    if len(new_short_name) < 2:
        await message.answer("❌ Название слишком короткое (минимум 2 символа).\n\nПопробуйте ещё раз:")
        return
    
    if len(new_short_name) > 20:
        await message.answer("❌ Название слишком длинное (максимум 20 символов).\n\nПопробуйте ещё раз:")
        return
    
    try:
        data = await state.get_data()
        game_id = data.get('editing_game_id')
        
        # Обновляем короткое название
        success = await GameRepository.update_game(game_id, short_name=new_short_name)
        
        if success:
            text = f"""✅ **Короткое название изменено!**

**Новое значение:** {new_short_name}"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="👁️ Просмотр игры",
                        callback_data=f"admin:view_game_{game_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 К списку игр",
                        callback_data="admin:list_games"
                    )
                ]
            ]
            
            await message.answer(
                text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            await state.clear()
        else:
            await message.answer("❌ Ошибка обновления игры. Попробуйте позже.")
            
    except Exception as e:
        logger.error(f"Ошибка обновления короткого названия: {e}")
        await message.answer("❌ Произошла ошибка при обновлении.")


# ========== РЕДАКТИРОВАНИЕ МАКС. ИГРОКОВ ==========

@router.callback_query(F.data.startswith("admin:edit_game_max_players_"))
async def start_edit_game_max_players(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования максимального количества игроков"""
    try:
        game_id = int(callback.data.split("_")[-1])
        game = await GameRepository.get_by_id(game_id)
        
        if not game:
            await callback.answer("❌ Игра не найдена", show_alert=True)
            return
        
        await state.update_data(editing_game_id=game_id)
        
        text = f"""👥 **Редактирование максимального количества игроков**

**Текущее значение:** {game.max_players}

Введите новое количество:

▪️ Минимум: 1 игрок
▪️ Максимум: 20 игроков
▪️ Только целые числа"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"admin:view_game_{game_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.editing_game_max_players)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала редактирования макс. игроков: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(AdminStates.editing_game_max_players))
async def process_edit_game_max_players(message: Message, state: FSMContext):
    """Обработка нового количества игроков"""
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите число от 1 до 20.")
        return
    
    max_players = int(message.text.strip())
    
    if max_players < 1 or max_players > 20:
        await message.answer("❌ Количество должно быть от 1 до 20.\n\nПопробуйте ещё раз:")
        return
    
    try:
        data = await state.get_data()
        game_id = data.get('editing_game_id')
        
        # Обновляем количество игроков
        success = await GameRepository.update_game(game_id, max_players=max_players)
        
        if success:
            text = f"""✅ **Максимум игроков изменён!**

**Новое значение:** {max_players} 👥"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="👁️ Просмотр игры",
                        callback_data=f"admin:view_game_{game_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 К списку игр",
                        callback_data="admin:list_games"
                    )
                ]
            ]
            
            await message.answer(
                text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            await state.clear()
        else:
            await message.answer("❌ Ошибка обновления игры. Попробуйте позже.")
            
    except Exception as e:
        logger.error(f"Ошибка обновления макс. игроков: {e}")
        await message.answer("❌ Произошла ошибка при обновлении.")


# ========== РЕДАКТИРОВАНИЕ ЗАПАСНЫХ ==========

@router.callback_query(F.data.startswith("admin:edit_game_substitutes_"))
async def start_edit_game_substitutes(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования количества запасных"""
    try:
        game_id = int(callback.data.split("_")[-1])
        game = await GameRepository.get_by_id(game_id)
        
        if not game:
            await callback.answer("❌ Игра не найдена", show_alert=True)
            return
        
        await state.update_data(editing_game_id=game_id)
        
        text = f"""🔄 **Редактирование запасных игроков**

**Текущее значение:** {game.max_substitutes}

Введите новое количество:

▪️ Минимум: 0 запасных
▪️ Максимум: 10 запасных
▪️ Только целые числа"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="0️⃣ Без запасных",
                    callback_data=f"admin:set_game_substitutes_0_{game_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"admin:view_game_{game_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.editing_game_max_substitutes)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала редактирования запасных: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:set_game_substitutes_0_"))
async def set_game_substitutes_zero_direct(callback: CallbackQuery, state: FSMContext):
    """Установка 0 запасных напрямую"""
    try:
        game_id = int(callback.data.split("_")[-1])
        
        success = await GameRepository.update_game(game_id, max_substitutes=0)
        
        if success:
            text = """✅ **Запасные игроки изменены!**

**Новое значение:** 0 (без запасных)"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="👁️ Просмотр игры",
                        callback_data=f"admin:view_game_{game_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 К списку игр",
                        callback_data="admin:list_games"
                    )
                ]
            ]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            await state.clear()
        else:
            await callback.answer("❌ Ошибка обновления", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка установки запасных: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(AdminStates.editing_game_max_substitutes))
async def process_edit_game_substitutes(message: Message, state: FSMContext):
    """Обработка нового количества запасных"""
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите число от 0 до 10.")
        return
    
    max_substitutes = int(message.text.strip())
    
    if max_substitutes < 0 or max_substitutes > 10:
        await message.answer("❌ Количество должно быть от 0 до 10.\n\nПопробуйте ещё раз:")
        return
    
    try:
        data = await state.get_data()
        game_id = data.get('editing_game_id')
        
        # Обновляем количество запасных
        success = await GameRepository.update_game(game_id, max_substitutes=max_substitutes)
        
        if success:
            text = f"""✅ **Запасные игроки изменены!**

**Новое значение:** {max_substitutes} 🔄"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="👁️ Просмотр игры",
                        callback_data=f"admin:view_game_{game_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 К списку игр",
                        callback_data="admin:list_games"
                    )
                ]
            ]
            
            await message.answer(
                text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            await state.clear()
        else:
            await message.answer("❌ Ошибка обновления игры. Попробуйте позже.")
            
    except Exception as e:
        logger.error(f"Ошибка обновления запасных: {e}")
        await message.answer("❌ Произошла ошибка при обновлении.")


# ========== УДАЛЕНИЕ ИГРЫ ==========

@router.callback_query(F.data.startswith("admin:confirm_delete_game_"))
async def confirm_delete_game(callback: CallbackQuery, state: FSMContext):
    """Подтверждение удаления игры"""
    try:
        game_id = int(callback.data.split("_")[-1])
        game = await GameRepository.get_by_id(game_id)
        
        if not game:
            await callback.answer("❌ Игра не найдена", show_alert=True)
            return
        
        text = f"""⚠️ **Подтверждение удаления**

Вы действительно хотите удалить игру **{game.name}**?

⚠️ Это действие необратимо!
⚠️ Турниры с этой игрой могут стать недоступными!"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"admin:delete_game_confirmed_{game_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"admin:view_game_{game_id}"
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


@router.callback_query(F.data.startswith("admin:delete_game_confirmed_"))
async def delete_game_confirmed(callback: CallbackQuery, state: FSMContext):
    """Окончательное удаление игры"""
    try:
        game_id = int(callback.data.split("_")[-1])
        game = await GameRepository.get_by_id(game_id)
        
        if not game:
            await callback.answer("❌ Игра не найдена", show_alert=True)
            return
        
        game_name = game.name
        success = await GameRepository.delete_game(game_id)
        
        if success:
            text = f"""✅ **Игра удалена**

Игра **{game_name}** была успешно удалена из системы."""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="📋 К списку игр",
                        callback_data="admin:list_games"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏆 К турнирам",
                        callback_data="admin:tournaments"
                    )
                ]
            ]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            await state.clear()
            logger.info(f"Игра удалена: ID={game_id}, название={game_name}")
        else:
            await callback.answer("❌ Ошибка удаления", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка удаления игры: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)