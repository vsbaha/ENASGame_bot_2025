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
from database.models import MatchStatus, TournamentStatus, TeamStatus
from integrations.challonge_api import ChallongeAPI
from config.settings import settings
from handlers.admin.states import AdminStates

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("admin:manage_matches_"))
async def manage_matches_redirect(callback: CallbackQuery, state: FSMContext):
    """Перенаправление на список матчей"""
    await callback.answer()
    
    try:
        tournament_id = int(callback.data.split("_")[2])
        await display_tournament_matches(callback, tournament_id)
    except Exception as e:
        logger.error(f"Ошибка отображения матчей: {e}")
        from utils.message_utils import safe_edit_message
        await safe_edit_message(callback.message, "❌ Ошибка загрузки матчей")


def get_matches_keyboard(tournament_id: int, matches: list, back_callback: str = None, tournament_format: str = 'single_elimination'):
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
        # Группируем матчи по раундам и bracket_type (для Double Elimination)
        matches_by_round = {}
        for match in matches:
            round_num = match.round_number
            bracket_type = getattr(match, 'bracket_type', 'winner') or 'winner'
            
            # Ключ: (bracket_type, round_number) для разделения WB и LB
            key = (bracket_type, round_num)
            if key not in matches_by_round:
                matches_by_round[key] = []
            matches_by_round[key].append(match)
        
        # Сортируем: сначала Winner Bracket, потом Loser Bracket
        sorted_keys = sorted(matches_by_round.keys(), key=lambda x: (0 if x[0] == 'winner' else 1, x[1]))
        
        # Выводим матчи по раундам
        for key in sorted_keys:
            bracket_type, round_num = key
            round_matches = matches_by_round[key]
            
            # Фильтруем только матчи, где назначены обе команды
            ready_matches = [m for m in round_matches if m.team1_id and m.team2_id]
            
            # Если нет готовых матчей, пропускаем раунд
            if not ready_matches:
                continue
            
            # Заголовок раунда
            round_name = get_round_name(round_num, len(matches_by_round), tournament_format, bracket_type)
            buttons.append([
                InlineKeyboardButton(
                    text=f"━━━ {round_name} ━━━",
                    callback_data="noop"
                )
            ])
            
            # Матчи раунда
            for match in ready_matches:
                team1_name = match.team1.name if match.team1 else "?"
                team2_name = match.team2.name if match.team2 else "?"
                
                # Статус матча
                if match.status == MatchStatus.COMPLETED.value:
                    status_icon = "✅"
                    score = f"{match.team1_score or 0}:{match.team2_score or 0}"
                    text = f"{status_icon} {team1_name} {score} {team2_name}"
                elif match.status == MatchStatus.CANCELLED.value:
                    status_icon = "❌"
                    text = f"{status_icon} {team1_name} — {team2_name}"
                else:
                    # Проверяем, назначены ли обе команды
                    if match.team1_id and match.team2_id:
                        status_icon = "🎮"  # Готов к игре
                    else:
                        status_icon = "⏳"  # Ожидание
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


def get_round_name(round_number: int, total_rounds: int, tournament_format: str = 'single_elimination', bracket_type: str = None) -> str:
    """Получение названия раунда с учётом формата турнира"""
    from utils.bracket_formatter import (
        get_round_name_single_elimination,
        get_round_name_double_elimination,
        get_round_name_round_robin,
        get_round_name_swiss
    )
    
    if tournament_format == 'double_elimination':
        return get_round_name_double_elimination(round_number, bracket_type)
    elif tournament_format == 'round_robin':
        return get_round_name_round_robin(round_number)
    elif tournament_format == 'swiss':
        return get_round_name_swiss(round_number, total_rounds)
    else:  # single_elimination или по умолчанию
        return get_round_name_single_elimination(round_number, total_rounds)


