"""
Статистика турниров
"""
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from database.repositories import TournamentRepository
from utils.message_utils import safe_edit_message

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "admin:tournament_stats")
async def tournament_statistics_menu(callback: CallbackQuery, state: FSMContext):
    """Меню статистики турниров"""
    await state.clear()
    
    try:
        # Получаем общую статистику
        total_tournaments = await TournamentRepository.get_total_count()
        active_tournaments = await TournamentRepository.get_active_count()
        completed_tournaments = total_tournaments - active_tournaments
        
        # Получаем турниры за последние 30 дней
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_tournaments = await TournamentRepository.get_tournaments_since(thirty_days_ago)
        
        # Получаем статистику по статусам
        status_stats = await TournamentRepository.get_status_statistics()
        
        text = f"""📊 **Статистика турниров**

📈 **Общая статистика:**
🏆 Всего турниров: **{total_tournaments}**
🏃 Активных: **{active_tournaments}**
✅ Завершенных: **{completed_tournaments}**

📅 **За последние 30 дней:**
🆕 Создано турниров: **{len(recent_tournaments) if recent_tournaments else 0}**

📋 **По статусам:**"""
        
        # Добавляем статистику по статусам
        status_names = {
            'registration': '📝 Регистрация',
            'in_progress': '🏃 В процессе',
            'completed': '✅ Завершен',
            'cancelled': '❌ Отменен',
            'paused': '⏸️ Приостановлен'
        }
        
        if status_stats:
            for status, count in status_stats.items():
                status_name = status_names.get(status, f"❓ {status}")
                text += f"\n{status_name}: **{count}**"
        else:
            text += "\n*Нет данных*"
        
        # Получаем популярные игры
        popular_games = await TournamentRepository.get_popular_games()
        
        if popular_games:
            text += "\n\n🎮 **Популярные игры:**"
            for game_name, count in popular_games[:5]:  # Топ 5
                text += f"\n• {game_name}: **{count}** турниров"
        
        # Добавляем информацию о форматах
        format_stats = await TournamentRepository.get_format_statistics()
        
        if format_stats:
            text += "\n\n🏆 **Популярные форматы:**"
            format_names = {
                'single_elimination': 'Одиночное исключение',
                'double_elimination': 'Двойное исключение',
                'round_robin': 'Круговая система',
                'swiss': 'Швейцарская система'
            }
            
            for format_type, count in format_stats.items():
                format_name = format_names.get(format_type, format_type)
                text += f"\n• {format_name}: **{count}**"
        
        keyboard = [
            [
                {
                    "text": "📊 Детальная статистика",
                    "callback_data": "admin:detailed_tournament_stats"
                }
            ],
            [
                {
                    "text": "📈 Статистика по датам",
                    "callback_data": "admin:tournament_date_stats"
                }
            ],
            [
                {
                    "text": "🎮 Статистика по играм",
                    "callback_data": "admin:tournament_game_stats"
                }
            ],
            [
                {
                    "text": "🔄 Обновить",
                    "callback_data": "admin:tournament_stats"
                }
            ],
            [
                {
                    "text": "🔙 Назад",
                    "callback_data": "admin:tournaments"
                }
            ]
        ]
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
                for btn in keyboard
            ]
        )
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown", reply_markup=markup
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики турниров: {e}")
        await callback.answer("❌ Ошибка загрузки статистики", show_alert=True)


@router.callback_query(F.data == "admin:detailed_tournament_stats")
async def detailed_tournament_statistics(callback: CallbackQuery, state: FSMContext):
    """Детальная статистика турниров"""
    try:
        # Получаем детальную статистику
        total_tournaments = await TournamentRepository.get_total_count()
        
        if total_tournaments == 0:
            text = """📊 **Детальная статистика**

❌ **Нет данных**

Турниры еще не созданы в системе."""
        else:
            # Получаем различную статистику
            avg_teams = await TournamentRepository.get_average_teams_per_tournament()
            tournaments_this_month = await TournamentRepository.get_tournaments_this_month()
            tournaments_this_week = await TournamentRepository.get_tournaments_this_week()
            
            text = f"""📊 **Детальная статистика**

📈 **Основные метрики:**
🏆 Всего турниров: **{total_tournaments}**
👥 Среднее количество команд: **{avg_teams:.1f}**

📅 **Временные периоды:**
🗓️ За этот месяц: **{tournaments_this_month}**
📅 За эту неделю: **{tournaments_this_week}**

📊 **Активность:**
⚡ Активных турниров: **{await TournamentRepository.get_active_count()}**
⏸️ Приостановленных: **{await TournamentRepository.get_paused_count()}**
✅ Завершенных: **{await TournamentRepository.get_completed_count()}**

🏅 **Эффективность:**
📈 Коэффициент завершения: **{await TournamentRepository.get_completion_rate():.1f}%**
⏱️ Средняя длительность: **{await TournamentRepository.get_average_duration()} дней**"""
        
        keyboard = [
            [
                {
                    "text": "📊 Экспорт данных",
                    "callback_data": "admin:export_tournament_stats"
                }
            ],
            [
                {
                    "text": "🔄 Обновить",
                    "callback_data": "admin:detailed_tournament_stats"
                }
            ],
            [
                {
                    "text": "🔙 Назад",
                    "callback_data": "admin:tournament_stats"
                }
            ]
        ]
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
                for btn in keyboard
            ]
        )
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown", reply_markup=markup
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения детальной статистики: {e}")
        await callback.answer("❌ Ошибка загрузки статистики", show_alert=True)


