"""
Хендлеры для статистики и аналитики
"""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database.repositories import UserRepository, TournamentRepository, TeamRepository
from utils.localization import _
from utils.message_utils import safe_edit_message
from .keyboards import get_statistics_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "admin:download_database")
async def download_database(callback: CallbackQuery):
    """Отправка файла базы данных администратору"""
    try:
        import os
        from config.settings import settings
        
        # Путь к файлу БД
        db_path = "tournament_bot.db"
        
        if not os.path.exists(db_path):
            await callback.answer("❌ Файл базы данных не найден", show_alert=True)
            return
        
        # Получаем размер файла
        file_size = os.path.getsize(db_path)
        file_size_mb = file_size / (1024 * 1024)
        
        # Отправляем файл
        from aiogram.types import FSInputFile
        
        try:
            db_file = FSInputFile(db_path)
            await callback.message.answer_document(
                document=db_file,
                caption=f"💾 <b>База данных бота</b>\n\n📊 Размер: {file_size_mb:.2f} МБ\n📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                parse_mode="HTML"
            )
            await callback.answer("✅ База данных отправлена")
        except Exception as e:
            logger.error(f"Ошибка отправки файла БД: {e}")
            await callback.answer("❌ Ошибка отправки файла", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка получения БД: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "admin:statistics")
async def statistics_menu(callback: CallbackQuery, state: FSMContext):
    """Меню статистики"""
    await state.clear()

    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    language = user.language if user else "ru"
    
    text = _("""
📊 Статистика и аналитика

Выберите тип статистики для просмотра:
""", language)
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=get_statistics_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "admin:general_stats")
async def general_statistics(callback: CallbackQuery, state: FSMContext):
    """Общая статистика"""
    try:

        # Получаем общую статистику
        total_users = await UserRepository.get_total_count()
        total_tournaments = await TournamentRepository.get_total_count()
        total_teams = await TeamRepository.get_total_count()
        
        # Статистика за последние 30 дней
        date_30_days_ago = datetime.now() - timedelta(days=30)
        new_users_30d = await UserRepository.get_count_since(date_30_days_ago)
        new_tournaments_30d = await TournamentRepository.get_count_since(date_30_days_ago)
        new_teams_30d = await TeamRepository.get_count_since(date_30_days_ago)
        
        # Статистика за последние 7 дней
        date_7_days_ago = datetime.now() - timedelta(days=7)
        new_users_7d = await UserRepository.get_count_since(date_7_days_ago)
        new_tournaments_7d = await TournamentRepository.get_count_since(date_7_days_ago)
        new_teams_7d = await TeamRepository.get_count_since(date_7_days_ago)
        
        # Статистика по языкам
        language_stats = await UserRepository.get_language_statistics()
        language_text = "\n".join([
            f"• {lang.upper()}: {count}" 
            for lang, count in language_stats.items()
        ])
        
        # Статистика по регионам
        region_stats = await UserRepository.get_region_statistics()
        region_text = "\n".join([
            f"• {region.upper()}: {count}" 
            for region, count in region_stats.items()
        ])
        
        text = _("""
📊 Общая статистика

📈 Всего в системе:
👥 Пользователей: {total_users}
🏆 Турниров: {total_tournaments}
👥 Команд: {total_teams}

📅 За последние 30 дней:
➕ Новых пользователей: {users_30d}
➕ Новых турниров: {tournaments_30d}
➕ Новых команд: {teams_30d}

📅 За последние 7 дней:
➕ Новых пользователей: {users_7d}
➕ Новых турниров: {tournaments_7d}
➕ Новых команд: {teams_7d}

🌍 По языкам:
{languages}

🗺️ По регионам:
{regions}

📅 Обновлено: {updated}
""", "ru").format(
            total_users=total_users,
            total_tournaments=total_tournaments,
            total_teams=total_teams,
            users_30d=new_users_30d,
            tournaments_30d=new_tournaments_30d,
            teams_30d=new_teams_30d,
            users_7d=new_users_7d,
            tournaments_7d=new_tournaments_7d,
            teams_7d=new_teams_7d,
            languages=language_text or "Нет данных",
            regions=region_text or "Нет данных",
            updated=datetime.now().strftime("%d.%m.%Y %H:%M")
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения общей статистики: {e}")
        text = _("""
❌ Ошибка получения статистики

Произошла ошибка при загрузке данных.
Попробуйте позже.
""", "ru")
    
    keyboard = [[
        InlineKeyboardButton(
            text=_("🔙 Назад к статистике", "ru"),
            callback_data="admin:statistics"
        )
    ]]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "admin:tournament_stats")
