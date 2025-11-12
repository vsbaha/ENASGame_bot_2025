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
from ..states import AdminStates

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("admin:edit_game_"))
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
            text = "❌ **Нет доступных игр**\n\nСначала добавьте игры в систему."
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
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            await callback.answer()
            return
        
        await state.update_data(editing_tournament_id=tournament_id)
        
        text = f"""🎮 **Изменение игры турнира**

**Турнир:** {tournament.name}
**Текущая игра:** {tournament.game.name if hasattr(tournament, 'game') and tournament.game else 'N/A'}

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
            callback.message, text, parse_mode="Markdown",
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
        
        text = f"""🏆 **Изменение формата турнира**

**Турнир:** {tournament.name}
**Текущий формат:** {tournament.format}

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
            callback.message, text, parse_mode="Markdown",
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

**Текущие даты:**
📅 Регистрация: {tournament.registration_start.strftime('%d.%m.%Y %H:%M')} - {tournament.registration_end.strftime('%d.%m.%Y %H:%M')}
🏁 Начало турнира: {tournament.tournament_start.strftime('%d.%m.%Y %H:%M')}

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
            callback.message, text, parse_mode="Markdown",
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
        
        text = f"""📢 **Редактирование обязательных каналов**

**Турнир:** {tournament.name}

**Текущие каналы:** {len(channels)}
"""
        
        if channels:
            text += "\n"
            for i, channel in enumerate(channels, 1):
                text += f"{i}. {channel}\n"
        else:
            text += "\n_Нет обязательных каналов_\n"
        
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
            callback.message, text, parse_mode="Markdown",
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
        
        text = f"""➕ **Добавление канала**

**Турнир:** {tournament.name}

Отправьте ссылку на канал или username:

**Примеры:**
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
            callback.message, text, parse_mode="Markdown",
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
            await message.answer(f"✅ Канал {channel} добавлен!")
            await state.clear()
            
            # Показываем обновленный список
            text = f"""📢 **Обязательные каналы обновлены**

**Турнир:** {tournament.name}
**Всего каналов:** {len(current_channels)}

"""
            for i, ch in enumerate(current_channels, 1):
                text += f"{i}. {ch}\n"
            
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
                parse_mode="Markdown",
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
                # Обновляем отображение
                callback.data = f"admin:edit_required_channels_{tournament_id}"
                await edit_required_channels_start(callback, state)
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
            callback.data = f"admin:edit_required_channels_{tournament_id}"
            await edit_required_channels_start(callback, state)
        else:
            await callback.answer("❌ Ошибка очистки", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка очистки каналов: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)