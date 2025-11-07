"""
Обработчики для управления форматами турниров
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from utils.message_utils import safe_edit_message
from .keyboards import get_tournament_management_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "admin:manage_formats")
async def manage_tournament_formats(callback: CallbackQuery, state: FSMContext):
    """Управление форматами турниров"""
    await state.clear()
    
    text = """🏆 **Управление форматами турниров**

📋 Доступные форматы:

🏁 **Single Elimination**
▪️ Классическая система на выбывание
▪️ Одно поражение = исключение  
▪️ Быстрый формат

🔄 **Double Elimination**
▪️ Система с верхней и нижней сеткой
▪️ Два поражения = исключение
▪️ Более справедливый формат

⚡ **Round Robin**
▪️ Каждый с каждым
▪️ Играют все участники
▪️ Длительный, но справедливый

Выберите действие:"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="📊 Статистика использования",
                callback_data="admin:format_statistics"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Настройки форматов",
                callback_data="admin:format_settings"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Добавить кастомный формат",
                callback_data="admin:add_custom_format"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к турнирам",
                callback_data="admin:tournaments"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "admin:format_statistics")
async def show_format_statistics(callback: CallbackQuery, state: FSMContext):
    """Показ статистики использования форматов"""
    try:
        from database.repositories import TournamentRepository
        
        stats = await TournamentRepository.get_format_statistics()
        
        total_tournaments = sum(stats.values()) if stats else 0
        
        if total_tournaments == 0:
            text = """📊 **Статистика форматов турниров**

❌ Пока нет созданных турниров для анализа статистики."""
        else:
            text = f"""📊 **Статистика форматов турниров**

📈 Всего турниров: {total_tournaments}

"""
            for format_key, count in stats.items():
                format_names = {
                    'single': '🏁 Single Elimination',
                    'double': '🔄 Double Elimination',
                    'round_robin': '⚡ Round Robin'
                }
                
                format_name = format_names.get(format_key, format_key)
                percentage = round((count / total_tournaments * 100), 1)
                text += f"{format_name}: {count} ({percentage}%)\n"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔙 Назад к форматам",
                    callback_data="admin:manage_formats"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики форматов: {e}")
        await callback.answer("❌ Ошибка получения статистики")


@router.callback_query(F.data == "admin:format_settings")
async def show_format_settings(callback: CallbackQuery, state: FSMContext):
    """Настройки форматов"""
    text = """⚙️ **Настройки форматов турниров**

🔧 **Доступные настройки:**

🏁 **Single Elimination:**
▪️ Минимум участников: 2
▪️ Максимум участников: 128  
▪️ Случайная жеребьевка: ✅
▪️ Сидирование: ✅

🔄 **Double Elimination:**
▪️ Минимум участников: 3
▪️ Максимум участников: 64
▪️ Случайная жеребьевка: ✅
▪️ Сидирование: ✅

⚡ **Round Robin:**
▪️ Минимум участников: 3
▪️ Максимум участников: 16
▪️ Случайная жеребьевка: ❌
▪️ Сидирование: ❌

*Настройки оптимизированы для стабильной работы*"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔧 Изменить лимиты",
                callback_data="admin:edit_format_limits"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎲 Настройки жеребьевки",
                callback_data="admin:seeding_settings"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к форматам",
                callback_data="admin:manage_formats"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "admin:add_custom_format")
async def add_custom_format(callback: CallbackQuery, state: FSMContext):
    """Добавление кастомного формата"""
    text = """📝 **Добавление кастомного формата**

⚠️ **В разработке**

Функция добавления кастомных форматов турниров будет доступна в следующих версиях.

Пока доступны стандартные форматы:
- Single Elimination
- Double Elimination  
- Round Robin

Эти форматы покрывают большинство потребностей турниров."""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="📧 Запросить функцию",
                callback_data="admin:request_feature"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к форматам",
                callback_data="admin:manage_formats"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "admin:edit_format_limits")
async def edit_format_limits(callback: CallbackQuery, state: FSMContext):
    """Редактирование лимитов форматов"""
    text = """🔧 **Изменение лимитов участников**

⚠️ **Осторожно!** 

Изменение лимитов может повлиять на стабильность турниров:

🏁 **Single Elimination:** 2-128 участников
▪️ Оптимально: 8-64 участника
▪️ Потребление ресурсов: Низкое

🔄 **Double Elimination:** 3-64 участника  
▪️ Оптимально: 8-32 участника
▪️ Потребование ресурсов: Среднее

⚡ **Round Robin:** 3-16 участников
▪️ Оптимально: 4-8 участников
▪️ Потребление ресурсов: Высокое

*Рекомендуется сохранить текущие лимиты*"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="📊 Текущие лимиты",
                callback_data="admin:current_limits"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚠️ Изменить (экспертный режим)",
                callback_data="admin:expert_limits"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к настройкам",
                callback_data="admin:format_settings"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "admin:current_limits")
async def show_current_limits(callback: CallbackQuery, state: FSMContext):
    """Показ текущих лимитов"""
    text = """📊 **Текущие лимиты участников**

🏁 **Single Elimination:**
▪️ Минимум: 2 участника
▪️ Максимум: 128 участников
▪️ Статус: ✅ Активен

🔄 **Double Elimination:**
▪️ Минимум: 3 участника  
▪️ Максимум: 64 участника
▪️ Статус: ✅ Активен

⚡ **Round Robin:**
▪️ Минимум: 3 участника
▪️ Максимум: 16 участников
▪️ Статус: ✅ Активен

💡 **Рекомендации:**
- Single Elimination для больших турниров
- Double Elimination для соревновательных турниров
- Round Robin для малых групповых турниров"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад к лимитам",
                callback_data="admin:edit_format_limits"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()