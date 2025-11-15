"""
Обработчики турниров
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from datetime import datetime

from database.repositories.user_repository import UserRepository
from database.repositories.tournament_repository import TournamentRepository
from database.repositories.game_repository import GameRepository
from utils.localization import Localization
from utils.message_utils import safe_edit_message
from utils.keyboards import get_tournaments_keyboard, get_back_keyboard, get_games_selection_keyboard
from utils.text_formatting import escape_html
from .states import UserStates

# Создаем роутер для турниров
tournaments_router = Router()
logger = logging.getLogger(__name__)


@tournaments_router.callback_query(F.data == "menu:tournaments", StateFilter(UserStates.main_menu))
async def show_game_selection(callback: CallbackQuery):
    """Показать выбор игры для турниров"""
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    localization = Localization()
    localization.set_language(user.language)
    
    # Получаем все активные игры
    games = await GameRepository.get_all_active()
    
    if not games:
        await safe_edit_message(
            callback.message,
            "❌ **Нет доступных игр**\n\nИгры еще не добавлены в систему.",
            reply_markup=get_back_keyboard(localization),
            parse_mode="Markdown"
        )
        return
    
    text = "🎮 **Выберите игру для просмотра турниров:**"
    
    await safe_edit_message(
        callback.message,
        text,
        reply_markup=get_games_selection_keyboard(games, localization),
        parse_mode="Markdown"
    )
    await callback.answer()


@tournaments_router.callback_query(F.data.startswith("user_game:"))
async def show_tournaments_by_game(callback: CallbackQuery):
    """Показать турниры выбранной игры"""
    game_id = int(callback.data.split(":")[1])
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    localization = Localization()
    localization.set_language(user.language)
    
    # Получаем игру
    game = await GameRepository.get_by_id(game_id)
    if not game:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return
    
    # Получаем активные турниры для региона пользователя и выбранной игры
    all_tournaments = await TournamentRepository.get_active_tournaments(user.region)
    tournaments = [t for t in all_tournaments if t.game_id == game_id]
    
    safe_game_name = escape_html(game.name)
    
    if not tournaments:
        text = f"❌ <b>Нет активных турниров по игре {safe_game_name}</b>\n\nПопробуйте выбрать другую игру или зайдите позже."
        
        # Если есть логотип игры, отправляем с фото
        if game.icon_file_id:
            try:
                await callback.message.delete()
                await callback.bot.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=game.icon_file_id,
                    caption=text,
                    reply_markup=get_back_keyboard(localization),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки логотипа игры: {e}")
                await safe_edit_message(
                    callback.message,
                    text,
                    reply_markup=get_back_keyboard(localization),
                    parse_mode="HTML"
                )
        else:
            await safe_edit_message(
                callback.message,
                text,
                reply_markup=get_back_keyboard(localization),
                parse_mode="HTML"
            )
        await callback.answer()
        return
    
    # Формируем список турниров
    tournaments_text = f"🎮 <b>Турниры по игре: {safe_game_name}</b>\n\n"
    
    for tournament in tournaments:
        # Проверяем статус регистрации
        now = datetime.utcnow()
        is_registration_open = (
            tournament.status == "registration" and 
            tournament.registration_start <= now <= tournament.registration_end
        )
        
        status_emoji = "✅" if is_registration_open else "🔒"
        safe_tournament_name = escape_html(tournament.name)
        tournaments_text += f"{status_emoji} <b>{safe_tournament_name}</b>\n"
        
        if is_registration_open:
            tournaments_text += "📝 Регистрация открыта\n"
        else:
            tournaments_text += "🔒 Регистрация закрыта\n"
        
        # Считаем зарегистрированные команды
        registered_count = len(tournament.teams) if tournament.teams else 0
        tournaments_text += f"👥 Команд: {registered_count}/{tournament.max_teams}\n\n"
    
    # Если есть логотип игры, отправляем с фото
    if game.icon_file_id:
        try:
            await callback.message.delete()
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=game.icon_file_id,
                caption=tournaments_text,
                reply_markup=get_tournaments_keyboard(tournaments, localization, show_back_to_games=True),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки логотипа игры: {e}")
            await safe_edit_message(
                callback.message,
                tournaments_text,
                reply_markup=get_tournaments_keyboard(tournaments, localization, show_back_to_games=True),
                parse_mode="HTML"
            )
    else:
        await safe_edit_message(
            callback.message,
            tournaments_text,
            reply_markup=get_tournaments_keyboard(tournaments, localization, show_back_to_games=True),
            parse_mode="HTML"
        )
    
    await callback.answer()


@tournaments_router.callback_query(F.data.startswith("tournament:"))
async def show_tournament_details(callback: CallbackQuery):
    """Показать детали конкретного турнира"""
    tournament_id = int(callback.data.split(":")[1])
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    localization = Localization()
    localization.set_language(user.language)
    
    # Получаем турнир
    tournament = await TournamentRepository.get_by_id(tournament_id)
    if not tournament:
        await callback.answer("❌ Турнир не найден", show_alert=True)
        return
    
    # Формируем описание турнира
    now = datetime.utcnow()
    is_registration_open = (
        tournament.status == "registration" and 
        tournament.registration_start <= now <= tournament.registration_end
    )
    
    from utils.datetime_utils import format_datetime_for_user
    
    # Форматируем формат турнира для отображения
    format_names = {
        'single_elimination': 'Одиночное выбывание',
        'double_elimination': 'Двойное выбывание',
        'round_robin': 'Круговая система',
        'group_stage_playoffs': 'Групповая стадия + плей-офф'
    }
    format_display = format_names.get(tournament.format, tournament.format)
    
    # Экранируем данные для HTML
    safe_name = escape_html(tournament.name)
    safe_game_name = escape_html(tournament.game.name)
    safe_format = escape_html(format_display)
    
    # Статус регистрации
    registered_count = len(tournament.teams) if tournament.teams else 0
    
    text = f"""🏆 <b>{safe_name}</b>