async def tournament_statistics(callback: CallbackQuery, state: FSMContext):
    """Статистика турниров"""
    try:

        # Общая статистика турниров
        total_tournaments = await TournamentRepository.get_total_count()
        active_tournaments = await TournamentRepository.get_active_count()
        completed_tournaments = await TournamentRepository.get_completed_count()
        upcoming_tournaments = await TournamentRepository.get_upcoming_count()
        
        # Статистика по играм
        game_stats = await TournamentRepository.get_game_statistics()
        game_text = "\n".join([
            f"• {game}: {count} турниров" 
            for game, count in game_stats.items()
        ])
        
        # Топ турниров по количеству команд
        top_tournaments = await TournamentRepository.get_top_by_teams(5)
        top_text = "\n".join([
            f"• {tournament.name}: {len(tournament.teams)} команд" 
            for tournament in top_tournaments
        ])
        
        text = _("""
🏆 Статистика турниров

📊 Общие показатели:
🎯 Всего турниров: {total}
▶️ Активных: {active}
✅ Завершенных: {completed}
⏳ Предстоящих: {upcoming}

🎮 По играм:
{games}

👑 Топ турниров по командам:
{top_tournaments}

📅 Обновлено: {updated}
""", "ru").format(
            total=total_tournaments,
            active=active_tournaments,
            completed=completed_tournaments,
            upcoming=upcoming_tournaments,
            games=game_text or "Нет данных",
            top_tournaments=top_text or "Нет данных",
            updated=datetime.now().strftime("%d.%m.%Y %H:%M")
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики турниров: {e}")
        text = _("""
❌ Ошибка получения статистики

Произошла ошибка при загрузке данных.
Попробуйте позже.
""", "ru")
    
    keyboard = [[
        InlineKeyboardButton(
            text=_("🔙 Назад к статистике", "ru"),
            callback_data="admin:statistics"
        )
    ]]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "admin:team_stats")
async def team_statistics(callback: CallbackQuery, state: FSMContext):
    """Статистика команд"""
    try:

        # Общая статистика команд
        total_teams = await TeamRepository.get_total_count()
        active_teams = await TeamRepository.get_active_count()
        pending_teams = await TeamRepository.get_pending_count()
        blocked_teams = await TeamRepository.get_blocked_count()
        
        # Средний размер команд
        avg_team_size = await TeamRepository.get_average_team_size()
        
        # Статистика по турнирам
        tournament_stats = await TeamRepository.get_tournament_participation_stats()
        tournament_text = "\n".join([
            f"• {tournament}: {count} команд" 
            for tournament, count in tournament_stats.items()
        ])
        
        # Топ капитанов по количеству команд
        top_captains = await TeamRepository.get_top_captains(5)
        captains_text = "\n".join([
            f"• {captain}: {count} команд" 
            for captain, count in top_captains.items()
        ])
        
        text = _("""
👥 Статистика команд

📊 Общие показатели:
🎯 Всего команд: {total}
✅ Активных: {active}
⏳ На рассмотрении: {pending}
🚫 Заблокированных: {blocked}

📏 Средний размер команды: {avg_size} участников

🏆 По турнирам:
{tournaments}

👑 Топ капитанов:
{captains}

📅 Обновлено: {updated}
""", "ru").format(
            total=total_teams,
            active=active_teams,
            pending=pending_teams,
            blocked=blocked_teams,
            avg_size=round(avg_team_size, 1) if avg_team_size else 0,
            tournaments=tournament_text or "Нет данных",
            captains=captains_text or "Нет данных",
            updated=datetime.now().strftime("%d.%m.%Y %H:%M")
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики команд: {e}")
        text = _("""
❌ Ошибка получения статистики

Произошла ошибка при загрузке данных.
Попробуйте позже.
""", "ru")
    
    keyboard = [[
        InlineKeyboardButton(
            text=_("🔙 Назад к статистике", "ru"),
            callback_data="admin:statistics"
        )
    ]]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "admin:user_stats")