@router.callback_query(F.data == "admin:tournament_date_stats")
async def tournament_date_statistics(callback: CallbackQuery, state: FSMContext):
    """Статистика турниров по датам"""
    try:
        # Получаем статистику по датам
        today = datetime.now(timezone.utc).date()
        
        # Статистика за разные периоды
        stats_data = {
            'today': await TournamentRepository.get_tournaments_count_for_date(today),
            'yesterday': await TournamentRepository.get_tournaments_count_for_date(today - timedelta(days=1)),
            'this_week': await TournamentRepository.get_tournaments_this_week(),
            'last_week': await TournamentRepository.get_tournaments_last_week(),
            'this_month': await TournamentRepository.get_tournaments_this_month(),
            'last_month': await TournamentRepository.get_tournaments_last_month(),
        }
        
        text = f"""📈 **Статистика по датам**

📅 **Ежедневная активность:**
🕐 Сегодня: **{stats_data['today']}**
🕐 Вчера: **{stats_data['yesterday']}**

📅 **Недельная активность:**
📊 Эта неделя: **{stats_data['this_week']}**
📊 Прошлая неделя: **{stats_data['last_week']}**

📅 **Месячная активность:**
📊 Этот месяц: **{stats_data['this_month']}**
📊 Прошлый месяц: **{stats_data['last_month']}**

📈 **Тренды:**"""
        
        # Вычисляем тренды
        daily_change = stats_data['today'] - stats_data['yesterday']
        weekly_change = stats_data['this_week'] - stats_data['last_week']
        monthly_change = stats_data['this_month'] - stats_data['last_month']
        
        def format_change(change):
            if change > 0:
                return f"📈 +{change}"
            elif change < 0:
                return f"📉 {change}"
            else:
                return "➖ 0"
        
        text += f"""
🔄 День к дню: {format_change(daily_change)}
🔄 Неделя к неделе: {format_change(weekly_change)}
🔄 Месяц к месяцу: {format_change(monthly_change)}"""
        
        # Получаем пиковые дни
        peak_days = await TournamentRepository.get_peak_creation_days()
        if peak_days:
            text += "\n\n🏆 **Самые активные дни:**"
            for date, count in peak_days[:5]:
                text += f"\n• {date.strftime('%d.%m.%Y')}: **{count}** турниров"
        
        keyboard = [
            [
                {
                    "text": "📊 График по дням",
                    "callback_data": "admin:tournament_daily_chart"
                }
            ],
            [
                {
                    "text": "🔄 Обновить",
                    "callback_data": "admin:tournament_date_stats"
                }
            ],
            [
                {
                    "text": "🔙 Назад",
                    "callback_data": "admin:tournament_stats"
                }
            ]
        ]
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
                for btn in keyboard
            ]
        )
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown", reply_markup=markup
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики по датам: {e}")
        await callback.answer("❌ Ошибка загрузки статистики", show_alert=True)


@router.callback_query(F.data == "admin:tournament_game_stats")
async def tournament_game_statistics(callback: CallbackQuery, state: FSMContext):
    """Статистика турниров по играм"""
    try:
        # Получаем статистику по играм
        popular_games = await TournamentRepository.get_popular_games()
        total_tournaments = await TournamentRepository.get_total_count()
        
        if not popular_games or total_tournaments == 0:
            text = """🎮 **Статистика по играм**

❌ **Нет данных**

Турниры с играми еще не созданы."""
        else:
            text = f"""🎮 **Статистика по играм**

📊 **Популярность игр:**
🏆 Всего турниров: **{total_tournaments}**

"""
            
            for i, (game_name, count) in enumerate(popular_games, 1):
                percentage = (count / total_tournaments) * 100
                
                # Эмодзи рейтинга
                if i == 1:
                    emoji = "🥇"
                elif i == 2:
                    emoji = "🥈"
                elif i == 3:
                    emoji = "🥉"
                else:
                    emoji = f"{i}️⃣"
                
                text += f"{emoji} **{game_name}**\n"
                text += f"   📊 Турниров: **{count}** ({percentage:.1f}%)\n\n"
            
            # Статистика форматов по играм
            format_by_game_stats = await TournamentRepository.get_format_by_game_statistics()
            
            if format_by_game_stats:
                text += "🏆 **Форматы по играм:**\n"
                format_names = {
                    'single_elimination': 'Одиночное исключение',
                    'double_elimination': 'Двойное исключение',
                    'round_robin': 'Круговая система',
                    'swiss': 'Швейцарская система'
                }
                
                for (game_name, format_type), count in format_by_game_stats.items():
                    format_name = format_names.get(format_type, format_type)
                    text += f"• {game_name} - {format_name}: **{count}**\n"
        
        keyboard = [
            [
                {
                    "text": "📊 Детали по играм",
                    "callback_data": "admin:game_details_stats"
                }
            ],
            [
                {
                    "text": "🔄 Обновить",
                    "callback_data": "admin:tournament_game_stats"
                }
            ],
            [
                {
                    "text": "🔙 Назад",
                    "callback_data": "admin:tournament_stats"
                }
            ]
        ]
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
                for btn in keyboard
            ]
        )
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown", reply_markup=markup
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики по играм: {e}")
        await callback.answer("❌ Ошибка загрузки статистики", show_alert=True)


