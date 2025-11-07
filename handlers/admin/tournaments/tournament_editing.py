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