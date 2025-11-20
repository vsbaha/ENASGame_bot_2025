"""
Редактор турнирной сетки
Позволяет админам менять команды местами до начала турнира
"""
import logging
from typing import List, Dict, Any

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database.repositories import TournamentRepository, TeamRepository
from database.models import TournamentStatus
from integrations.challonge_api import ChallongeAPI
from config.settings import Settings
from utils.message_utils import safe_edit_message

logger = logging.getLogger(__name__)
router = Router()
settings = Settings()


def get_bracket_editor_keyboard(tournament_id: int, participants: List[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура редактора сетки"""
    buttons = []
    
    if not participants:
        buttons.append([
            InlineKeyboardButton(
                text="📝 Нет участников",
                callback_data="noop"
            )
        ])
    else:
        # Заголовок
        buttons.append([
            InlineKeyboardButton(
                text="═══ Участники сетки ═══",
                callback_data="noop"
            )
        ])
        
        # Кнопки выбора команд для обмена
        # API v2.1 возвращает данные напрямую
        for participant in participants[:20]:  # Максимум 20
            name = participant.get("name", "Unknown")
            seed = participant.get("seed", "?")
            participant_id = participant.get("id")
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"#{seed} {name}",
                    callback_data=f"admin:select_swap_team_{tournament_id}_{participant_id}"
                )
            ])
    
    # Кнопки управления
    buttons.append([
        InlineKeyboardButton(
            text="🔄 Обновить список",
            callback_data=f"admin:edit_bracket_{tournament_id}"
        )
    ])
    
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Назад к сетке",
            callback_data=f"admin:generate_bracket_{tournament_id}"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data.startswith("admin:edit_bracket_"))
async def show_bracket_editor(callback: CallbackQuery, state: FSMContext):
    """Показать редактор сетки"""
    await callback.answer()
    
    try:
        tournament_id = int(callback.data.split("_")[2])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.message.edit_text("❌ Турнир не найден")
            return
        
        # Проверка статуса турнира
        if tournament.status != TournamentStatus.REGISTRATION.value:
            text = f"""⚠️ **Редактирование недоступно**

Редактировать сетку можно только до запуска турнира.

**Текущий статус:** {tournament.status}"""
            
            keyboard = [[
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=f"admin:generate_bracket_{tournament_id}"
                )
            ]]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            return
        
        # Проверка Challonge ID
        if not tournament.challonge_id:
            text = f"""⚠️ **Сетка не создана**

Сначала создайте турнир в Challonge.

Используйте: **"🆕 Создать в Challonge"**"""
            
            keyboard = [[
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=f"admin:generate_bracket_{tournament_id}"
                )
            ]]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            return
        
        # Получаем участников из Challonge
        challonge = ChallongeAPI(settings.challonge_client_id, settings.challonge_client_secret, settings.challonge_username)
        participants = await challonge.get_participants(tournament.challonge_id)
        
        if not participants:
            text = f"""⚠️ **Нет участников**

Добавьте команды через "👥 Синхронизировать участников"."""
            
            keyboard = [[
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=f"admin:generate_bracket_{tournament_id}"
                )
            ]]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            return
        
        # Очищаем состояние
        await state.clear()
        
        text = f"""✏️ **Редактор турнирной сетки**

**Турнир:** {tournament.name}
**Участников:** {len(participants)}

**Выберите команду** для обмена позициями:

_Выберите первую команду, затем вторую._
_Они поменяются местами в сетке._"""
        
        keyboard = get_bracket_editor_keyboard(tournament_id, participants)
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка редактора сетки: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("admin:select_swap_team_"))
async def select_team_for_swap(callback: CallbackQuery, state: FSMContext):
    """Выбор команды для обмена"""
    await callback.answer()
    
    try:
        parts = callback.data.split("_")
        tournament_id = int(parts[3])
        participant_id = int(parts[4])
        
        # Получаем данные из состояния
        data = await state.get_data()
        first_participant_id = data.get("first_swap_participant_id")
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament or not tournament.challonge_id:
            await callback.answer("❌ Ошибка: турнир не найден", show_alert=True)
            return
        
        challonge = ChallongeAPI(settings.challonge_client_id, settings.challonge_client_secret, settings.challonge_username)
        participants = await challonge.get_participants(tournament.challonge_id)
        
        # Находим выбранного участника
        # API v2.1 возвращает данные напрямую
        selected_participant = None
        for p in participants:
            if p.get("id") == participant_id:
                selected_participant = p
                break
        
        if not selected_participant:
            await callback.answer("❌ Участник не найден", show_alert=True)
            return
        
        if not first_participant_id:
            # Это первый выбор
            await state.update_data(
                first_swap_participant_id=participant_id,
                first_swap_participant_name=selected_participant.get("name"),
                first_swap_participant_seed=selected_participant.get("seed")
            )
            
            text = f"""✏️ **Редактор турнирной сетки**

**Турнир:** {tournament.name}

**Выбрана первая команда:**
🔵 #{selected_participant.get('seed')} **{selected_participant.get('name')}**

**Теперь выберите вторую команду** для обмена позициями:"""
            
            # Обновляем клавиатуру с выделением выбранной команды
            keyboard_buttons = []
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="═══ Участники сетки ═══",
                    callback_data="noop"
                )
            ])
            
            # API v2.1 возвращает данные напрямую
            for participant in participants[:20]:
                name = participant.get("name", "Unknown")
                seed = participant.get("seed", "?")
                pid = participant.get("id")
                
                # Выделяем выбранную команду
                if pid == participant_id:
                    button_text = f"🔵 #{seed} {name} ✓"
                else:
                    button_text = f"#{seed} {name}"
                
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"admin:select_swap_team_{tournament_id}_{pid}"
                    )
                ])
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"admin:edit_bracket_{tournament_id}"
                )
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=keyboard
            )
            
        else:
            # Это второй выбор - выполняем обмен
            if first_participant_id == participant_id:
                await callback.answer("⚠️ Нельзя выбрать ту же команду", show_alert=True)
                return
            
            first_name = data.get("first_swap_participant_name")
            first_seed = data.get("first_swap_participant_seed")
            second_name = selected_participant.get("name")
            second_seed = selected_participant.get("seed")
            
            # Выполняем обмен seed'ов в Challonge
            success = await challonge.swap_participants(
                tournament.challonge_id,
                first_participant_id,
                participant_id
            )
            
            if success:
                await state.clear()
                
                text = f"""✅ **Обмен выполнен!**

**Турнир:** {tournament.name}

🔵 #{first_seed} **{first_name}**
🔄
🔴 #{second_seed} **{second_name}**

Позиции команд обменены в сетке."""
                
                keyboard = [
                    [
                        InlineKeyboardButton(
                            text="✏️ Продолжить редактирование",
                            callback_data=f"admin:edit_bracket_{tournament_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔙 Назад к сетке",
                            callback_data=f"admin:generate_bracket_{tournament_id}"
                        )
                    ]
                ]
                
                await safe_edit_message(
                    callback.message, text, parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
            else:
                await callback.answer("❌ Ошибка обмена команд", show_alert=True)
                await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка выбора команды для обмена: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        await state.clear()
