# -*- coding: utf-8 -*-
"""
Админские обработчики управления командами (русский, без локализации). Версия без дубликатов и мусора, с DRY-хелперами.
"""
from __future__ import annotations

import logging
from typing import List, Callable

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database.repositories import UserRepository, TeamRepository
from database.db_manager import get_session
from utils.message_utils import safe_edit_message
from .states import AdminStates
from .keyboards import get_team_moderation_keyboard, get_team_action_keyboard


router = Router()
logger = logging.getLogger(__name__)


# ========= DRY helpers ========= #
def kb(rows: List[List[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_row(callback_data: str) -> List[InlineKeyboardButton]:
    return [InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)]


def list_keyboard(items: List, label: Callable[[object], str], data: Callable[[object], str], limit: int = 10) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for it in items[:limit]:
        rows.append([InlineKeyboardButton(text=label(it), callback_data=data(it))])
    return kb(rows)


def _safe(val, default: str = "Неизвестно") -> str:
    return str(val) if val not in (None, "") else default


def tournament_name(team) -> str:
    return team.tournament.name if getattr(team, "tournament", None) else "Не указан"


def members_count(team) -> int:
    members = getattr(team, "members", None)
    return len(members) if members else 0


def created_at_text(team) -> str:
    created = getattr(team, "created_at", None)
    try:
        return created.strftime("%d.%m.%Y %H:%M") if created else "Неизвестно"
    except Exception:
        return "Неизвестно"


def status_text(team) -> str:
    return getattr(team, "status", None) or "Неизвестно"


def description_text(team) -> str:
    desc = getattr(team, "description", None)
    return desc if desc else "Описание отсутствует"


def render_application_text(team, captain_name: str) -> str:
    return (
        """
👥 Заявка на регистрацию команды

📋 Название: {name}
👤 Капитан: {captain}
🏆 Турнир: {tournament}
👥 Участники: {members}
📅 Дата подачи: {created}

💼 Описание:
{desc}

Выберите действие:
"""
    ).format(
        name=team.name,
        captain=captain_name,
        tournament=tournament_name(team),
        members=members_count(team),
        created=created_at_text(team),
        desc=description_text(team),
    )


def render_team_card(team, captain_name: str) -> str:
    return (
        """
👥 Информация о команде

📋 Название: {name}
👤 Капитан: {captain}
🏆 Турнир: {tournament}
👥 Участников: {members}
📊 Статус: {status}
📅 Создана: {created}

💼 Описание:
{desc}
"""
    ).format(
        name=team.name,
        captain=captain_name,
        tournament=tournament_name(team),
        members=members_count(team),
        status=status_text(team),
        created=created_at_text(team),
        desc=description_text(team),
    )


async def _get_team_or_answer_cb(callback: CallbackQuery, team_id: int):
    team = await TeamRepository.get_by_id(team_id)
    if not team:
        await callback.answer("❌ Команда не найдена")
        return None
    return team


async def _get_team_or_reply_msg(message: Message, team_id: int):
    team = await TeamRepository.get_by_id(team_id)
    if not team:
        await message.answer("❌ Команда не найдена", parse_mode="Markdown")
        return None
    return team


# ========= Handlers ========= #
@router.callback_query(F.data == "admin:teams")
async def team_moderation_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    pending = await TeamRepository.get_pending_teams()
    active = await TeamRepository.get_active_teams()
    blocked = await TeamRepository.get_blocked_teams()

    text = f"""
👥 Модерация команд

📊 Статистика:
⏱ Заявки на рассмотрении: {len(pending)}
✅ Активные команды: {len(active)}
🚫 Заблокированные: {len(blocked)}

Выберите действие:
"""

    await safe_edit_message(callback.message, text, parse_mode="Markdown", reply_markup=get_team_moderation_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:team_applications")
async def view_team_applications(callback: CallbackQuery, state: FSMContext):
    teams = await TeamRepository.get_pending_teams()

    if not teams:
        text = (
            """
📋 Заявки на регистрацию команд

✅ Нет заявок для рассмотрения

Все заявки обработаны!
"""
        )
        await safe_edit_message(callback.message, text, parse_mode="Markdown", reply_markup=kb([back_row("admin:teams")]))
        await callback.answer()
        return

    text = f"""
📋 Заявки на регистрацию команд

Новых заявок: {len(teams)}

Выберите команду для рассмотрения:
"""
    markup = list_keyboard(
        teams,
        label=lambda t: f"👥 {t.name}",
        data=lambda t: f"admin:review_team_{t.id}",
    )
    markup.inline_keyboard.append(back_row("admin:teams"))

    await safe_edit_message(callback.message, text, parse_mode="Markdown", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:review_team_\d+$"))
async def review_team_application(callback: CallbackQuery, state: FSMContext):
    from database.repositories import PlayerRepository
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return

    captain = await UserRepository.get_by_id(team.captain_id)
    captain_name = _safe(getattr(captain, "full_name", None), "Неизвестно")
    
    # Получаем игроков для полного отображения
    main_players = await PlayerRepository.get_main_players(team_id)
    substitute_players = await PlayerRepository.get_substitute_players(team_id)
    
    # Формируем детальный текст с игроками
    players_text = ""
    if main_players:
        players_text += "\n**Основной состав:**\n"
        for i, player in enumerate(main_players, 1):
            captain_mark = " (Капитан)" if i == 1 else ""
            players_text += f"{i}. {player.nickname} (`{player.game_id}`){captain_mark}\n"
    
    if substitute_players:
        players_text += "\n**Запасные игроки:**\n"
        for i, player in enumerate(substitute_players, 1):
            players_text += f"{i}. {player.nickname} (`{player.game_id}`)\n"
    
    # Формируем ссылку на капитана
    captain_link = f"[Написать капитану](tg://user?id={captain.telegram_id})" if captain else "Не найден"
    
    text = f"""
👥 Заявка на регистрацию команды

📋 Название: {team.name}
👤 Капитан: {captain_name}
💬 Связь: {captain_link}
🏆 Турнир: {tournament_name(team)}
👥 Участников: {len(main_players) + len(substitute_players)}
📅 Дата подачи: {created_at_text(team)}
{players_text}

Выберите действие:
"""
    
    await safe_edit_message(callback.message, text, parse_mode="Markdown", reply_markup=get_team_action_keyboard(team_id))
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:approve_team_\d+$"))
async def approve_team(callback: CallbackQuery, state: FSMContext):
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return

    try:
        await TeamRepository.update_status(team_id, "approved")
        
        # Отправляем уведомление капитану
        from database.repositories import UserRepository
        from utils.text_formatting import escape_html
        
        captain = await UserRepository.get_by_id(team.captain_id)
        if captain:
            team_name_escaped = escape_html(team.name)
            tournament_name = escape_html(team.tournament.name if hasattr(team, 'tournament') and team.tournament else 'Неизвестный')
            captain_text = f"""✅ <b>Ваша команда одобрена!</b>

👥 <b>Команда:</b> {team_name_escaped}
🏆 <b>Турнир:</b> {tournament_name}

🎉 Поздравляем! Ваша заявка на участие в турнире одобрена.
Следите за расписанием матчей."""
            
            try:
                await callback.bot.send_message(
                    chat_id=captain.telegram_id,
                    text=captain_text,
                    parse_mode="HTML"
                )
                logger.info(f"Уведомление об одобрении отправлено капитану {captain.telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления капитану {captain.telegram_id}: {e}")
        
        # Получаем админа который одобрил
        admin = await UserRepository.get_by_telegram_id(callback.from_user.id)
        admin_name = escape_html(admin.full_name or admin.username or callback.from_user.username or "Администратор")
        
        # Получаем полный состав команды
        from database.repositories import PlayerRepository
        main_players = await PlayerRepository.get_main_players(team_id)
        substitute_players = await PlayerRepository.get_substitute_players(team_id)
        
        main_roster = "\n".join([f"   {i}. {escape_html(p.nickname)} ({escape_html(p.game_id)})" 
                                  for i, p in enumerate(main_players, 1)])
        
        substitute_roster = ""
        if substitute_players:
            substitute_roster = "\n\n<b>Запасные:</b>\n" + "\n".join([f"   {i}. {escape_html(p.nickname)} ({escape_html(p.game_id)})" 
                                                                        for i, p in enumerate(substitute_players, 1)])
        
        # Формируем полное сообщение с составом
        team_name_escaped = escape_html(team.name)
        tournament_name_escaped = escape_html(team.tournament.name if hasattr(team, 'tournament') and team.tournament else 'Неизвестный')
        captain_name = escape_html(team.captain.full_name or team.captain.username if hasattr(team, 'captain') and team.captain else 'Unknown')
        
        updated_text = f"""✅ <b>Заявка одобрена</b>
<b>ID команды: #{team.id}</b>

👥 <b>Команда:</b> {team_name_escaped}
🏆 <b>Турнир:</b> {tournament_name_escaped}
👤 <b>Капитан:</b> {captain_name}

<b>Основной состав:</b>
{main_roster}{substitute_roster}

✅ <b>Одобрено:</b> {admin_name}"""
        
        # Создаем клавиатуру с кнопкой связи с капитаном
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        approved_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Связь с капитаном",
                    url=f"tg://user?id={captain.telegram_id}"
                )
            ]
        ])
        
        try:
            await callback.message.edit_caption(
                caption=updated_text,
                parse_mode="HTML",
                reply_markup=approved_keyboard
            )
        except:
            # Если это не фото, пробуем редактировать текст
            try:
                await callback.message.edit_text(
                    text=updated_text,
                    parse_mode="HTML",
                    reply_markup=approved_keyboard
                )
            except Exception as e:
                logger.error(f"Ошибка редактирования сообщения: {e}")
        
        await callback.answer("✅ Команда одобрена")
    except Exception as e:
        logger.error(f"Ошибка при одобрении команды {team_id}: {e}")
        await callback.answer("❌ Ошибка при одобрении команды")


