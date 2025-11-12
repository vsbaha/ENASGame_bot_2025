"""
Обработчики команд пользователя - полная система регистрации
"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database.repositories.user_repository import UserRepository
from database.repositories.team_repository import TeamRepository
from database.repositories.player_repository import PlayerRepository
from database.repositories.tournament_repository import TournamentRepository
from database.repositories.game_repository import GameRepository
from database.models import TeamStatus
from utils.message_utils import safe_edit_message
from .states import UserStates

# Создаем роутер для команд
teams_router = Router()
logger = logging.getLogger(__name__)


# ========== ПРОСМОТР СВОИХ КОМАНД ==========

@teams_router.callback_query(F.data == "menu:my_teams")
async def show_my_teams(callback: CallbackQuery, state: FSMContext):
    """Показать мои команды"""
    try:
        user = await UserRepository.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        teams = await TeamRepository.get_teams_by_captain(user.id)
        
        if not teams:
            text = """👥 **Мои команды**

У вас пока нет зарегистрированных команд.

Зарегистрируйте команду на турнир, чтобы начать участвовать в соревнованиях!"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="➕ Создать команду",
                        callback_data="team:create"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="main_menu"
                    )
                ]
            ]
        else:
            text = f"""👥 **Мои команды ({len(teams)})**

Список ваших команд:

"""
            keyboard = []
            
            for team in teams:
                # Эмодзи статуса
                status_emoji = {
                    TeamStatus.PENDING.value: "⏳",
                    TeamStatus.APPROVED.value: "✅",
                    TeamStatus.REJECTED.value: "❌"
                }.get(team.status, "❓")
                
                # Добавляем информацию о команде
                text += f"{status_emoji} **{team.name}**\n"
                text += f"   🏆 {team.tournament.name}\n"
                text += f"   🎮 {team.tournament.game.name}\n"
                
                # Показываем причину отклонения
                if team.status == TeamStatus.REJECTED.value and team.rejection_reason:
                    text += f"   ⚠️ Причина: {team.rejection_reason}\n"
                
                text += "\n"
                
                # Кнопка для просмотра команды
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"{status_emoji} {team.name}",
                        callback_data=f"team:view_{team.id}"
                    )
                ])
            
            keyboard.extend([
                [
                    InlineKeyboardButton(
                        text="➕ Создать команду",
                        callback_data="team:create"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="main_menu"
                    )
                ]
            ])
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(UserStates.viewing_team_list)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка показа команд: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ========== ПРОСМОТР КОНКРЕТНОЙ КОМАНДЫ ==========

@teams_router.callback_query(F.data.startswith("team:view_"))
async def view_team_details(callback: CallbackQuery, state: FSMContext):
    """Просмотр деталей команды"""
    try:
        team_id = int(callback.data.split("_")[1])
        team = await TeamRepository.get_by_id(team_id)
        
        if not team:
            await callback.answer("❌ Команда не найдена", show_alert=True)
            return
        
        # Проверяем что это команда пользователя
        user = await UserRepository.get_by_telegram_id(callback.from_user.id)
        if team.captain_id != user.id:
            await callback.answer("❌ Это не ваша команда", show_alert=True)
            return
        
        # Получаем игроков
        main_players = await PlayerRepository.get_main_players(team_id)
        substitute_players = await PlayerRepository.get_substitute_players(team_id)
        
        # Формируем текст
        status_text = {
            TeamStatus.PENDING.value: "⏳ Ожидает модерации",
            TeamStatus.APPROVED.value: "✅ Одобрена",
            TeamStatus.REJECTED.value: "❌ Отклонена"
        }.get(team.status, "❓ Неизвестно")
        
        text = f"""👥 **{team.name}**

🏆 **Турнир:** {team.tournament.name}
🎮 **Игра:** {team.tournament.game.name}
📊 **Статус:** {status_text}
👤 **Капитан:** {team.captain.full_name}

**Основной состав** ({len(main_players)}/{team.tournament.game.max_players}):
"""
        
        if main_players:
            for i, player in enumerate(main_players, 1):
                text += f"{i}. {player.nickname} (`{player.game_id}`)\n"
        else:
            text += "Нет игроков\n"
        
        text += f"\n**Запасные игроки** ({len(substitute_players)}/{team.tournament.game.max_substitutes}):\n"
        
        if substitute_players:
            for i, player in enumerate(substitute_players, 1):
                text += f"{i}. {player.nickname} (`{player.game_id}`)\n"
        else:
            text += "Нет запасных\n"
        
        # Причина отклонения
        if team.status == TeamStatus.REJECTED.value and team.rejection_reason:
            text += f"\n⚠️ **Причина отклонения:**\n{team.rejection_reason}"
        
        # Кнопки действий
        keyboard = []
        
        # Если команда на модерации или отклонена, можно редактировать
        if team.status in [TeamStatus.PENDING.value, TeamStatus.REJECTED.value]:
            keyboard.append([
                InlineKeyboardButton(
                    text="📝 Редактировать состав",
                    callback_data=f"team:edit_roster_{team_id}"
                )
            ])
            keyboard.append([
                InlineKeyboardButton(
                    text="🗑️ Удалить команду",
                    callback_data=f"team:delete_confirm_{team_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 К списку команд",
                callback_data="menu:my_teams"
            )
        ])
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(UserStates.viewing_team)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка просмотра команды: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ========== СОЗДАНИЕ КОМАНДЫ - ШАГ 1: ВЫБОР ТУРНИРА ==========