🎮 <b>Игра:</b> {safe_game_name}
📋 <b>Формат:</b> {safe_format}
👥 <b>Максимум команд:</b> {tournament.max_teams}

📅 <b>Даты ({user.timezone}):</b>
📝 Регистрация: <i>{format_datetime_for_user(tournament.registration_start, user.timezone)} - {format_datetime_for_user(tournament.registration_end, user.timezone)}</i>
🏁 Начало турнира: <i>{format_datetime_for_user(tournament.tournament_start, user.timezone)}</i>

"""
    
    if tournament.description:
        # Ограничиваем описание для caption (макс 1024 символа для всего caption)
        safe_description = escape_html(tournament.description)
        if len(text) + len(safe_description) > 900:  # Оставляем запас
            safe_description = safe_description[:800] + "..."
        text += f"📄 <b>Описание:</b>\n{safe_description}\n\n"
    
    # Статус регистрации
    text += f"👥 <b>Зарегистрировано команд:</b> {registered_count}/{tournament.max_teams}\n\n"
    
    if is_registration_open:
        text += "✅ <b>Регистрация открыта!</b>"
    else:
        text += "🔒 <b>Регистрация закрыта</b>"
    
    # Ограничиваем общую длину caption (максимум 1024 символа)
    if len(text) > 1020:
        text = text[:1000] + "...\n\n" + text.split("\n\n")[-1]  # Сохраняем последний блок со статусом
    
    # Создаем клавиатуру
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    if is_registration_open and registered_count < tournament.max_teams:
        builder.button(
            text="✅ Зарегистрировать команду",
            callback_data=f"register_team:{tournament_id}"
        )
    
    builder.button(text="◀️ Назад к турнирам", callback_data=f"user_game:{tournament.game_id}")
    builder.adjust(1)
    
    # Удаляем старое сообщение
    try:
        await callback.message.delete()
    except:
        pass
    
    # Если есть логотип турнира, отправляем с фото БЕЗ кнопок
    if tournament.logo_file_id:
        try:
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=tournament.logo_file_id,
                caption=text,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки логотипа турнира: {e}")
            # Если не удалось отправить с фото, отправляем текстом
            await callback.message.answer(text, parse_mode="HTML")
    else:
        # Если нет логотипа, отправляем просто текст
        await callback.message.answer(text, parse_mode="HTML")
    
    # Отправляем файл правил С КНОПКАМИ (если есть файл)
    if tournament.rules_file_id:
        try:
            await callback.message.answer_document(
                document=tournament.rules_file_id,
                caption=f"📄 <b>Регламент турнира</b>\n\n{escape_html(tournament.rules_file_name or 'Правила.pdf')}",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки файла правил турнира: {e}")
            # Если не удалось отправить файл, отправляем кнопки отдельным сообщением
            await callback.message.answer(
                "─────────────────────\n<b>Выберите действие:</b>",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
    else:
        # Если нет файла правил, отправляем кнопки отдельным сообщением
        await callback.message.answer(
            "─────────────────────\n<b>Выберите действие:</b>",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    
    await callback.answer()


@tournaments_router.callback_query(F.data.startswith("register_team:"))
async def register_team_for_tournament(callback: CallbackQuery, state: FSMContext):
    """Регистрация команды на турнир - переадресация на teams.py логику"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        tournament_id = int(callback.data.split(":")[1])
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Проверяем что турнир открыт для регистрации
        now = datetime.utcnow()
        if tournament.status != "registration":
            await callback.answer("❌ Регистрация на этот турнир закрыта", show_alert=True)
            return
        
        if not (tournament.registration_start <= now <= tournament.registration_end):
            await callback.answer("❌ Регистрация на этот турнир еще не началась или уже закончилась", show_alert=True)
            return
        
        # Проверяем что турнир не заполнен
        from database.repositories.team_repository import TeamRepository
        teams_count = await TeamRepository.get_approved_teams_count(tournament_id)
        if teams_count >= tournament.max_teams:
            await callback.answer("❌ Турнир уже заполнен", show_alert=True)
            return
        
        # ПРОВЕРКА ПОДПИСКИ НА ОБЯЗАТЕЛЬНЫЕ КАНАЛЫ
        required_channels_list = tournament.required_channels_list
        if required_channels_list:
            from utils.channel_checker import check_all_channels_subscription, format_channel_url, format_channel_name
            
            # Используем модуль channel_checker для консистентности
            is_subscribed, unsubscribed = await check_all_channels_subscription(
                callback.bot,
                callback.from_user.id,
                required_channels_list
            )
            
            if not is_subscribed:
                tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                text = f"""⚠️ <b>Требуется подписка</b>

Для участия в турнире <b>"{tournament_name}"</b> необходимо подписаться на следующие каналы:

"""
                
                # Создаем клавиатуру с кнопками подписки
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                builder = InlineKeyboardBuilder()
                
                for channel in unsubscribed:
                    channel_display = format_channel_name(channel)
                    channel_url = format_channel_url(channel)
                    
                    text += f"• {channel_display}\n"
                    builder.button(text=f"📢 {channel_display}", url=channel_url)
                
                text += "\nПосле подписки попробуйте зарегистрироваться снова."
                
                builder.button(text="◀️ Назад к турниру", callback_data=f"tournament:{tournament_id}")
                builder.adjust(1)
                
                await safe_edit_message(
                    callback.message,
                    text,
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
                return
        
        # Сохраняем ID турнира в состоянии (используем стандартное имя tournament_id)
        await state.update_data(
            tournament_id=tournament_id,
            tournament_name=tournament.name,
            game_id=tournament.game_id,
            game_name=tournament.game.name if hasattr(tournament, 'game') and tournament.game else 'Unknown',
            max_players=tournament.game.max_players if hasattr(tournament, 'game') and tournament.game else 5,
            max_substitutes=tournament.game.max_substitutes if hasattr(tournament, 'game') and tournament.game else 0
        )
        
        # Переходим к вводу названия команды
        from .states import UserStates
        
        text = f"""📝 **Регистрация команды на турнир**

🏆 Турнир: **{tournament.name}**
🎮 Игра: **{tournament.game.name}**

Введите название вашей команды:

*Требования:*
▪️ От 3 до 50 символов
▪️ Можно использовать буквы, цифры и спецсимволы"""
        
        await safe_edit_message(
            callback.message,
            text,
            parse_mode="Markdown"
        )
        
        await state.set_state(UserStates.registering_team_entering_name)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при регистрации команды: {e}")
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)