@router.callback_query(F.data.regexp(r"^admin:reject_team_\d+$"))
async def reject_team(callback: CallbackQuery, state: FSMContext):
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return

    from utils.text_formatting import escape_html
    team_name_escaped = escape_html(team.name)
    
    text = f"""❌ <b>Отклонение заявки</b>

👥 <b>Команда:</b> {team_name_escaped}

Введите причину отклонения заявки:
<i>(Это сообщение получит капитан команды)</i>"""
    
    # Отправляем в личку админу для ввода причины
    try:
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=text,
            parse_mode="HTML"
        )
        await callback.answer("✅ Проверьте личные сообщения бота", show_alert=True)
    except:
        await callback.answer("❌ Откройте личку сботом для ввода причины", show_alert=True)
        return
    
    await state.set_state(AdminStates.rejecting_team)
    await state.update_data(team_id=team_id, chat_message_id=callback.message.message_id, chat_id=callback.message.chat.id)
    await callback.answer()


@router.message(StateFilter(AdminStates.rejecting_team))
async def process_team_rejection_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    team_id = data.get("team_id")
    chat_message_id = data.get("chat_message_id")
    chat_id = data.get("chat_id")
    reason = (message.text or "").strip()

    if not team_id:
        await message.answer("❌ Ошибка: команда не найдена")
        await state.clear()
        return

    team = await _get_team_or_reply_msg(message, int(team_id))
    if not team:
        await state.clear()
        return

    try:
        from utils.text_formatting import escape_html
        from database.repositories import UserRepository
        
        await TeamRepository.update_status(int(team_id), "rejected")
        await TeamRepository.set_rejection_reason(int(team_id), reason)
        
        # Отправляем уведомление капитану
        captain = await UserRepository.get_by_id(team.captain_id)
        if captain:
            team_name_escaped = escape_html(team.name)
            tournament_name = escape_html(team.tournament.name if hasattr(team, 'tournament') and team.tournament else 'Неизвестный')
            reason_escaped = escape_html(reason)
            
            captain_text = f"""❌ <b>Ваша заявка отклонена</b>

👥 <b>Команда:</b> {team_name_escaped}
🏆 <b>Турнир:</b> {tournament_name}

📝 <b>Причина отклонения:</b>
{reason_escaped}

Вы можете исправить ошибки и подать заявку заново."""
            
            try:
                await message.bot.send_message(
                    chat_id=captain.telegram_id,
                    text=captain_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления капитану: {e}")
        
        # Удаляем сообщение из админ-чата (заявка отклонена)
        if chat_id and chat_message_id:
            try:
                await message.bot.delete_message(
                    chat_id=chat_id,
                    message_id=chat_message_id
                )
            except Exception as e:
                logger.error(f"Ошибка удаления сообщения из админ-чата: {e}")
        
        await message.answer("✅ Заявка отклонена, капитан получил уведомление")
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при отклонении команды {team_id}: {e}")
        await message.answer("❌ Ошибка при отклонении заявки", parse_mode="Markdown")
        await state.clear()


@router.callback_query(F.data == "admin:active_teams")
async def view_active_teams(callback: CallbackQuery, state: FSMContext):
    teams = await TeamRepository.get_active_teams()

    if not teams:
        text = (
            """
👥 Активные команды

📭 Активных команд нет

Пока что нет активных команд в системе.
"""
        )
        await safe_edit_message(callback.message, text, parse_mode="Markdown", reply_markup=kb([back_row("admin:teams")]))
        await callback.answer()
        return

    text = f"""
👥 Активные команды

Всего активных команд: {len(teams)}
"""
    markup = list_keyboard(
        teams,
        label=lambda t: f"👥 {t.name}",
        data=lambda t: f"admin:team_details_{t.id}",
    )
    markup.inline_keyboard.append(back_row("admin:teams"))
    await safe_edit_message(callback.message, text, parse_mode="Markdown", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "admin:blocked_teams")
async def view_blocked_teams(callback: CallbackQuery, state: FSMContext):
    teams = await TeamRepository.get_blocked_teams()

    if not teams:
        text = (
            """
🚫 Заблокированные команды

✅ Заблокированных команд нет

Все команды имеют хороший статус!
"""
        )
        await safe_edit_message(callback.message, text, parse_mode="Markdown", reply_markup=kb([back_row("admin:teams")]))
        await callback.answer()
        return

    text = f"""
🚫 Заблокированные команды

Заблокированных команд: {len(teams)}

Список команд:
"""
    markup = list_keyboard(
        teams,
        label=lambda t: f"🚫 {t.name}",
        data=lambda t: f"admin:team_details_{t.id}",
    )
    markup.inline_keyboard.append(back_row("admin:teams"))
    await safe_edit_message(callback.message, text, parse_mode="Markdown", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:team_details_\d+$"))
async def view_team_details(callback: CallbackQuery, state: FSMContext):
    from database.repositories import PlayerRepository
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return

    captain = await UserRepository.get_by_id(team.captain_id)
    captain_name = _safe(getattr(captain, "full_name", None), "Неизвестно")
    
    # Получаем игроков для полного отображения
    main_players = await PlayerRepository.get_main_players(team_id)
    substitute_players = await PlayerRepository.get_substitute_players(team_id)
    
    # Формируем детальный текст с игроками
    players_text = ""
    if main_players:
        players_text += "\n**Основной состав:**\n"
        for i, player in enumerate(main_players, 1):
            captain_mark = " (Капитан)" if i == 1 else ""
            players_text += f"{i}. {player.nickname} (`{player.game_id}`){captain_mark}\n"
    
    if substitute_players:
        players_text += "\n**Запасные игроки:**\n"
        for i, player in enumerate(substitute_players, 1):
            players_text += f"{i}. {player.nickname} (`{player.game_id}`)\n"
    
    # Формируем ссылку на капитана
    captain_link = f"[Написать капитану](tg://user?id={captain.telegram_id})" if captain else "Не найден"
    
    text = f"""
👥 Информация о команде

📋 Название: {team.name}
👤 Капитан: {captain_name}
💬 Связь: {captain_link}
🏆 Турнир: {tournament_name(team)}
👥 Участников: {len(main_players) + len(substitute_players)}
📊 Статус: {status_text(team)}
📅 Создана: {created_at_text(team)}
{players_text}
"""

    # Формируем кнопки в зависимости от статуса
    buttons = [
        [InlineKeyboardButton(text="📝 Редактировать", callback_data=f"admin:edit_team_{team_id}")]
    ]
    
    if team.status == "blocked":
        buttons.append([InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"admin:unblock_team_{team_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"admin:block_team_{team_id}")])
    
    buttons.append([InlineKeyboardButton(text="🔄 Изменить статус", callback_data=f"admin:change_status_{team_id}")])
    buttons.append(back_row("admin:teams"))
    
    await safe_edit_message(
        callback.message,
        text,
        parse_mode="Markdown",
        reply_markup=kb(buttons),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:edit_team_\d+$"))
async def edit_team_menu(callback: CallbackQuery, state: FSMContext):
    """Меню редактирования команды"""
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return

    text = f"""
📝 Редактирование команды

👥 Команда: {team.name}
🏆 Турнир: {tournament_name(team)}

Выберите, что хотите изменить:
"""
    
    await safe_edit_message(
        callback.message,
        text,
        parse_mode="Markdown",
        reply_markup=kb([
            [
                InlineKeyboardButton(text="📝 Изменить название", callback_data=f"admin:edit_team_name_{team_id}"),
            ],
            [
                InlineKeyboardButton(text="🖼 Изменить логотип", callback_data=f"admin:edit_team_logo_{team_id}"),
            ],
            [
                InlineKeyboardButton(text="👥 Управление составом", callback_data=f"admin:manage_roster_{team_id}"),
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data=f"admin:team_details_{team_id}"),
            ]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:edit_team_name_\d+$"))
async def start_edit_team_name(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования названия команды"""
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return

    text = f"""
📝 Изменение названия команды

Текущее название: {team.name}

Введите новое название команды:
"""
    
    await safe_edit_message(
        callback.message,
        text,
        parse_mode="Markdown",
        reply_markup=kb([[InlineKeyboardButton(text="🔙 Отменить", callback_data=f"admin:edit_team_{team_id}")]])
    )
    
    await state.set_state(AdminStates.editing_team_name)
    await state.update_data(team_id=team_id)
    await callback.answer()


@router.message(StateFilter(AdminStates.editing_team_name))
async def process_edit_team_name(message: Message, state: FSMContext):
    """Обработка нового названия команды"""
    data = await state.get_data()
    team_id = data.get("team_id")
    new_name = (message.text or "").strip()

    if not team_id:
        await message.answer("❌ Ошибка: команда не найдена", parse_mode="Markdown")
        await state.clear()
        return

    if not new_name:
        await message.answer("❌ Название не может быть пустым", parse_mode="Markdown")
        return

    if len(new_name) > 50:
        await message.answer("❌ Название слишком длинное (максимум 50 символов)", parse_mode="Markdown")
        return

    team = await _get_team_or_reply_msg(message, int(team_id))
    if not team:
        await state.clear()
        return

    try:
        old_name = team.name
        await TeamRepository.update_team_name(int(team_id), new_name)
        
        text = f"""
✅ Название команды изменено

Старое название: {old_name}
Новое название: {new_name}
"""
        
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=kb([
                [InlineKeyboardButton(text="👥 К деталям команды", callback_data=f"admin:team_details_{team_id}")],
                [InlineKeyboardButton(text="🔙 К списку команд", callback_data="admin:teams")]
            ])
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при изменении названия команды {team_id}: {e}")
        await message.answer("❌ Ошибка при изменении названия", parse_mode="Markdown")
        await state.clear()


@router.callback_query(F.data.regexp(r"^admin:edit_team_logo_\d+$"))
async def start_edit_team_logo(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования логотипа команды"""
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return
    
    text = f"""
🖼 Изменение логотипа команды

👥 Команда: {team.name}

Загрузите новый логотип команды.

⚠️ Требования:
▪️ Формат: JPG, PNG
▪️ Размер: до 5 МБ
▪️ Логотип должен быть квадратным (512x512, 1024x1024)
"""
    
    # Отправляем новое сообщение для загрузки фото
    await callback.message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=kb([[InlineKeyboardButton(text="🔙 Отменить", callback_data=f"admin:edit_team_{team_id}")]])
    )
    
    await state.set_state(AdminStates.editing_team_logo)
    await state.update_data(team_id=team_id)
    await callback.answer()


@router.message(StateFilter(AdminStates.editing_team_logo), F.photo)
async def process_edit_team_logo(message: Message, state: FSMContext):
    """Обработка нового логотипа команды"""
    data = await state.get_data()
    team_id = data.get("team_id")

    if not team_id:
        await message.answer("❌ Ошибка: команда не найдена", parse_mode="Markdown")
        await state.clear()
        return

    team = await _get_team_or_reply_msg(message, int(team_id))
    if not team:
        await state.clear()
        return

    try:
        # Берём самое большое фото
        photo = message.photo[-1]
        
        # Проверка размера (5 МБ)
        if photo.file_size > 5242880:
            await message.answer("❌ Файл слишком большой. Максимальный размер: 5 МБ.\n\nПопробуйте другой файл:")
            return
        
        # Проверяем квадратность (допуск ±10%)
        width = photo.width
        height = photo.height
        ratio = width / height if height > 0 else 0
        
        if ratio < 0.9 or ratio > 1.1:
            await message.answer(
                f"⚠️ Логотип должен быть квадратным!\n\n"
                f"Текущее соотношение: {width}x{height}\n"
                f"Пожалуйста, загрузите квадратное изображение."
            )
            return
        
        # Обновляем логотип
        await TeamRepository.update_team(int(team_id), logo_file_id=photo.file_id)
        
        text = f"""
✅ Логотип команды изменён

👥 Команда: {team.name}
"""
        
        # Отправляем новый логотип
        await message.answer_photo(
            photo=photo.file_id,
            caption=text,
            parse_mode="Markdown",
            reply_markup=kb([
                [InlineKeyboardButton(text="👥 К деталям команды", callback_data=f"admin:team_details_{team_id}")],
                [InlineKeyboardButton(text="🔙 К списку команд", callback_data="admin:teams")]
            ])
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при изменении логотипа команды {team_id}: {e}")
        await message.answer("❌ Ошибка при изменении логотипа", parse_mode="Markdown")
        await state.clear()


@router.callback_query(F.data.regexp(r"^admin:manage_roster_\d+$"))
async def manage_team_roster(callback: CallbackQuery, state: FSMContext):
    """Управление составом команды"""
    from database.repositories import PlayerRepository
    
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return

    # Получаем игроков
    main_players = await PlayerRepository.get_main_players(team_id)
    substitute_players = await PlayerRepository.get_substitute_players(team_id)
    
    text = f"""
👥 Управление составом

📋 Команда: {team.name}
🏆 Турнир: {tournament_name(team)}

**Основной состав ({len(main_players)}):**
"""
    
    for i, player in enumerate(main_players, 1):
        text += f"{i}. {player.nickname} (`{player.game_id}`)\n"
    
    if substitute_players:
        text += f"\n**Запасные ({len(substitute_players)}):**\n"
        for i, player in enumerate(substitute_players, 1):
            text += f"{i}. {player.nickname} (`{player.game_id}`)\n"
    
    text += "\nВыберите действие:"
    
    # Создаём кнопки для каждого игрока
    buttons = []
    
    # Основной состав
    for player in main_players:
        buttons.append([
            InlineKeyboardButton(
                text=f"✏️ {player.nickname}",
                callback_data=f"admin:edit_player_{player.id}"
            ),
            InlineKeyboardButton(
                text="❌",
                callback_data=f"admin:remove_player_{player.id}_{team_id}"
            )
        ])
    
    # Запасные
    for player in substitute_players:
        buttons.append([
            InlineKeyboardButton(
                text=f"✏️ {player.nickname} (зап.)",
                callback_data=f"admin:edit_player_{player.id}"
            ),
            InlineKeyboardButton(
                text="❌",
                callback_data=f"admin:remove_player_{player.id}_{team_id}"
            )
        ])
    
    # Кнопки управления
    buttons.extend([
        [
            InlineKeyboardButton(
                text="➕ Добавить игрока",
                callback_data=f"admin:add_player_{team_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=f"admin:edit_team_{team_id}"
            )
        ]
    ])
    
    await safe_edit_message(
        callback.message,
        text,
        parse_mode="Markdown",
        reply_markup=kb(buttons)
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:add_player_\d+$"))
async def add_roster_player(callback: CallbackQuery, state: FSMContext):
    """Начало добавления игрока"""
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return
    
    text = f"""
➕ Добавление игрока

📋 Команда: {team.name}

Введите данные игрока в формате:
`Никнейм | Game ID | Тип`

**Тип:** `основной` или `запасной`

💡 Пример:
`ProPlayer | 123456789 | основной`
`SubPlayer | 987654321 | запасной`
"""
    
    await safe_edit_message(
        callback.message,
        text,
        parse_mode="Markdown",
        reply_markup=kb([[InlineKeyboardButton(text="🔙 Отменить", callback_data=f"admin:manage_roster_{team_id}")]])
    )
    
    await state.set_state(AdminStates.adding_roster_player)
    await state.update_data(team_id=team_id)
    await callback.answer()


@router.message(StateFilter(AdminStates.adding_roster_player))
async def process_add_roster_player(message: Message, state: FSMContext):
    """Обработка добавления игрока"""
    from database.repositories import PlayerRepository
    
    data = await state.get_data()
    team_id = data.get("team_id")
    
    if not team_id:
        await message.answer("❌ Ошибка: команда не найдена")
        await state.clear()
        return
    
    # Парсим ввод
    parts = [p.strip() for p in message.text.split("|")]
    
    if len(parts) != 3:
        await message.answer("❌ Неверный формат. Используйте:\n`Никнейм | Game ID | Тип`\n\nПопробуйте ещё раз:", parse_mode="Markdown")
        return
    
    nickname, game_id, player_type = parts
    player_type = player_type.lower()
    
    if player_type not in ["основной", "запасной"]:
        await message.answer("❌ Тип должен быть 'основной' или 'запасной'.\n\nПопробуйте ещё раз:")
        return
    
    is_substitute = player_type == "запасной"
    
    try:
        # Добавляем игрока
        player = await PlayerRepository.add_player(
            team_id=int(team_id),
            nickname=nickname,
            game_id=game_id,
            is_substitute=is_substitute
        )
        
        if player:
            type_text = "запасных" if is_substitute else "основной состав"
            text = f"""
✅ Игрок добавлен

👤 Никнейм: {nickname}
🆔 Game ID: {game_id}
📊 Тип: {type_text}
"""
            await message.answer(
                text,
                parse_mode="Markdown",
                reply_markup=kb([
                    [InlineKeyboardButton(text="👥 К составу", callback_data=f"admin:manage_roster_{team_id}")],
                    [InlineKeyboardButton(text="🔙 К команде", callback_data=f"admin:team_details_{team_id}")]
                ])
            )
            await state.clear()
        else:
            await message.answer("❌ Ошибка добавления игрока")
            await state.clear()
    except Exception as e:
        logger.error(f"Ошибка добавления игрока: {e}")
        await message.answer("❌ Ошибка добавления игрока")
        await state.clear()


@router.callback_query(F.data.regexp(r"^admin:remove_player_\d+_\d+$"))
async def remove_roster_player(callback: CallbackQuery, state: FSMContext):
    """Удаление игрока из состава"""
    from database.repositories import PlayerRepository
    
    parts = callback.data.split("_")
    player_id = int(parts[2])
    team_id = int(parts[3])
    
    try:
        # Получаем информацию об игроке перед удалением
        players = await PlayerRepository.get_team_players(team_id)
        player_to_remove = next((p for p in players if p.id == player_id), None)
        
        if not player_to_remove:
            await callback.answer("❌ Игрок не найден", show_alert=True)
            return
        
        # Удаляем игрока
        success = await PlayerRepository.remove_player(player_id)
        
        if success:
            await callback.answer(f"✅ Игрок {player_to_remove.nickname} удалён", show_alert=True)
            # Обновляем список
            await manage_team_roster(callback, state)
        else:
            await callback.answer("❌ Ошибка удаления", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка удаления игрока: {e}")
        await callback.answer("❌ Ошибка удаления", show_alert=True)


@router.callback_query(F.data.regexp(r"^admin:edit_player_\d+$"))
async def edit_roster_player_menu(callback: CallbackQuery, state: FSMContext):
    """Меню редактирования игрока"""
    from database.repositories import PlayerRepository
    
    player_id = int(callback.data.split("_")[-1])
    
    # Получаем игрока
    players = await PlayerRepository.get_team_players(0)  # Получим через прямой запрос
    async with get_session() as session:
        from database.models import Player
        player = await session.get(Player, player_id)
        
        if not player:
            await callback.answer("❌ Игрок не найден", show_alert=True)
            return
        
        type_text = "Запасной" if player.is_substitute else "Основной состав"
        
        text = f"""
✏️ Редактирование игрока

👤 Никнейм: {player.nickname}
🆔 Game ID: {player.game_id}
📊 Тип: {type_text}

Выберите, что хотите изменить:
"""
        
        await safe_edit_message(
            callback.message,
            text,
            parse_mode="Markdown",
            reply_markup=kb([
                [
                    InlineKeyboardButton(
                        text="✏️ Изменить никнейм",
                        callback_data=f"admin:edit_player_nick_{player_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🆔 Изменить Game ID",
                        callback_data=f"admin:edit_player_gameid_{player_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад к составу",
                        callback_data=f"admin:manage_roster_{player.team_id}"
                    )
                ]
            ])
        )
        await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:edit_player_nick_\d+$"))
async def start_edit_player_nickname(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования никнейма"""
    player_id = int(callback.data.split("_")[-1])
    
    async with get_session() as session:
        from database.models import Player
        player = await session.get(Player, player_id)
        
        if not player:
            await callback.answer("❌ Игрок не найден", show_alert=True)
            return
        
        text = f"""
✏️ Изменение никнейма

Текущий никнейм: {player.nickname}

Введите новый никнейм:
"""
        
        await safe_edit_message(
            callback.message,
            text,
            parse_mode="Markdown",
            reply_markup=kb([[InlineKeyboardButton(text="🔙 Отменить", callback_data=f"admin:edit_player_{player_id}")]])
        )
        
        await state.set_state(AdminStates.editing_roster_player_nickname)
        await state.update_data(player_id=player_id, team_id=player.team_id)
        await callback.answer()


@router.message(StateFilter(AdminStates.editing_roster_player_nickname))
async def process_edit_player_nickname(message: Message, state: FSMContext):
    """Обработка нового никнейма"""
    from database.repositories import PlayerRepository
    
    data = await state.get_data()
    player_id = data.get("player_id")
    team_id = data.get("team_id")
    new_nickname = message.text.strip()
    
    if not new_nickname:
        await message.answer("❌ Никнейм не может быть пустым")
        return
    
    try:
        success = await PlayerRepository.update_player(player_id, nickname=new_nickname)
        
        if success:
            await message.answer(
                f"✅ Никнейм изменён на: {new_nickname}",
                reply_markup=kb([
                    [InlineKeyboardButton(text="👥 К составу", callback_data=f"admin:manage_roster_{team_id}")],
                ])
            )
            await state.clear()
        else:
            await message.answer("❌ Ошибка обновления")
            await state.clear()
    except Exception as e:
        logger.error(f"Ошибка обновления никнейма: {e}")
        await message.answer("❌ Ошибка обновления")
        await state.clear()


@router.callback_query(F.data.regexp(r"^admin:edit_player_gameid_\d+$"))
async def start_edit_player_gameid(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования Game ID"""
    player_id = int(callback.data.split("_")[-1])
    
    async with get_session() as session:
        from database.models import Player
        player = await session.get(Player, player_id)
        
        if not player:
            await callback.answer("❌ Игрок не найден", show_alert=True)
            return
        
        text = f"""
🆔 Изменение Game ID

Текущий Game ID: {player.game_id}

Введите новый Game ID:
"""
        
        await safe_edit_message(
            callback.message,
            text,
            parse_mode="Markdown",
            reply_markup=kb([[InlineKeyboardButton(text="🔙 Отменить", callback_data=f"admin:edit_player_{player_id}")]])
        )
        
        await state.set_state(AdminStates.editing_roster_player_game_id)
        await state.update_data(player_id=player_id, team_id=player.team_id)
        await callback.answer()


@router.message(StateFilter(AdminStates.editing_roster_player_game_id))
async def process_edit_player_gameid(message: Message, state: FSMContext):
    """Обработка нового Game ID"""
    from database.repositories import PlayerRepository
    
    data = await state.get_data()
    player_id = data.get("player_id")
    team_id = data.get("team_id")
    new_game_id = message.text.strip()
    
    if not new_game_id:
        await message.answer("❌ Game ID не может быть пустым")
        return
    
    try:
        success = await PlayerRepository.update_player(player_id, game_id=new_game_id)
        
        if success:
            await message.answer(
                f"✅ Game ID изменён на: {new_game_id}",
                reply_markup=kb([
                    [InlineKeyboardButton(text="👥 К составу", callback_data=f"admin:manage_roster_{team_id}")],
                ])
            )
            await state.clear()
        else:
            await message.answer("❌ Ошибка обновления")
            await state.clear()
    except Exception as e:
        logger.error(f"Ошибка обновления Game ID: {e}")
        await message.answer("❌ Ошибка обновления")
        await state.clear()


@router.callback_query(F.data.regexp(r"^admin:block_team_\d+$"))
async def block_team(callback: CallbackQuery, state: FSMContext):
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return

    text = f"""
🚫 Блокировка команды

👥 Команда: {team.name}
🏆 Турнир: {tournament_name(team)}

Выберите область блокировки:
"""
    await safe_edit_message(
        callback.message,
        text,
        parse_mode="Markdown",
        reply_markup=kb([
            [
                InlineKeyboardButton(
                    text="🏆 Только этот турнир",
                    callback_data=f"admin:block_scope_tournament_{team_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌐 Все турниры",
                    callback_data=f"admin:block_scope_global_{team_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Отменить",
                    callback_data=f"admin:team_details_{team_id}"
                )
            ]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:block_scope_(tournament|global)_\d+$"))
async def block_team_select_scope(callback: CallbackQuery, state: FSMContext):
    """Выбор области блокировки"""
    parts = callback.data.split("_")
    scope = parts[2]  # tournament или global
    team_id = int(parts[3])
    
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return
    
    scope_text = "только на этот турнир" if scope == "tournament" else "на все турниры"
    
    text = f"""
🚫 Блокировка команды

👥 Команда: {team.name}
🚫 Область: {scope_text}

Введите причину блокировки:
(Это сообщение получит капитан команды)
"""
    await safe_edit_message(
        callback.message,
        text,
        parse_mode="Markdown",
        reply_markup=kb([[InlineKeyboardButton(text="🔙 Отменить", callback_data=f"admin:team_details_{team_id}")]]),
    )
    await state.set_state(AdminStates.blocking_team)
    await state.update_data(team_id=team_id, block_scope=scope)
    await callback.answer()


@router.message(StateFilter(AdminStates.blocking_team))
async def process_team_blocking_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    team_id = data.get("team_id")
    reason = (message.text or "").strip()

    if not team_id:
        await message.answer("❌ Ошибка: команда не найдена", parse_mode="Markdown")
        await state.clear()
        return

    team = await _get_team_or_reply_msg(message, int(team_id))
    if not team:
        await state.clear()
        return

    try:
        from utils.text_formatting import escape_html
        from datetime import datetime
        
        block_scope = data.get("block_scope", "tournament")
        
        # Получаем админа
        admin = await UserRepository.get_by_telegram_id(message.from_user.id)
        
        # Блокируем команду
        await TeamRepository.block_team(
            team_id=int(team_id),
            reason=reason,
            scope=block_scope,
            blocked_by=admin.id if admin else None
        )
        
        # Отправляем уведомление капитану
        captain = await UserRepository.get_by_id(team.captain_id)
        if captain:
            team_name_escaped = escape_html(team.name)
            tournament_name = escape_html(team.tournament.name if hasattr(team, 'tournament') and team.tournament else 'Неизвестный')
            reason_escaped = escape_html(reason)
            
            scope_text = "только на этот турнир" if block_scope == "tournament" else "на все турниры"
            
            captain_text = f"""🚫 <b>Ваша команда заблокирована</b>

👥 <b>Команда:</b> {team_name_escaped}
🏆 <b>Турнир:</b> {tournament_name}
🚫 <b>Область блокировки:</b> {scope_text}

📝 <b>Причина блокировки:</b>
{reason_escaped}

Для получения дополнительной информации обратитесь к администраторам."""
            
            try:
                await message.bot.send_message(
                    chat_id=captain.telegram_id,
                    text=captain_text,
                    parse_mode="HTML"
                )
                logger.info(f"Уведомление о блокировке отправлено капитану {captain.telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления капитану: {e}")
        
        scope_text = "только на этот турнир" if block_scope == "tournament" else "на все турниры"
        text = f"""
🚫 Команда заблокирована

👥 Команда: "{team.name}"
🚫 Область: {scope_text}
Причина: {reason}

Капитан получил уведомление.
"""
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=kb([[InlineKeyboardButton(text="👥 К командам", callback_data="admin:teams"), InlineKeyboardButton(text="🚫 Заблокированные", callback_data="admin:blocked_teams")]]),
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при блокировке команды {team_id}: {e}")
        await message.answer("❌ Ошибка при блокировке команды", parse_mode="Markdown")
        await state.clear()


@router.callback_query(F.data.regexp(r"^admin:unblock_team_\d+$"))
async def unblock_team(callback: CallbackQuery, state: FSMContext):
    """Разблокировка команды"""
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return
    
    try:
        await TeamRepository.unblock_team(team_id)
        
        # Уведомляем капитана
        from utils.text_formatting import escape_html
        captain = await UserRepository.get_by_id(team.captain_id)
        if captain:
            team_name_escaped = escape_html(team.name)
            tournament_name = escape_html(team.tournament.name if hasattr(team, 'tournament') and team.tournament else 'Неизвестный')
            
            captain_text = f"""✅ <b>Ваша команда разблокирована!</b>

👥 <b>Команда:</b> {team_name_escaped}
🏆 <b>Турнир:</b> {tournament_name}

Теперь вы снова можете участвовать в турнирах."""
            
            try:
                await callback.bot.send_message(
                    chat_id=captain.telegram_id,
                    text=captain_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления капитану: {e}")
        
        await callback.answer("✅ Команда разблокирована", show_alert=True)
        # Возвращаемся к деталям команды
        await view_team_details(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка разблокировки команды: {e}")
        await callback.answer("❌ Ошибка разблокировки", show_alert=True)


@router.callback_query(F.data.regexp(r"^admin:change_status_\d+$"))
async def change_team_status_menu(callback: CallbackQuery, state: FSMContext):
    """Меню изменения статуса команды"""
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return
    
    current_status_text = {
        "pending": "⏳ Ожидает модерации",
        "approved": "✅ Одобрена",
        "rejected": "❌ Отклонена",
        "blocked": "🚫 Заблокирована"
    }.get(team.status, team.status)
    
    text = f"""
🔄 Изменение статуса команды

👥 Команда: {team.name}
📊 Текущий статус: {current_status_text}

Выберите новый статус:
"""
    
    buttons = []
    
    if team.status != "pending":
        buttons.append([InlineKeyboardButton(text="⏳ Ожидает модерации", callback_data=f"admin:set_status_pending_{team_id}")])
    
    if team.status != "approved":
        buttons.append([InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin:set_status_approved_{team_id}")])
    
    if team.status != "rejected":
        buttons.append([InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin:set_status_rejected_{team_id}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"admin:team_details_{team_id}")])
    
    await safe_edit_message(
        callback.message,
        text,
        parse_mode="Markdown",
        reply_markup=kb(buttons)
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:set_status_(pending|approved|rejected)_\d+$"))
async def set_team_status(callback: CallbackQuery, state: FSMContext):
    """Установка нового статуса команды"""
    parts = callback.data.split("_")
    new_status = parts[2]
    team_id = int(parts[3])
    
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return
    
    try:
        await TeamRepository.update_status(team_id, new_status)
        
        status_text = {
            "pending": "⏳ Ожидает модерации",
            "approved": "✅ Одобрена",
            "rejected": "❌ Отклонена"
        }.get(new_status, new_status)
        
        await callback.answer(f"✅ Статус изменён на: {status_text}", show_alert=True)
        # Возвращаемся к деталям команды
        await view_team_details(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка изменения статуса: {e}")
        await callback.answer("❌ Ошибка изменения статуса", show_alert=True)


@router.callback_query(F.data == "admin:search_team")
async def search_team_prompt(callback: CallbackQuery, state: FSMContext):
    text = (
        """
🔍 Поиск команды

Введите название команды или ID для поиска:
"""
    )
    await safe_edit_message(callback.message, text, parse_mode="Markdown", reply_markup=kb([[InlineKeyboardButton(text="🔙 Отменить", callback_data="admin:teams")]]))
    await state.set_state(AdminStates.searching_team)
    await callback.answer()


@router.message(StateFilter(AdminStates.searching_team))
async def process_team_search(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if not query:
        await message.answer("❌ Введите название команды или ID", parse_mode="Markdown")
        return

    try:
        if query.isdigit():
            team = await TeamRepository.get_by_id(int(query))
            teams = [team] if team else []
        else:
            teams = await TeamRepository.search_by_name(query)

        if not teams:
            text = f"""
🔍 Результаты поиска

❌ Команды не найдены

По запросу "{query}" команды не найдены.
"""
            await message.answer(
                text,
                parse_mode="Markdown",
                reply_markup=kb([[InlineKeyboardButton(text="🔍 Новый поиск", callback_data="admin:search_team")], back_row("admin:teams")]),
            )
            await state.clear()
            return

        text = f"""
🔍 Результаты поиска

Найдено команд: {len(teams)}

Выберите команду:
"""
        markup = list_keyboard(
            teams,
            label=lambda t: f"👥 {t.name} (ID: {t.id})",
            data=lambda t: f"admin:team_details_{t.id}",
        )
        markup.inline_keyboard.extend([[InlineKeyboardButton(text="🔍 Новый поиск", callback_data="admin:search_team")], back_row("admin:teams")])
        await message.answer(text, parse_mode="Markdown", reply_markup=markup)
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при поиске команды: {e}")
        await message.answer("❌ Ошибка при поиске команды", parse_mode="Markdown")
        await state.clear()