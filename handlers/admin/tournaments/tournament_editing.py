"""
Дополнительные обработчики для редактирования турниров
"""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database.repositories import TournamentRepository, GameRepository
from utils.message_utils import safe_edit_message
from utils.datetime_utils import format_datetime_for_user
from ..states import AdminStates

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("admin:edit_tournament_game_"))
async def edit_tournament_game_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование игры турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Получаем список игр
        games = await GameRepository.get_all_games()
        
        if not games:
            text = "❌ <b>Нет доступных игр</b>\n\nСначала добавьте игры в систему."
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
                        callback_data=f"admin:edit_tournament_details_{tournament_id}"
                    )
                ]
            ]
            
            await safe_edit_message(
                callback.message, text, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            await callback.answer()
            return
        
        await state.update_data(editing_tournament_id=tournament_id)
        
        tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        game_name = tournament.game.name if hasattr(tournament, 'game') and tournament.game else 'N/A'
        game_name = game_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        text = f"""🎮 <b>Изменение игры турнира</b>

<b>Турнир:</b> {tournament_name}
<b>Текущая игра:</b> {game_name}

Выберите новую игру:"""
        
        keyboard = []
        for game in games[:10]:  # Показываем первые 10
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🎮 {game.name}",
                    callback_data=f"admin:select_new_game_{tournament_id}_{game.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 Отменить",
                callback_data=f"admin:edit_tournament_details_{tournament_id}"
            )
        ])
        
        await safe_edit_message(
            callback.message, text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка редактирования игры турнира: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:select_new_game_"))
async def select_new_game_for_tournament(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выбора новой игры"""
    try:
        parts = callback.data.split("_")
        tournament_id = int(parts[-2])
        game_id = int(parts[-1])
        
        # Получаем информацию об игре
        game = await GameRepository.get_by_id(game_id)
        
        if not game:
            await callback.answer("❌ Игра не найдена", show_alert=True)
            return
        
        # Обновляем игру турнира
        success = await TournamentRepository.update_game(tournament_id, game_id)
        
        if success:
            await callback.answer("✅ Игра обновлена!", show_alert=True)
            # Возвращаемся к меню редактирования
            from .tournament_management import edit_tournament_details_menu
            callback.data = f"admin:edit_tournament_details_{tournament_id}"
            await edit_tournament_details_menu(callback, state)
        else:
            await callback.answer("❌ Ошибка обновления игры", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка выбора игры: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:edit_format_"))
async def edit_tournament_format_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование формата турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        await state.update_data(editing_tournament_id=tournament_id)
        
        tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        text = f"""🏆 <b>Изменение формата турнира</b>

<b>Турнир:</b> {tournament_name}
<b>Текущий формат:</b> {tournament.format}

Выберите новый формат:"""
        
        formats = [
            ("single", "🥇 Одиночное исключение"),
            ("double", "🥈 Двойное исключение"),
            ("round_robin", "⚽ Круговой турнир"),
            ("group_playoffs", "📊 Групповой этап + плей-офф")
        ]
        
        keyboard = []
        for format_key, format_name in formats:
            keyboard.append([
                InlineKeyboardButton(
                    text=format_name,
                    callback_data=f"admin:select_new_format_{tournament_id}_{format_key}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 Отменить",
                callback_data=f"admin:edit_tournament_details_{tournament_id}"
            )
        ])
        
        await safe_edit_message(
            callback.message, text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка редактирования формата турнира: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:select_new_format_"))
async def select_new_format_for_tournament(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выбора нового формата"""
    try:
        parts = callback.data.split("_")
        tournament_id = int(parts[-2])
        new_format = parts[-1]
        
        # Обновляем формат турнира
        success = await TournamentRepository.update_format(tournament_id, new_format)
        
        if success:
            format_names = {
                "single": "Одиночное исключение",
                "double": "Двойное исключение", 
                "round_robin": "Круговой турнир",
                "group_playoffs": "Групповой этап + плей-офф"
            }
            
            await callback.answer(f"✅ Формат изменен на: {format_names.get(new_format, new_format)}", show_alert=True)
            # Возвращаемся к меню редактирования
            from .tournament_management import edit_tournament_details_menu
            callback.data = f"admin:edit_tournament_details_{tournament_id}"
            await edit_tournament_details_menu(callback, state)
        else:
            await callback.answer("❌ Ошибка обновления формата", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка выбора формата: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:edit_dates_"))
async def edit_tournament_dates_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование дат турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        await state.update_data(editing_tournament_id=tournament_id)
        
        text = f"""📅 **Изменение дат турнира**

**Турнир:** {tournament.name}

**Текущие даты (UTC):**
📅 Регистрация: {format_datetime_for_user(tournament.registration_start, 'UTC')} - {format_datetime_for_user(tournament.registration_end, 'UTC')}
🏁 Начало турнира: {format_datetime_for_user(tournament.tournament_start, 'UTC')}

Что хотите изменить?"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📅 Начало регистрации",
                    callback_data=f"admin:edit_reg_start_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Конец регистрации", 
                    callback_data=f"admin:edit_reg_end_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏁 Дата турнира",
                    callback_data=f"admin:edit_tournament_date_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Отменить",
                    callback_data=f"admin:edit_tournament_details_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка редактирования дат турнира: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# Обработчики для отдельных дат можно добавить позже


@router.callback_query(F.data.startswith("admin:edit_required_channels_"))
async def edit_required_channels_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование обязательных каналов"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        await state.update_data(editing_tournament_id=tournament_id)
        
        # Получаем текущие каналы
        channels = tournament.required_channels_list
        
        tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        text = f"""📢 <b>Редактирование обязательных каналов</b>

<b>Турнир:</b> {tournament_name}

<b>Текущие каналы:</b> {len(channels)}
"""
        
        if channels:
            text += "\n"
            for i, channel in enumerate(channels, 1):
                channel_escaped = channel.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                text += f"{i}. {channel_escaped}\n"
        else:
            text += "\n<i>Нет обязательных каналов</i>\n"
        
        text += "\nВыберите действие:"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="➕ Добавить канал",
                    callback_data=f"admin:add_required_channel_{tournament_id}"
                )
            ]
        ]
        
        # Если есть каналы, показываем кнопки удаления
        if channels:
            for i, channel in enumerate(channels):
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"❌ Удалить: {channel}",
                        callback_data=f"admin:remove_channel_{tournament_id}_{i}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton(
                    text="🗑️ Очистить все",
                    callback_data=f"admin:clear_all_channels_{tournament_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=f"admin:edit_tournament_details_{tournament_id}"
            )
        ])
        
        await safe_edit_message(
            callback.message, text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка редактирования каналов: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:add_required_channel_"))
async def add_required_channel_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на добавление канала"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        await state.update_data(editing_tournament_id=tournament_id)
        await state.set_state(AdminStates.editing_tournament_required_channels)
        
        tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        text = f"""➕ <b>Добавление канала</b>

<b>Турнир:</b> {tournament_name}

Отправьте ссылку на канал или username:

<b>Примеры:</b>
• @channel_name
• https://t.me/channel_name
• t.me/channel_name

Или отправьте "отмена" для отмены."""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"admin:edit_required_channels_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка запроса добавления канала: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(AdminStates.editing_tournament_required_channels))
async def process_add_required_channel(message: Message, state: FSMContext):
    """Обработка добавления канала"""
    try:
        data = await state.get_data()
        tournament_id = data.get("editing_tournament_id")
        
        if not tournament_id:
            await message.answer("❌ Ошибка: турнир не найден")
            await state.clear()
            return
        
        # Проверка на отмену
        if message.text.lower() in ['отмена', 'cancel']:
            await state.clear()
            await message.answer("❌ Добавление канала отменено")
            return
        
        channel = message.text.strip()
        
        # Валидация формата канала
        if not (channel.startswith('@') or 't.me/' in channel or 'https://t.me/' in channel):
            await message.answer(
                "⚠️ Неверный формат канала!\n\n"
                "Используйте:\n"
                "• @channel_name\n"
                "• https://t.me/channel_name\n"
                "• t.me/channel_name"
            )
            return
        
        # Нормализация формата
        if 'https://t.me/' in channel:
            channel = '@' + channel.split('/')[-1]
        elif 't.me/' in channel:
            channel = '@' + channel.split('/')[-1]
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await message.answer("❌ Турнир не найден")
            await state.clear()
            return
        
        # Получаем текущие каналы
        current_channels = tournament.required_channels_list
        
        # Проверка на дубликат
        if channel in current_channels:
            await message.answer(f"⚠️ Канал {channel} уже добавлен!")
            return
        
        # Добавляем канал
        current_channels.append(channel)
        
        # Обновляем в БД
        success = await TournamentRepository.update_required_channels(
            tournament_id, 
            current_channels
        )
        
        if success:
            channel_escaped = channel.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            await message.answer(f"✅ Канал {channel_escaped} добавлен!", parse_mode="HTML")
            await state.clear()
            
            # Показываем обновленный список
            tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            text = f"""📢 <b>Обязательные каналы обновлены</b>

<b>Турнир:</b> {tournament_name}
<b>Всего каналов:</b> {len(current_channels)}

"""
            for i, ch in enumerate(current_channels, 1):
                ch_escaped = ch.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                text += f"{i}. {ch_escaped}\n"
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="➕ Добавить ещё",
                        callback_data=f"admin:add_required_channel_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✏️ Редактировать",
                        callback_data=f"admin:edit_required_channels_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data=f"admin:edit_tournament_details_{tournament_id}"
                    )
                ]
            ]
            
            await message.answer(
                text, 
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        else:
            await message.answer("❌ Ошибка сохранения канала")
            await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка обработки добавления канала: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


@router.callback_query(F.data.startswith("admin:remove_channel_"))
async def remove_required_channel(callback: CallbackQuery, state: FSMContext):
    """Удаление канала"""
    try:
        parts = callback.data.split("_")
        tournament_id = int(parts[-2])
        channel_index = int(parts[-1])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        current_channels = tournament.required_channels_list
        
        if 0 <= channel_index < len(current_channels):
            removed_channel = current_channels.pop(channel_index)
            
            # Обновляем в БД
            success = await TournamentRepository.update_required_channels(
                tournament_id, 
                current_channels
            )
            
            if success:
                await callback.answer(f"✅ Канал {removed_channel} удален", show_alert=True)
                # Обновляем отображение списка каналов
                tournament = await TournamentRepository.get_by_id(tournament_id)
                if tournament:
                    channels = tournament.required_channels_list
                    tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    
                    text = f"""📢 <b>Редактирование обязательных каналов</b>

<b>Турнир:</b> {tournament_name}

"""
                    
                    if channels:
                        text += f"<b>Текущие каналы</b> ({len(channels)}):\n\n"
                        for i, ch in enumerate(channels):
                            ch_escaped = ch.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                            text += f"{i+1}. {ch_escaped}\n"
                    else:
                        text += "\n<i>Нет обязательных каналов</i>\n"
                    
                    keyboard = []
                    
                    # Кнопки удаления каналов
                    if channels:
                        for i, ch in enumerate(channels):
                            ch_display = ch[:20] + "..." if len(ch) > 20 else ch
                            keyboard.append([
                                InlineKeyboardButton(
                                    text=f"❌ {ch_display}",
                                    callback_data=f"admin:remove_channel_{tournament_id}_{i}"
                                )
                            ])
                        keyboard.append([
                            InlineKeyboardButton(
                                text="🗑️ Очистить все",
                                callback_data=f"admin:clear_all_channels_{tournament_id}"
                            )
                        ])
                    
                    keyboard.extend([
                        [
                            InlineKeyboardButton(
                                text="➕ Добавить канал",
                                callback_data=f"admin:add_required_channel_{tournament_id}"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="🔙 Назад",
                                callback_data=f"admin:edit_tournament_details_{tournament_id}"
                            )
                        ]
                    ])
                    
                    await callback.message.edit_text(
                        text,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                    )
            else:
                await callback.answer("❌ Ошибка удаления", show_alert=True)
        else:
            await callback.answer("❌ Канал не найден", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка удаления канала: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:clear_all_channels_"))
async def clear_all_channels(callback: CallbackQuery, state: FSMContext):
    """Очистка всех каналов"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Обновляем в БД
        success = await TournamentRepository.update_required_channels(
            tournament_id, 
            []
        )
        
        if success:
            await callback.answer("✅ Все каналы удалены", show_alert=True)
            # Обновляем отображение
            tournament = await TournamentRepository.get_by_id(tournament_id)
            if tournament:
                tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                text = f"""📢 <b>Редактирование обязательных каналов</b>

<b>Турнир:</b> {tournament_name}

<i>Нет обязательных каналов</i>
"""
                
                keyboard = [
                    [
                        InlineKeyboardButton(
                            text="➕ Добавить канал",
                            callback_data=f"admin:add_required_channel_{tournament_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔙 Назад",
                            callback_data=f"admin:edit_tournament_details_{tournament_id}"
                        )
                    ]
                ]
                
                await callback.message.edit_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
        else:
            await callback.answer("❌ Ошибка очистки", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка очистки каналов: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:edit_name_"))
async def edit_tournament_name(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование названия турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        await state.update_data(editing_tournament_id=tournament_id)
        await state.set_state(AdminStates.editing_tournament_name)
        
        from utils.text_formatting import escape_html
        tournament_name = escape_html(tournament.name)
        
        text = f"""📝 <b>Изменение названия турнира</b>

<b>Текущее название:</b> {tournament_name}

Введите новое название турнира:"""
        
        keyboard = [[
            InlineKeyboardButton(
                text="🔙 Отмена",
                callback_data=f"admin:edit_tournament_details_{tournament_id}"
            )
        ]]
        
        await safe_edit_message(
            callback.message, text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала редактирования названия: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(AdminStates.editing_tournament_name))
async def process_tournament_name_edit(message: Message, state: FSMContext):
    """Обработка нового названия турнира"""
    try:
        data = await state.get_data()
        tournament_id = data.get('editing_tournament_id')
        
        if not tournament_id:
            await message.answer("❌ Ошибка: турнир не найден")
            await state.clear()
            return
        
        new_name = message.text.strip()
        
        if len(new_name) < 3:
            await message.answer("❌ Название должно быть не менее 3 символов")
            return
        
        if len(new_name) > 100:
            await message.answer("❌ Название слишком длинное (максимум 100 символов)")
            return
        
        # Обновляем название
        await TournamentRepository.update_tournament(tournament_id, name=new_name)
        
        from utils.text_formatting import escape_html
        safe_name = escape_html(new_name)
        
        text = f"""✅ <b>Название изменено</b>

<b>Новое название:</b> {safe_name}"""
        
        keyboard = [[
            InlineKeyboardButton(
                text="🔙 К редактированию",
                callback_data=f"admin:edit_tournament_details_{tournament_id}"
            )
        ]]
        
        await message.answer(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка сохранения названия: {e}")
        await message.answer("❌ Ошибка при сохранении")
        await state.clear()


@router.callback_query(F.data.startswith("admin:edit_description_"))
async def edit_tournament_description(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование описания турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        await state.update_data(editing_tournament_id=tournament_id)
        await state.set_state(AdminStates.editing_tournament_description)
        
        from utils.text_formatting import escape_html
        current_desc = escape_html(tournament.description) if tournament.description else "Не указано"
        
        text = f"""📄 <b>Изменение описания турнира</b>

<b>Текущее описание:</b>
{current_desc}

Введите новое описание турнира:"""
        
        keyboard = [[
            InlineKeyboardButton(
                text="🔙 Отмена",
                callback_data=f"admin:edit_tournament_details_{tournament_id}"
            )
        ]]
        
        await safe_edit_message(
            callback.message, text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала редактирования описания: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(AdminStates.editing_tournament_description))
async def process_tournament_description_edit(message: Message, state: FSMContext):
    """Обработка нового описания турнира"""
    try:
        data = await state.get_data()
        tournament_id = data.get('editing_tournament_id')
        
        if not tournament_id:
            await message.answer("❌ Ошибка: турнир не найден")
            await state.clear()
            return
        
        new_description = message.text.strip()
        
        if len(new_description) > 1000:
            await message.answer("❌ Описание слишком длинное (максимум 1000 символов)")
            return
        
        # Обновляем описание
        await TournamentRepository.update_tournament(tournament_id, description=new_description)
        
        from utils.text_formatting import escape_html
        safe_desc = escape_html(new_description)
        if len(safe_desc) > 200:
            safe_desc = safe_desc[:200] + "..."
        
        text = f"""✅ <b>Описание изменено</b>

<b>Новое описание:</b>
{safe_desc}"""
        
        keyboard = [[
            InlineKeyboardButton(
                text="🔙 К редактированию",
                callback_data=f"admin:edit_tournament_details_{tournament_id}"
            )
        ]]
        
        await message.answer(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка сохранения описания: {e}")
        await message.answer("❌ Ошибка при сохранении")
        await state.clear()


@router.callback_query(F.data.startswith("admin:edit_max_teams_"))
async def edit_tournament_max_teams(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование максимального количества команд"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        await state.update_data(editing_tournament_id=tournament_id)
        await state.set_state(AdminStates.editing_tournament_max_teams)
        
        text = f"""👥 <b>Изменение максимального количества команд</b>

<b>Текущее значение:</b> {tournament.max_teams}

Введите новое количество команд (от 2 до 128):"""
        
        keyboard = [[
            InlineKeyboardButton(
                text="🔙 Отмена",
                callback_data=f"admin:edit_tournament_details_{tournament_id}"
            )
        ]]
        
        await safe_edit_message(
            callback.message, text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала редактирования макс. команд: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(AdminStates.editing_tournament_max_teams))
async def process_tournament_max_teams_edit(message: Message, state: FSMContext):
    """Обработка нового максимального количества команд"""
    try:
        data = await state.get_data()
        tournament_id = data.get('editing_tournament_id')
        
        if not tournament_id:
            await message.answer("❌ Ошибка: турнир не найден")
            await state.clear()
            return
        
        try:
            new_max_teams = int(message.text.strip())
        except ValueError:
            await message.answer("❌ Введите корректное число")
            return
        
        if new_max_teams < 2 or new_max_teams > 128:
            await message.answer("❌ Количество команд должно быть от 2 до 128")
            return
        
        # Обновляем максимальное количество команд
        await TournamentRepository.update_tournament(tournament_id, max_teams=new_max_teams)
        
        text = f"""✅ <b>Максимальное количество команд изменено</b>

<b>Новое значение:</b> {new_max_teams}"""
        
        keyboard = [[
            InlineKeyboardButton(
                text="🔙 К редактированию",
                callback_data=f"admin:edit_tournament_details_{tournament_id}"
            )
        ]]
        
        await message.answer(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка сохранения макс. команд: {e}")
        await message.answer("❌ Ошибка при сохранении")
        await state.clear()