def get_match_detail_keyboard(match_id: int, tournament_id: int, match_status: str = None):
    """Клавиатура для детального просмотра матча"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from database.models import MatchStatus
    
    buttons = []
    
    # Кнопка ввода результата только для незавершенных матчей
    if match_status != MatchStatus.COMPLETED.value:
        buttons.append([
            InlineKeyboardButton(
                text="📝 Ввести результат",
                callback_data=f"admin:enter_result_{match_id}"
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                text="✏️ Изменить результат",
                callback_data=f"admin:enter_result_{match_id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="◀️ К списку матчей",
            callback_data=f"admin:show_matches_{tournament_id}"
        )
    ])
    
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


async def display_tournament_matches(callback: CallbackQuery, tournament_id: int):
    """Helper функция для отображения списка матчей"""
    from utils.message_utils import safe_edit_message
    
    # Получаем турнир
    tournament = await TournamentRepository.get_by_id(tournament_id)
    if not tournament:
        await safe_edit_message(callback.message, "❌ Турнир не найден")
        return
    
    # Автосинхронизация матчей из Challonge (если турнир активен)
    if tournament.challonge_id and tournament.status == TournamentStatus.IN_PROGRESS.value:
        try:
            challonge = ChallongeAPI(settings.challonge_client_id, settings.challonge_client_secret, settings.challonge_username)
            challonge_matches = await challonge.get_matches(tournament.challonge_id)
            
            if challonge_matches:
                # Получаем участников для маппинга
                challonge_participants = await challonge.get_participants(tournament.challonge_id)
                teams = await TeamRepository.get_teams_by_tournament(tournament_id, status=TeamStatus.APPROVED)
                
                # Создаем маппинг участников
                participants_map = {}
                for participant in challonge_participants:
                    participant_name = participant.get("name")
                    participant_id = str(participant.get("id"))
                    for team in teams:
                        if team.name == participant_name:
                            participants_map[participant_id] = team.id
                            break
                
                # Синхронизируем
                await MatchRepository.sync_matches_from_challonge(
                    tournament_id=tournament_id,
                    challonge_matches=challonge_matches,
                    participants_map=participants_map
                )
                logger.info(f"🔄 Автосинхронизация: обновлено {len(challonge_matches)} матчей")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось синхронизировать матчи: {e}")
    
    # Получаем незавершенные матчи
    pending_matches = await MatchRepository.get_pending_matches(tournament_id)
    
    if not pending_matches and tournament.status != TournamentStatus.IN_PROGRESS.value:
        await safe_edit_message(
            callback.message,
            "⚠️ Матчи будут доступны после запуска турнира.",
            reply_markup=get_matches_keyboard(
                tournament_id, 
                [], 
                f"admin:manage_tournament_{tournament_id}",
                tournament.format
            )
        )
        return
    
    # Если нет активных матчей, показываем все
    tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    if not pending_matches:
        all_matches = await MatchRepository.get_tournament_matches(tournament_id)
        text = f"🏆 <b>{tournament_name}</b>\n\n📊 Все матчи турнира:"
        keyboard = get_matches_keyboard(
            tournament_id, 
            all_matches, 
            f"admin:manage_tournament_{tournament_id}",
            tournament.format
        )
    else:
        text = f"🏆 <b>{tournament_name}</b>\n\n⏳ Активные матчи:"
        keyboard = get_matches_keyboard(
            tournament_id, 
            pending_matches, 
            f"admin:manage_tournament_{tournament_id}",
            tournament.format
        )
    
    await safe_edit_message(callback.message, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:show_matches_"))
async def show_tournament_matches(callback: CallbackQuery, state: FSMContext):
    """Отображение списка матчей турнира"""
    await callback.answer()
    
    try:
        tournament_id = int(callback.data.split("_")[2])
        await display_tournament_matches(callback, tournament_id)
        
    except Exception as e:
        logger.error(f"Ошибка отображения матчей: {e}")
        from utils.message_utils import safe_edit_message
        await safe_edit_message(callback.message, f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("admin:match_view_"))
async def view_match_details(callback: CallbackQuery, state: FSMContext):
    """Детальный просмотр матча"""
    from utils.message_utils import safe_edit_message
    await callback.answer()
    
    try:
        match_id = int(callback.data.split("_")[2])
        
        match = await MatchRepository.get_by_id(match_id)
        if not match:
            await safe_edit_message(callback.message, "❌ Матч не найден")
            return
        
        # Формируем текст
        team1_name = match.team1.name if match.team1 else "?"
        team2_name = match.team2.name if match.team2 else "?"
        
        # HTML escaping
        team1_name = team1_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        team2_name = team2_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Получаем название раунда
        tournament = await TournamentRepository.get_by_id(match.tournament_id)
        bracket_type = getattr(match, 'bracket_type', 'winner')
        round_name = get_round_name(match.round_number, 1, tournament.format if tournament else 'single_elimination', bracket_type)
        
        text = f"🎮 <b>Детали матча</b>\n"
        text += f"📍 {round_name}\n\n"
        
        text += f"━━━━━━━━━━━━━━━━━━\n\n"
        
        text += f"🔵 <b>{team1_name}</b>"
        if match.status == MatchStatus.COMPLETED.value:
            text += f" — <b>{match.team1_score or 0}</b>"
        text += "\n"
        
        text += f"🔴 <b>{team2_name}</b>"
        if match.status == MatchStatus.COMPLETED.value:
            text += f" — <b>{match.team2_score or 0}</b>"
        text += "\n\n"
        
        text += f"━━━━━━━━━━━━━━━━━━\n\n"
        
        # Статус с иконками
        if match.status == MatchStatus.COMPLETED.value:
            winner_name = match.winner.name if match.winner else "Неизвестно"
            winner_name = winner_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            text += f"✅ <b>Завершен</b>\n"
            text += f"🏆 Победитель: <b>{winner_name}</b>"
        elif match.status == MatchStatus.CANCELLED.value:
            text += "❌ <b>Отменен</b>"
        elif match.team1_id and match.team2_id:
            text += "🎮 <b>Готов к игре</b>"
        else:
            text += "⏳ <b>Ожидание участников</b>"
        
        keyboard = get_match_detail_keyboard(match_id, match.tournament_id, match.status)
        await safe_edit_message(callback.message, text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка просмотра матча: {e}")
        from utils.message_utils import safe_edit_message
        await safe_edit_message(callback.message, f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("admin:enter_result_"))
async def start_enter_result(callback: CallbackQuery, state: FSMContext):
    """Начало ввода результата матча"""
    from utils.message_utils import safe_edit_message
    await callback.answer()
    
    try:
        match_id = int(callback.data.split("_")[2])
        
        match = await MatchRepository.get_by_id(match_id)
        if not match:
            await safe_edit_message(callback.message, "❌ Матч не найден")
            return
        
        if not match.team1 or not match.team2:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="◀️ К списку матчей",
                        callback_data=f"admin:show_matches_{match.tournament_id}"
                    )
                ]
            ])
            await safe_edit_message(
                callback.message,
                "⚠️ Невозможно ввести результат: не определены обе команды",
                reply_markup=keyboard
            )
            return
        
        # Сохраняем match_id в состояние
        await state.update_data(match_id=match_id)
        await state.set_state(AdminStates.entering_team1_score)
        
        team1_name = match.team1.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        team2_name = match.team2.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        text = f"📝 <b>Ввод результата матча</b>\n\n"
        text += f"━━━━━━━━━━━━━━━━━━\n\n"
        text += f"🔵 <b>{team1_name}</b>\n"
        text += f"🔴 <b>{team2_name}</b>\n\n"
        text += f"━━━━━━━━━━━━━━━━━━\n\n"
        text += f"Введите счет для команды <b>{team1_name}</b>:"
        
        await safe_edit_message(
            callback.message,
            text, 
            reply_markup=get_score_input_keyboard(match_id),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка начала ввода результата: {e}")
        await safe_edit_message(callback.message, f"❌ Ошибка: {str(e)}")


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
        team2_name = match.team2.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        await state.set_state(AdminStates.entering_team2_score)
        await message.answer(f"Теперь введите счет для <b>{team2_name}</b>:", parse_mode="HTML")
        
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
        team1_name = match.team1.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        team2_name = match.team2.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        winner_name = winner.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        text = f"🎮 <b>Подтверждение результата</b>\n\n"
        text += f"🔵 <b>{team1_name}</b> — <b>{team1_score}</b>\n"
        text += f"🔴 <b>{team2_name}</b> — <b>{team2_score}</b>\n\n"
        text += f"🏆 Победитель: <b>{winner_name}</b>\n\n"
        text += "Подтвердите результат:"
        
        await message.answer(
            text,
            reply_markup=get_score_confirmation_keyboard(match_id, match.tournament_id),
            parse_mode="HTML"
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
            from utils.message_utils import safe_edit_message
            await safe_edit_message(callback.message, "❌ Ошибка: данные результата не найдены")
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
            challonge = ChallongeAPI(settings.challonge_client_id, settings.challonge_client_secret, settings.challonge_username)
            
            # Получаем participant_id для обеих команд из Challonge
            participants = await challonge.get_participants(tournament.challonge_id)
            winner = await TeamRepository.get_by_id(winner_id)
            
            # Определяем ID проигравшего
            loser_id = match.team1_id if winner_id == match.team2_id else match.team2_id
            loser = await TeamRepository.get_by_id(loser_id)
            
            # API v2.1 возвращает данные напрямую
            winner_participant_id = None
            loser_participant_id = None
            
            for participant in participants:
                p_name = participant.get("name")
                p_id = str(participant.get("id"))
                
                if p_name == winner.name:
                    winner_participant_id = p_id
                elif p_name == loser.name:
                    loser_participant_id = p_id
            
            if winner_participant_id:
                scores_csv = f"{team1_score}-{team2_score}"
                success = await challonge.update_match_score(
                    tournament_id=tournament.challonge_id,
                    match_id=match.challonge_match_id,
                    winner_id=winner_participant_id,
                    scores_csv=scores_csv,
                    loser_id=loser_participant_id
                )
                
                if success:
                    logger.info(f"✅ Результат обновлен в Challonge: {scores_csv}")
                else:
                    logger.warning(
                        f"⚠️ Результат сохранен в боте, но не обновился в Challonge. "
                        f"Обновите вручную: https://challonge.com/ru/{tournament.challonge_id}"
                    )
        
        # Автосинхронизация после обновления результата
        if tournament.challonge_id:
            try:
                challonge_matches = await challonge.get_matches(tournament.challonge_id)
                if challonge_matches:
                    challonge_participants = await challonge.get_participants(tournament.challonge_id)
                    teams = await TeamRepository.get_teams_by_tournament(match.tournament_id, status=TeamStatus.APPROVED)
                    
                    participants_map = {}
                    for participant in challonge_participants:
                        participant_name = participant.get("name")
                        participant_id = str(participant.get("id"))
                        for team in teams:
                            if team.name == participant_name:
                                participants_map[participant_id] = team.id
                                break
                    
                    await MatchRepository.sync_matches_from_challonge(
                        tournament_id=match.tournament_id,
                        challonge_matches=challonge_matches,
                        participants_map=participants_map
                    )
                    logger.info("🔄 Автосинхронизация после обновления результата")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось синхронизировать после обновления: {e}")
        
        # Очищаем состояние
        await state.clear()
        
        # Показываем результат
        team1_name = updated_match.team1.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        team2_name = updated_match.team2.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        winner_name = updated_match.winner.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        text = f"✅ <b>Результат сохранен!</b>\n\n"
        text += f"🔵 {team1_name} — {team1_score}\n"
        text += f"🔴 {team2_name} — {team2_score}\n\n"
        text += f"🏆 Победитель: <b>{winner_name}</b>"
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="◀️ К списку матчей",
                    callback_data=f"admin:show_matches_{tournament.id}"
                )
            ]
        ])
        
        from utils.message_utils import safe_edit_message
        await safe_edit_message(callback.message, text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка подтверждения результата: {e}")
        from utils.message_utils import safe_edit_message
        await safe_edit_message(callback.message, f"❌ Ошибка сохранения: {str(e)}")
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
        challonge = ChallongeAPI(settings.challonge_client_id, settings.challonge_client_secret, settings.challonge_username)
        challonge_matches = await challonge.get_matches(tournament.challonge_id)
        
        if not challonge_matches:
            await callback.answer("⚠️ Матчи не найдены в Challonge", show_alert=True)
            return
        
        # Получаем участников из Challonge для создания маппинга
        challonge_participants = await challonge.get_participants(tournament.challonge_id)
        
        # Получаем команды из БД
        teams = await TeamRepository.get_teams_by_tournament(tournament_id, status=TeamStatus.APPROVED)
        
        # Создаем маппинг: challonge_participant_id -> team_id по именам
        # В API v2.1 данные участников возвращаются напрямую без вложенности "participant"
        participants_map = {}
        for participant in challonge_participants:
            participant_name = participant.get("name")
            participant_id = str(participant.get("id"))  # Преобразуем в строку для совместимости
            
            # Ищем команду с таким же именем
            for team in teams:
                if team.name == participant_name:
                    participants_map[participant_id] = team.id
                    break
        
        # Синхронизируем матчи с маппингом
        synced_matches = await MatchRepository.sync_matches_from_challonge(
            tournament_id=tournament_id,
            challonge_matches=challonge_matches,
            participants_map=participants_map
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
