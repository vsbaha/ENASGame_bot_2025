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
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return

    captain = await UserRepository.get_by_id(team.captain_id)
    captain_name = _safe(getattr(captain, "full_name", None), "Неизвестно")

    text = render_application_text(team, captain_name)
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
        text = f"""
✅ Команда одобрена!

👥 Команда "{team.name}" успешно одобрена и активирована.
Капитан получил уведомление.
"""
        await safe_edit_message(
            callback.message,
            text,
            parse_mode="Markdown",
            reply_markup=kb(
                [
                    [
                        InlineKeyboardButton(text="📋 К заявкам", callback_data="admin:team_applications"),
                        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:teams"),
                    ]
                ]
            ),
        )
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

    text = f"""
❌ Отклонение заявки

👥 Команда: {team.name}

Введите причину отклонения заявки:
(Это сообщение получит капитан команды)
"""
    await safe_edit_message(
        callback.message,
        text,
        parse_mode="Markdown",
        reply_markup=kb([[InlineKeyboardButton(text="🔙 Отменить", callback_data=f"admin:review_team_{team_id}")]]),
    )
    await state.set_state(AdminStates.rejecting_team)
    await state.update_data(team_id=team_id)
    await callback.answer()


@router.message(StateFilter(AdminStates.rejecting_team))
async def process_team_rejection_reason(message: Message, state: FSMContext):
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
        await TeamRepository.update_status(int(team_id), "rejected")
        text = f"""
❌ Заявка отклонена

👥 Команда "{team.name}" отклонена.
Причина: {reason}

Капитан получил уведомление с указанием причины.
"""
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=kb([[InlineKeyboardButton(text="📋 К заявкам", callback_data="admin:team_applications"), InlineKeyboardButton(text="🔙 Назад", callback_data="admin:teams")]]),
        )
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
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return

    captain = await UserRepository.get_by_id(team.captain_id)
    captain_name = _safe(getattr(captain, "full_name", None), "Неизвестно")

    text = render_team_card(team, captain_name)
    await safe_edit_message(
        callback.message,
        text,
        parse_mode="Markdown",
        reply_markup=kb(
            [
                [
                    InlineKeyboardButton(text="📝 Редактировать", callback_data=f"admin:edit_team_{team_id}"),
                    InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"admin:block_team_{team_id}"),
                ],
                back_row("admin:teams"),
            ]
        ),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:block_team_\d+$"))
async def block_team(callback: CallbackQuery, state: FSMContext):
    team_id = int(callback.data.split("_")[-1])
    team = await _get_team_or_answer_cb(callback, team_id)
    if not team:
        return

    text = f"""
🚫 Блокировка команды

👥 Команда: {team.name}

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
    await state.update_data(team_id=team_id)
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
        await TeamRepository.update_status(int(team_id), "rejected")
        text = f"""
🚫 Команда заблокирована

👥 Команда "{team.name}" заблокирована.
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