async def user_statistics(callback: CallbackQuery, state: FSMContext):
    """Статистика пользователей"""
    try:

        # Общая статистика пользователей
        total_users = await UserRepository.get_total_count()
        active_users = await UserRepository.get_active_count()
        admin_users = len(await UserRepository.get_admins())
        blocked_users = len(await UserRepository.get_blocked_users())
        
        # Статистика активности (последние 30 дней)
        date_30_days_ago = datetime.now() - timedelta(days=30)
        active_30d = await UserRepository.get_active_since(date_30_days_ago)
        
        # Статистика активности (последние 7 дней)
        date_7_days_ago = datetime.now() - timedelta(days=7)
        active_7d = await UserRepository.get_active_since(date_7_days_ago)
        
        # Статистика регистраций по дням за последнюю неделю
        daily_registrations = await UserRepository.get_daily_registrations(7)
        daily_text = "\n".join([
            f"• {date}: {count} пользователей" 
            for date, count in daily_registrations.items()
        ])
        
        # Топ пользователей по активности (последнее обновление)
        top_active = await UserRepository.get_most_active_users(5)
        active_text = "\n".join([
            f"• {user}: последнее обновление {activity}" 
            for user, activity in top_active.items()
        ])
        
        text = _("""
👤 Статистика пользователей

📊 Общие показатели:
🎯 Всего пользователей: {total}
▶️ Активных: {active}
👑 Администраторов: {admins}
🚫 Заблокированных: {blocked}

📈 Активность:
🌟 Обновлений за 30 дней: {active_30d}
🔥 Обновлений за 7 дней: {active_7d}

📅 Регистрации за неделю:
{daily}

🏆 Самые активные (по обновлению):
{top_active}

📅 Обновлено: {updated}
""", "ru").format(
            total=total_users,
            active=active_users,
            admins=admin_users,
            blocked=blocked_users,
            active_30d=active_30d,
            active_7d=active_7d,
            daily=daily_text or "Нет данных",
            top_active=active_text or "Нет данных",
            updated=datetime.now().strftime("%d.%m.%Y %H:%M")
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики пользователей: {e}")
        text = _("""
❌ Ошибка получения статистики

Произошла ошибка при загрузке данных.
Попробуйте позже.
""", "ru")
    
    keyboard = [[
        InlineKeyboardButton(
            text=_("🔙 Назад к статистике", "ru"),
            callback_data="admin:statistics"
        )
    ]]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "admin:export_data")