@router.callback_query(F.data == "admin:export_tournament_stats")
async def export_tournament_statistics(callback: CallbackQuery, state: FSMContext):
    """Экспорт статистики турниров"""
    try:
        # Получаем всю статистику
        stats = {
            'total': await TournamentRepository.get_total_count(),
            'active': await TournamentRepository.get_active_count(),
            'completed': await TournamentRepository.get_completed_count(),
            'cancelled': await TournamentRepository.get_cancelled_count(),
            'avg_teams': await TournamentRepository.get_average_teams_per_tournament(),
            'popular_games': await TournamentRepository.get_popular_games(),
            'format_stats': await TournamentRepository.get_format_statistics(),
        }
        
        # Формируем текст для экспорта
        export_text = f"""📊 ЭКСПОРТ СТАТИСТИКИ ТУРНИРОВ
Дата генерации: {datetime.now().strftime('%d.%m.%Y %H:%M')}

=== ОСНОВНАЯ СТАТИСТИКА ===
Всего турниров: {stats['total']}
Активных: {stats['active']}
Завершенных: {stats['completed']}
Отмененных: {stats['cancelled']}
Среднее количество команд: {stats['avg_teams']:.1f}

=== ПОПУЛЯРНЫЕ ИГРЫ ==="""
        
        if stats['popular_games']:
            for game_name, count in stats['popular_games']:
                export_text += f"\n{game_name}: {count} турниров"
        
        export_text += "\n\n=== ФОРМАТЫ ТУРНИРОВ ==="
        if stats['format_stats']:
            format_names = {
                'single_elimination': 'Одиночное исключение',
                'double_elimination': 'Двойное исключение',
                'round_robin': 'Круговая система',
                'swiss': 'Швейцарская система'
            }
            
            for format_type, count in stats['format_stats'].items():
                format_name = format_names.get(format_type, format_type)
                export_text += f"\n{format_name}: {count}"
        
        # Отправляем как файл (имитация)
        text = f"""📋 **Экспорт статистики**

✅ **Данные подготовлены**

📊 Статистика включает:
• Общие показатели
• Данные по играм  
• Форматы турниров
• Временные метрики

📄 **Размер данных:** {len(export_text)} символов

*В реальной системе здесь был бы файл для скачивания*"""
        
        keyboard = [
            [
                {
                    "text": "📋 Показать текст",
                    "callback_data": "admin:show_export_text"
                }
            ],
            [
                {
                    "text": "🔙 Назад",
                    "callback_data": "admin:detailed_tournament_stats"
                }
            ]
        ]
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
                for btn in keyboard
            ]
        )
        
        # Сохраняем экспортированный текст в состояние для показа
        await state.update_data(export_text=export_text)
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown", reply_markup=markup
        )
        await callback.answer("✅ Данные подготовлены!")
        
    except Exception as e:
        logger.error(f"Ошибка экспорта статистики: {e}")
        await callback.answer("❌ Ошибка экспорта", show_alert=True)


@router.callback_query(F.data == "admin:show_export_text")
async def show_export_text(callback: CallbackQuery, state: FSMContext):
    """Показать экспортированный текст"""
    try:
        data = await state.get_data()
        export_text = data.get('export_text', 'Данные не найдены')
        
        # Обрезаем текст если слишком длинный
        if len(export_text) > 4000:
            export_text = export_text[:4000] + "\n\n... (текст обрезан)"
        
        text = f"""📋 **Экспортированная статистика**

```
{export_text}
```"""
        
        keyboard = [
            [
                {
                    "text": "🔙 Назад к экспорту",
                    "callback_data": "admin:export_tournament_stats"
                }
            ]
        ]
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
                for btn in keyboard
            ]
        )
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown", reply_markup=markup
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка показа экспортированного текста: {e}")
        await callback.answer("❌ Ошибка показа данных", show_alert=True)