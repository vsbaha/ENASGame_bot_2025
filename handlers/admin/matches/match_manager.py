"""
Управление матчами турниров
Функции:
- Просмотр активных матчей
- Ввод результатов
- Обновление в Challonge
- История изменений
"""
import logging
from typing import Optional

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from database.repositories import TournamentRepository, MatchRepository, TeamRepository
from database.models import MatchStatus, TournamentStatus
from integrations.challonge_api import ChallongeAPI
from config import settings
from handlers.admin.states import AdminStates

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("admin:manage_matches_"))
async def manage_matches_redirect(callback: CallbackQuery, state: FSMContext):
    """Перенаправление на список матчей"""
    tournament_id = callback.data.split("_")[2]
    # Перенаправляем на show_matches
    callback.data = f"admin:show_matches_{tournament_id}"
    await show_tournament_matches(callback, state)


def get_matches_keyboard(tournament_id: int, matches: list, back_callback: str = None):
    """Создание клавиатуры со списком матчей"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = []
    
    if not matches:
        buttons.append([
            InlineKeyboardButton(
                text="📝 Нет доступных матчей",
                callback_data="noop"
            )
        ])
    else:
        # Группируем матчи по раундам
        matches_by_round = {}
        for match in matches:
            round_num = match.round_number
            if round_num not in matches_by_round:
                matches_by_round[round_num] = []
            matches_by_round[round_num].append(match)
        
        # Выводим матчи по раундам
        for round_num in sorted(matches_by_round.keys()):
            round_matches = matches_by_round[round_num]
            
            # Заголовок раунда
            round_name = get_round_name(round_num, len(matches_by_round))
            buttons.append([
                InlineKeyboardButton(
                    text=f"═══ {round_name} ═══",
                    callback_data="noop"
                )
            ])
            
            # Матчи раунда
            for match in round_matches:
                team1_name = match.team1.name if match.team1 else "TBD"
                team2_name = match.team2.name if match.team2 else "TBD"
                
                # Статус матча
                if match.status == MatchStatus.COMPLETED.value:
                    status_icon = "✅"
                    score = f"{match.team1_score or 0}:{match.team2_score or 0}"
                    text = f"{status_icon} {team1_name} {score} {team2_name}"
                else:
                    status_icon = "⏳"
                    text = f"{status_icon} {team1_name} vs {team2_name}"
                
                buttons.append([
                    InlineKeyboardButton(
                        text=text,
                        callback_data=f"admin:match_view_{match.id}"
                    )
                ])
    
    # Кнопка синхронизации
    buttons.append([
        InlineKeyboardButton(
            text="🔄 Синхронизировать с Challonge",
            callback_data=f"admin:sync_matches_{tournament_id}"
        )
    ])
    
    # Кнопка назад
    if back_callback:
        buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback)
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_round_name(round_number: int, total_rounds: int) -> str:
    """Получение названия раунда"""
    if round_number == total_rounds:
        return "🏆 Финал"
    elif round_number == total_rounds - 1:
        return "🥉 Полуфинал"
    elif round_number == total_rounds - 2:
        return "🎯 Четвертьфинал"
    else:
        return f"Раунд {round_number}"


def get_match_detail_keyboard(match_id: int, tournament_id: int):
    """Клавиатура для детального просмотра матча"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = [
        [
            InlineKeyboardButton(
                text="✏️ Ввести результат",
                callback_data=f"admin:enter_result_{match_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ К списку матчей",
                callback_data=f"admin:show_matches_{tournament_id}"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_score_input_keyboard(match_id: int):
    """Клавиатура для ввода счета"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = [
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"admin:match_view_{match_id}"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_score_confirmation_keyboard(match_id: int, tournament_id: int):
    """Клавиатура подтверждения результата"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"admin:confirm_result_{match_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Изменить счет",
                callback_data=f"admin:enter_result_{match_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"admin:match_view_{match_id}"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data.startswith("admin:show_matches_"))
async def show_tournament_matches(callback: CallbackQuery, state: FSMContext):
    """Отображение списка матчей турнира"""
    await callback.answer()
    
    try:
        tournament_id = int(callback.data.split("_")[2])
        
        # Получаем турнир
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.message.edit_text("❌ Турнир не найден")
            return
        
        # Получаем незавершенные матчи
        pending_matches = await MatchRepository.get_pending_matches(tournament_id)
        
        if not pending_matches and tournament.status != TournamentStatus.IN_PROGRESS.value:
            await callback.message.edit_text(
                "⚠️ Матчи будут доступны после запуска турнира.",
                reply_markup=get_matches_keyboard(
                    tournament_id, 
                    [], 
                    f"admin:tournament_action_{tournament_id}"
                )
            )
            return
        
        # Если нет активных матчей, показываем все
        if not pending_matches:
            all_matches = await MatchRepository.get_tournament_matches(tournament_id)
            text = f"🏆 **{tournament.name}**\n\n📊 Все матчи турнира:"
            keyboard = get_matches_keyboard(
                tournament_id, 
                all_matches, 
                f"admin:tournament_action_{tournament_id}"
            )
        else:
            text = f"🏆 **{tournament.name}**\n\n⏳ Активные матчи:"
            keyboard = get_matches_keyboard(
                tournament_id, 
                pending_matches, 
                f"admin:tournament_action_{tournament_id}"
            )
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка отображения матчей: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("admin:match_view_"))
async def view_match_details(callback: CallbackQuery, state: FSMContext):
    """Детальный просмотр матча"""
    await callback.answer()
    
    try:
        match_id = int(callback.data.split("_")[2])
        
        match = await MatchRepository.get_by_id(match_id)
        if not match:
            await callback.message.edit_text("❌ Матч не найден")
            return
        
        # Формируем текст
        team1_name = match.team1.name if match.team1 else "TBD"
        team2_name = match.team2.name if match.team2 else "TBD"
        
        text = f"🎮 **Матч #{match.match_number}**\n"
        text += f"📍 Раунд {match.round_number}\n\n"
        
        text += f"🔵 **{team1_name}**"
        if match.status == MatchStatus.COMPLETED.value:
            text += f" — **{match.team1_score or 0}**"
        text += "\n"
        
        text += f"🔴 **{team2_name}**"
        if match.status == MatchStatus.COMPLETED.value:
            text += f" — **{match.team2_score or 0}**"
        text += "\n\n"
        
        # Статус
        if match.status == MatchStatus.COMPLETED.value:
            winner_name = match.winner.name if match.winner else "Неизвестно"
            text += f"✅ **Завершен**\n"
            text += f"🏆 Победитель: **{winner_name}**"
        elif match.status == MatchStatus.PENDING.value:
            text += "⏳ **Ожидает результата**"
        else:
            text += f"📌 Статус: {match.status}"
        
        keyboard = get_match_detail_keyboard(match_id, match.tournament_id)
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка просмотра матча: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("admin:enter_result_"))
async def start_enter_result(callback: CallbackQuery, state: FSMContext):
    """Начало ввода результата матча"""
    await callback.answer()
    
    try:
        match_id = int(callback.data.split("_")[2])
        
        match = await MatchRepository.get_by_id(match_id)
        if not match:
            await callback.message.edit_text("❌ Матч не найден")
            return
        
        if not match.team1 or not match.team2:
            await callback.message.edit_text(
                "⚠️ Невозможно ввести результат: не определены обе команды"
            )
            return
        
        # Сохраняем match_id в состояние
        await state.update_data(match_id=match_id)
        await state.set_state(AdminStates.entering_team1_score)
        
        team1_name = match.team1.name
        team2_name = match.team2.name
        
        text = f"🎮 **Ввод результата матча**\n\n"
        text += f"🔵 {team1_name}\n"
        text += f"🔴 {team2_name}\n\n"
        text += f"Введите счет для **{team1_name}**:"
        
        await callback.message.edit_text(
            text, 
            reply_markup=get_score_input_keyboard(match_id)
        )
        
    except Exception as e:
        logger.error(f"Ошибка начала ввода результата: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")


@router.message(StateFilter(AdminStates.entering_team1_score))
async def process_team1_score(message: Message, state: FSMContext):
    """Обработка ввода счета первой команды"""
    try:
        score = int(message.text.strip())
        if score < 0:
            await message.answer("⚠️ Счет не может быть отрицательным. Попробуйте снова:")
            return
        
        # Сохраняем счет
        await state.update_data(team1_score=score)
        
        # Получаем данные матча
        data = await state.get_data()
        match_id = data.get("match_id")
        
        match = await MatchRepository.get_by_id(match_id)
        team2_name = match.team2.name
        
        await state.set_state(AdminStates.entering_team2_score)
        await message.answer(f"Теперь введите счет для **{team2_name}**:")
        
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите число:")
    except Exception as e:
        logger.error(f"Ошибка обработки счета команды 1: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(StateFilter(AdminStates.entering_team2_score))
async def process_team2_score(message: Message, state: FSMContext):
    """Обработка ввода счета второй команды"""
    try:
        score = int(message.text.strip())
        if score < 0:
            await message.answer("⚠️ Счет не может быть отрицательным. Попробуйте снова:")
            return
        
        # Сохраняем счет
        await state.update_data(team2_score=score)
        
        # Получаем все данные
        data = await state.get_data()
        match_id = data.get("match_id")
        team1_score = data.get("team1_score")
        team2_score = score
        
        match = await MatchRepository.get_by_id(match_id)
        
        # Определяем победителя
        if team1_score > team2_score:
            winner = match.team1
        elif team2_score > team1_score:
            winner = match.team2
        else:
            await message.answer("⚠️ Счет не может быть равным. Введите счет для второй команды снова:")
            return
        
        # Сохраняем winner_id
        await state.update_data(winner_id=winner.id)
        
        # Показываем подтверждение
        text = f"🎮 **Подтверждение результата**\n\n"
        text += f"🔵 **{match.team1.name}** — **{team1_score}**\n"
        text += f"🔴 **{match.team2.name}** — **{team2_score}**\n\n"
        text += f"🏆 Победитель: **{winner.name}**\n\n"
        text += "Подтвердите результат:"
        
        await message.answer(
            text,
            reply_markup=get_score_confirmation_keyboard(match_id, match.tournament_id)
        )
        
        await state.set_state(AdminStates.confirming_match_result)
        
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите число:")
    except Exception as e:
        logger.error(f"Ошибка обработки счета команды 2: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("admin:confirm_result_"))
async def confirm_match_result(callback: CallbackQuery, state: FSMContext):
    """Подтверждение результата матча"""
    await callback.answer("⏳ Сохранение результата...")
    
    try:
        match_id = int(callback.data.split("_")[2])
        
        # Получаем данные из состояния
        data = await state.get_data()
        team1_score = data.get("team1_score")
        team2_score = data.get("team2_score")
        winner_id = data.get("winner_id")
        
        if not all([team1_score is not None, team2_score is not None, winner_id]):
            await callback.message.edit_text("❌ Ошибка: данные результата не найдены")
            return
        
        match = await MatchRepository.get_by_id(match_id)
        tournament = await TournamentRepository.get_by_id(match.tournament_id)
        
        # Обновляем результат в БД
        updated_match = await MatchRepository.update_match_score(
            match_id=match_id,
            team1_score=team1_score,
            team2_score=team2_score,
            winner_id=winner_id
        )
        
        # Обновляем результат в Challonge (если есть)
        if tournament.challonge_id and match.challonge_match_id:
            challonge = ChallongeAPI(settings.challonge_api_key, settings.challonge_username)
            
            # Получаем participant_id победителя из Challonge
            participants = await challonge.get_participants(tournament.challonge_id)
            winner = await TeamRepository.get_by_id(winner_id)
            
            winner_participant_id = None
            for participant in participants:
                p_data = participant.get("participant", participant)
                if p_data.get("name") == winner.name:
                    winner_participant_id = str(p_data["id"])
                    break
            
            if winner_participant_id:
                scores_csv = f"{team1_score}-{team2_score}"
                success = await challonge.update_match_score(
                    tournament_id=tournament.challonge_id,
                    match_id=match.challonge_match_id,
                    winner_id=winner_participant_id,
                    scores_csv=scores_csv
                )
                
                if success:
                    logger.info(f"Результат обновлен в Challonge: {scores_csv}")
        
        # Очищаем состояние
        await state.clear()
        
        # Показываем результат
        text = f"✅ **Результат сохранен!**\n\n"
        text += f"🔵 {updated_match.team1.name} — {team1_score}\n"
        text += f"🔴 {updated_match.team2.name} — {team2_score}\n\n"
        text += f"🏆 Победитель: **{updated_match.winner.name}**"
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="◀️ К списку матчей",
                    callback_data=f"admin:show_matches_{tournament.id}"
                )
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка подтверждения результата: {e}")
        await callback.message.edit_text(f"❌ Ошибка сохранения: {str(e)}")
        await state.clear()


@router.callback_query(F.data.startswith("admin:sync_matches_"))
async def sync_matches_from_challonge(callback: CallbackQuery, state: FSMContext):
    """Синхронизация матчей из Challonge"""
    await callback.answer("⏳ Синхронизация...")
    
    try:
        tournament_id = int(callback.data.split("_")[2])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament or not tournament.challonge_id:
            await callback.answer("⚠️ Турнир не создан в Challonge", show_alert=True)
            return
        
        # Получаем матчи из Challonge
        challonge = ChallongeAPI(settings.challonge_api_key, settings.challonge_username)
        challonge_matches = await challonge.get_matches(tournament.challonge_id)
        
        if not challonge_matches:
            await callback.answer("⚠️ Матчи не найдены в Challonge", show_alert=True)
            return
        
        # Синхронизируем матчи
        synced_matches = await MatchRepository.sync_matches_from_challonge(
            tournament_id=tournament_id,
            challonge_matches=challonge_matches
        )
        
        await callback.answer(
            f"✅ Синхронизировано {len(synced_matches)} матчей", 
            show_alert=True
        )
        
        # Обновляем отображение
        await show_tournament_matches(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка синхронизации матчей: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