async def export_data(callback: CallbackQuery, state: FSMContext):
    """Экспорт данных - меню выбора формата"""
    text = _("""
📊 Экспорт данных

Выберите формат экспорта:
""", "ru")
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="📄 CSV файлы",
                callback_data="admin:export_csv"
            ),
            InlineKeyboardButton(
                text="📋 JSON файлы", 
                callback_data="admin:export_json"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Excel файл",
                callback_data="admin:export_excel"
            )
        ],
        [
            InlineKeyboardButton(
                text=_("🔙 Назад к статистике", "ru"),
                callback_data="admin:statistics"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "admin:export_csv")
async def export_csv_menu(callback: CallbackQuery, state: FSMContext):
    """Меню экспорта CSV"""
    text = _("""
📄 Экспорт в CSV

Выберите данные для экспорта:
""", "ru")
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="👤 Пользователи",
                callback_data="admin:export_users_csv"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Команды",
                callback_data="admin:export_teams_csv"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏆 Турниры",
                callback_data="admin:export_tournaments_csv"
            )
        ],
        [
            InlineKeyboardButton(
                text=_("🔙 Назад к экспорту", "ru"),
                callback_data="admin:export_data"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "admin:export_json")
async def export_json_menu(callback: CallbackQuery, state: FSMContext):
    """Меню экспорта JSON"""
    text = _("""
📋 Экспорт в JSON

Выберите данные для экспорта:
""", "ru")
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="👤 Пользователи",
                callback_data="admin:export_users_json"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Команды",
                callback_data="admin:export_teams"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏆 Турниры",
                callback_data="admin:export_tournaments_json"
            )
        ],
        [
            InlineKeyboardButton(
                text=_("🔙 Назад к экспорту", "ru"),
                callback_data="admin:export_data"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

# CSV экспорт хэндлеры
@router.callback_query(F.data == "admin:export_users_csv")
async def export_users_csv_handler(callback: CallbackQuery, state: FSMContext):
    """Экспорт пользователей в CSV"""
    await callback.answer("Генерирую CSV файл пользователей...")
    
    try:
        from services.export_service import export_service
        from aiogram.types import BufferedInputFile
        
        # Генерируем CSV
        csv_data = await export_service.export_users_csv()
        csv_content = csv_data.getvalue().encode('utf-8-sig')  # BOM для правильного отображения в Excel
        
        # Отправляем файл
        file = BufferedInputFile(csv_content, filename=f"users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        await callback.message.answer_document(
            document=file,
            caption="📄 Экспорт пользователей в формате CSV"
        )
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")

@router.callback_query(F.data == "admin:export_teams_csv")
async def export_teams_csv_handler(callback: CallbackQuery, state: FSMContext):
    """Экспорт команд в CSV"""
    await callback.answer("Генерирую CSV файл команд...")
    
    try:
        from services.export_service import export_service
        from aiogram.types import BufferedInputFile
        
        # Генерируем CSV
        csv_data = await export_service.export_teams_csv()
        csv_content = csv_data.getvalue().encode('utf-8-sig')
        
        # Отправляем файл
        file = BufferedInputFile(csv_content, filename=f"teams_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        await callback.message.answer_document(
            document=file,
            caption="📄 Экспорт команд в формате CSV"
        )
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")

@router.callback_query(F.data == "admin:export_tournaments_csv")
async def export_tournaments_csv_handler(callback: CallbackQuery, state: FSMContext):
    """Экспорт турниров в CSV"""
    await callback.answer("Генерирую CSV файл турниров...")
    
    try:
        from services.export_service import export_service
        from aiogram.types import BufferedInputFile
        
        # Генерируем CSV
        csv_data = await export_service.export_tournaments_csv()
        csv_content = csv_data.getvalue().encode('utf-8-sig')
        
        # Отправляем файл
        file = BufferedInputFile(csv_content, filename=f"tournaments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        await callback.message.answer_document(
            document=file,
            caption="📄 Экспорт турниров в формате CSV"
        )
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")

# JSON экспорт хэндлеры
@router.callback_query(F.data == "admin:export_users_json")
async def export_users_json_handler(callback: CallbackQuery, state: FSMContext):
    """Экспорт пользователей в JSON"""
    await callback.answer("Генерирую JSON файл пользователей...")
    
    try:
        from services.export_service import export_service
        from aiogram.types import BufferedInputFile
        
        # Генерируем JSON
        json_content = await export_service.export_users_json()
        
        # Отправляем файл
        file = BufferedInputFile(json_content.encode('utf-8'), filename=f"users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        await callback.message.answer_document(
            document=file,
            caption="📋 Экспорт пользователей в формате JSON"
        )
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")

@router.callback_query(F.data == "admin:export_teams_json")
async def export_teams_json_handler(callback: CallbackQuery, state: FSMContext):
    """Экспорт команд в JSON"""
    await callback.answer("Генерирую JSON файл команд...")
    
    try:
        from services.export_service import export_service
        from aiogram.types import BufferedInputFile
        
        # Генерируем JSON
        json_content = await export_service.export_teams_json()
        
        # Отправляем файл
        file = BufferedInputFile(json_content.encode('utf-8'), filename=f"teams_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        await callback.message.answer_document(
            document=file,
            caption="📋 Экспорт команд в формате JSON"
        )
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")

@router.callback_query(F.data == "admin:export_tournaments_json")
async def export_tournaments_json_handler(callback: CallbackQuery, state: FSMContext):
    """Экспорт турниров в JSON"""
    await callback.answer("Генерирую JSON файл турниров...")
    
    try:
        from services.export_service import export_service
        from aiogram.types import BufferedInputFile
        
        # Генерируем JSON
        json_content = await export_service.export_tournaments_json()
        
        # Отправляем файл
        file = BufferedInputFile(json_content.encode('utf-8'), filename=f"tournaments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        await callback.message.answer_document(
            document=file,
            caption="📋 Экспорт турниров в формате JSON"
        )
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")

# Excel экспорт хэндлер
@router.callback_query(F.data == "admin:export_excel")
async def export_excel_handler(callback: CallbackQuery, state: FSMContext):
    """Экспорт всех данных в Excel"""
    await callback.answer("Генерирую Excel файл со всеми данными...")
    
    try:
        from services.export_service import export_service
        from aiogram.types import BufferedInputFile
        
        # Генерируем Excel
        excel_data = await export_service.export_excel()
        excel_content = excel_data.getvalue()
        
        # Отправляем файл
        file = BufferedInputFile(excel_content, filename=f"enas_game_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        await callback.message.answer_document(
            document=file,
            caption="📊 Полный экспорт данных в формате Excel"
        )
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")