@teams_router.callback_query(F.data == "team:create")
async def start_team_creation(callback: CallbackQuery, state: FSMContext):
    """Начало создания команды - выбор турнира"""
    try:
        user = await UserRepository.get_by_telegram_id(callback.from_user.id)
        
        # Получаем активные турниры (в режиме регистрации)
        tournaments = await TournamentRepository.get_active_tournaments()
        
        if not tournaments:
            text = """❌ **Нет доступных турниров**

К сожалению, сейчас нет турниров открытых для регистрации.

Следите за объявлениями о новых турнирах!"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="menu:my_teams"
                    )
                ]
            ]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            return
        
        text = """➕ **Создание новой команды**

**Шаг 1/5:** Выберите турнир

Выберите турнир, в котором хотите участвовать:"""
        
        keyboard = []
        
        for tournament in tournaments:
            # Проверяем, не зарегистрирован ли уже
            is_registered = await TeamRepository.is_captain_registered(user.id, tournament.id)
            
            if is_registered:
                button_text = f"✅ {tournament.name} (уже участвуете)"
                callback_data = "team:already_registered"
            else:
                # Проверяем заполненность
                teams_count = await TeamRepository.get_approved_teams_count(tournament.id)
                button_text = f"🏆 {tournament.name} ({teams_count}/{tournament.max_teams})"
                callback_data = f"team:select_tournament_{tournament.id}"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=callback_data
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="menu:my_teams"
            )
        ])
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(UserStates.registering_team_selecting_tournament)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала создания команды: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@teams_router.callback_query(F.data == "team:already_registered")
async def already_registered_handler(callback: CallbackQuery):
    """Обработка попытки зарегистрироваться повторно"""
    await callback.answer(
        "❌ Вы уже зарегистрированы на этот турнир!",
        show_alert=True
    )


# ========== СОЗДАНИЕ КОМАНДЫ - ШАГ 2: ВВОД НАЗВАНИЯ ==========

@teams_router.callback_query(F.data.startswith("team:select_tournament_"))
async def select_tournament(callback: CallbackQuery, state: FSMContext):
    """Выбор турнира и ввод названия команды"""
    try:
        tournament_id = int(callback.data.split("_")[2])
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Проверяем что турнир открыт для регистрации
        if tournament.status != "registration":
            await callback.answer("❌ Регистрация на этот турнир закрыта", show_alert=True)
            return
        
        # Проверяем что турнир не заполнен
        teams_count = await TeamRepository.get_approved_teams_count(tournament_id)
        if teams_count >= tournament.max_teams:
            await callback.answer("❌ Турнир уже заполнен", show_alert=True)
            return
        
        # ПРОВЕРКА ПОДПИСКИ НА ОБЯЗАТЕЛЬНЫЕ КАНАЛЫ
        if tournament.required_channels:
            from aiogram import Bot
            bot = callback.bot
            
            not_subscribed = []
            for channel_username in tournament.required_channels:
                try:
                    # Проверяем подписку пользователя на канал
                    member = await bot.get_chat_member(f"@{channel_username}", callback.from_user.id)
                    
                    # Статусы: creator, administrator, member - подписан
                    # left, kicked - не подписан
                    if member.status in ['left', 'kicked']:
                        not_subscribed.append(channel_username)
                        
                except Exception as e:
                    logger.warning(f"Ошибка проверки подписки на @{channel_username}: {e}")
                    # Если канал недоступен или ошибка, добавляем в список
                    not_subscribed.append(channel_username)
            
            # Если есть неподписанные каналы, блокируем регистрацию
            if not_subscribed:
                channels_list = "\n".join([f"• @{ch}" for ch in not_subscribed])
                text = f"""❌ **Требуется подписка**

Для участия в турнире **"{tournament.name}"** необходимо подписаться на следующие каналы:

{channels_list}

После подписки попробуйте снова."""
                
                keyboard = [
                    [
                        InlineKeyboardButton(
                            text="🔙 Назад к выбору турнира",
                            callback_data="team:create"
                        )
                    ]
                ]
                
                await safe_edit_message(
                    callback.message, text, parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
                await callback.answer("❌ Подпишитесь на обязательные каналы", show_alert=True)
                return
        
        # Сохраняем выбранный турнир
        await state.update_data(
            tournament_id=tournament_id,
            tournament_name=tournament.name,
            game_id=tournament.game_id,
            game_name=tournament.game.name,
            max_players=tournament.game.max_players,
            max_substitutes=tournament.game.max_substitutes
        )
        
        text = f"""➕ **Создание команды для "{tournament.name}"**

**Шаг 2/5:** Название команды

🎮 Игра: {tournament.game.name}
👥 Состав: {tournament.game.max_players} основных + {tournament.game.max_substitutes} запасных

Введите название вашей команды:

▪️ Минимум 3 символа
▪️ Максимум 50 символов
▪️ Должно быть уникальным в этом турнире"""
        
        keyboard = [
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
        await state.set_state(UserStates.registering_team_entering_name)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка выбора турнира: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@teams_router.message(StateFilter(UserStates.registering_team_entering_name))
async def process_team_name(message: Message, state: FSMContext):
    """Обработка названия команды"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение.")
        return
    
    team_name = message.text.strip()
    
    # Валидация
    if len(team_name) < 3:
        await message.answer("❌ Название слишком короткое (минимум 3 символа).\n\nПопробуйте ещё раз:")
        return
    
    if len(team_name) > 50:
        await message.answer("❌ Название слишком длинное (максимум 50 символов).\n\nПопробуйте ещё раз:")
        return
    
    try:
        data = await state.get_data()
        tournament_id = data.get('tournament_id')
        
        # Проверка уникальности в турнире
        existing_team = await TeamRepository.get_by_name_and_tournament(tournament_id, team_name)
        if existing_team:
            await message.answer(f"❌ Команда с названием '{team_name}' уже зарегистрирована на этот турнир.\n\nВведите другое название:")
            return
        
        # Сохраняем название
        await state.update_data(team_name=team_name)
        
        # Переходим к логотипу (опционально)
        text = f"""✅ **Название принято:** {team_name}

**Шаг 3/5:** Логотип команды (опционально)

Вы можете загрузить логотип вашей команды или пропустить этот шаг.

Формат: JPG, PNG
Размер: до 5 МБ"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⏭️ Пропустить",
                    callback_data="team:skip_logo"
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
        await state.set_state(UserStates.registering_team_uploading_logo)
        
    except Exception as e:
        logger.error(f"Ошибка обработки названия команды: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


# ПРОДОЛЖЕНИЕ СЛЕДУЕТ...