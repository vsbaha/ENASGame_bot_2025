"""
Хендлеры для управления турнирами
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database.repositories import UserRepository, TournamentRepository
from utils.message_utils import safe_edit_message
from handlers.admin.states import AdminStates
from handlers.admin.keyboards import get_tournament_management_keyboard, get_tournament_settings_keyboard, get_tournament_action_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "admin:tournaments")
async def tournament_management_menu(callback: CallbackQuery, state: FSMContext):
    """Меню управления турнирами"""
    await state.clear()
    
    # Получаем статистику турниров
    try:
        total_tournaments = await TournamentRepository.get_total_count()
        active_tournaments = await TournamentRepository.get_active_count()
    except Exception as e:
        logger.error(f"Ошибка получения статистики турниров: {e}")
        total_tournaments = 0
        active_tournaments = 0
    
    text = f"""🏆 Управление турнирами

📊 Статистика:
📋 Всего турниров: {total_tournaments}
🏃 Активных: {active_tournaments}

Выберите действие:"""
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=get_tournament_management_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:tournament_settings")
async def tournament_settings_menu(callback: CallbackQuery, state: FSMContext):
    """Меню настроек турниров"""
    await state.clear()
    
    try:
        # Получаем статистику и список турниров
        total_tournaments = await TournamentRepository.get_total_count()
        active_tournaments = await TournamentRepository.get_active_count()
        completed_tournaments = total_tournaments - active_tournaments
        
        # Получаем список турниров
        tournaments = await TournamentRepository.get_all()
        
        text = f"""⚙️ **Настройки турниров**

📊 **Статистика:**
📋 Всего турниров: **{total_tournaments}**
🏃 Активных: **{active_tournaments}**
✅ Завершенных: **{completed_tournaments}**

"""
        
        if tournaments:
            text += "🏆 **Выберите турнир для управления:**"
        else:
            text += "❌ **Турниры не созданы**\n\nСоздайте турнир в главном меню турниров."
    
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=get_tournament_settings_keyboard(tournaments)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения данных турниров: {e}")
        await callback.answer("❌ Ошибка загрузки данных", show_alert=True)


@router.callback_query(F.data.startswith("admin:manage_tournament_"))
async def manage_specific_tournament(callback: CallbackQuery, state: FSMContext):
    """Управление конкретным турниром"""
    await state.clear()
    
    try:
        # Извлекаем ID турнира из callback_data
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем информацию о турнире
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Статус эмодзи
        status_emoji = {
            'registration': '📝',
            'in_progress': '🏃', 
            'completed': '✅',
            'cancelled': '❌',
            'paused': '⏸️'
        }.get(tournament.status, '❓')
        
        # Статус на русском
        status_text = {
            'registration': 'Регистрация',
            'in_progress': 'В процессе',
            'completed': 'Завершен',
            'cancelled': 'Отменен', 
            'paused': 'Приостановлен'
        }.get(tournament.status, 'Неизвестно')
        
        # Форматы турниров на русском
        format_names = {
            'single_elimination': 'Одиночная сетка на выбывание',
            'double_elimination': 'Двойная сетка на выбывание', 
            'round_robin': 'Круговая система',
            'group_stage_playoffs': 'Групповой этап + плейофф'
        }
        
        format_text = format_names.get(tournament.format, tournament.format)
        
        text = f"""🏆 **{tournament.name}**

📊 **Полная информация о турнире:**

**Основные данные:**
🎮 Игра: **{tournament.game.name if hasattr(tournament, 'game') and tournament.game else 'N/A'}**
🏆 Формат: **{format_text}**
📈 Статус: {status_emoji} **{status_text}**
👥 Максимум команд: **{tournament.max_teams}**
🌍 Регион: **{tournament.region.upper() if hasattr(tournament, 'region') else 'KG'}**

**Временные рамки:**
📅 Создан: **{tournament.created_at.strftime('%d.%m.%Y в %H:%M')}**
📝 Регистрация: **{tournament.registration_start.strftime('%d.%m.%Y %H:%M')} - {tournament.registration_end.strftime('%d.%m.%Y %H:%M')}**
🚀 Начало турнира: **{tournament.tournament_start.strftime('%d.%m.%Y в %H:%M')}**
⏰ Дедлайн правок: **{tournament.edit_deadline.strftime('%d.%m.%Y %H:%M')}**

**Дополнительно:**
📝 Описание: {tournament.description or '*Не указано*'}
📋 Правила: {tournament.rules_text[:100] + '...' if tournament.rules_text and len(tournament.rules_text) > 100 else tournament.rules_text or '*Не указаны*'}
📄 Файл правил: **{tournament.rules_file_name or 'Не загружен'}**
🔗 Challonge ID: **{tournament.challonge_id or 'Не создан'}**

**Выберите действие:**"""
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=get_tournament_action_keyboard(tournament_id, tournament.status)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения информации о турнире: {e}")
        await callback.answer("❌ Ошибка получения данных турнира", show_alert=True)


@router.callback_query(F.data.startswith("admin:start_tournament_"))
async def start_tournament(callback: CallbackQuery, state: FSMContext):
    """Запуск турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Обновляем статус турнира
        success = await TournamentRepository.update_status(tournament_id, 'in_progress')
        
        if success:
            await callback.answer("✅ Турнир запущен!", show_alert=True)
            # Возвращаемся к управлению турниром
            callback.data = f"admin:manage_tournament_{tournament_id}"
            await manage_specific_tournament(callback, state)
        else:
            await callback.answer("❌ Ошибка запуска турнира", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка запуска турнира: {e}")
        await callback.answer("❌ Ошибка запуска турнира", show_alert=True)


@router.callback_query(F.data.startswith("admin:pause_tournament_"))
async def pause_tournament(callback: CallbackQuery, state: FSMContext):
    """Приостановка турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Обновляем статус турнира
        success = await TournamentRepository.update_status(tournament_id, 'paused')
        
        if success:
            await callback.answer("⏸️ Турнир приостановлен!", show_alert=True)
            # Возвращаемся к управлению турниром
            callback.data = f"admin:manage_tournament_{tournament_id}"
            await manage_specific_tournament(callback, state)
        else:
            await callback.answer("❌ Ошибка приостановки турнира", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка приостановки турнира: {e}")
        await callback.answer("❌ Ошибка приостановки турнира", show_alert=True)


@router.callback_query(F.data.startswith("admin:resume_tournament_"))
async def resume_tournament(callback: CallbackQuery, state: FSMContext):
    """Продолжение турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Обновляем статус турнира
        success = await TournamentRepository.update_status(tournament_id, 'in_progress')
        
        if success:
            await callback.answer("▶️ Турнир продолжен!", show_alert=True)
            # Возвращаемся к управлению турниром
            callback.data = f"admin:manage_tournament_{tournament_id}"
            await manage_specific_tournament(callback, state)
        else:
            await callback.answer("❌ Ошибка продолжения турнира", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка продолжения турнира: {e}")
        await callback.answer("❌ Ошибка продолжения турнира", show_alert=True)


@router.callback_query(F.data.startswith("admin:confirm_delete_tournament_"))
async def confirm_delete_tournament(callback: CallbackQuery, state: FSMContext):
    """Подтверждение удаления турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем информацию о турнире
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        text = f"""🗑️ **Подтверждение удаления**

⚠️ **Вы действительно хотите удалить турнир?**

🏆 **Название:** {tournament.name}
📅 **Создан:** {tournament.created_at.strftime('%d.%m.%Y')}
👥 **Команд:** {tournament.max_teams}

**Это действие необратимо!**"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"admin:delete_tournament_confirmed_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"admin:manage_tournament_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка подтверждения удаления турнира: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:delete_tournament_confirmed_"))
async def delete_tournament_confirmed(callback: CallbackQuery, state: FSMContext):
    """Окончательное удаление турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Удаляем турнир
        success = await TournamentRepository.delete_tournament(tournament_id)
        
        if success:
            await callback.answer("✅ Турнир удален!", show_alert=True)
            # Возвращаемся к настройкам турниров
            callback.data = "admin:tournament_settings"
            await tournament_settings_menu(callback, state)
        else:
            await callback.answer("❌ Ошибка удаления турнира", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка удаления турнира: {e}")
        await callback.answer("❌ Ошибка удаления турнира", show_alert=True)


@router.callback_query(F.data.startswith("admin:edit_tournament_details_"))
async def edit_tournament_details_menu(callback: CallbackQuery, state: FSMContext):
    """Меню редактирования деталей турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем информацию о турнире
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Сохраняем ID турнира в состояние
        await state.update_data(editing_tournament_id=tournament_id)
        
        text = f"""📝 **Редактирование турнира**

🏆 **{tournament.name}**

**Что хотите изменить?**"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📝 Название",
                    callback_data=f"admin:edit_name_{tournament_id}"
                ),
                InlineKeyboardButton(
                    text="📄 Описание", 
                    callback_data=f"admin:edit_description_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎮 Игру",
                    callback_data=f"admin:edit_game_{tournament_id}"
                ),
                InlineKeyboardButton(
                    text="🏆 Формат",
                    callback_data=f"admin:edit_format_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Макс. команд",
                    callback_data=f"admin:edit_max_teams_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Даты",
                    callback_data=f"admin:edit_dates_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Правила",
                    callback_data=f"admin:edit_rules_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад к турниру",
                    callback_data=f"admin:manage_tournament_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка меню редактирования турнира: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:tournament_detailed_stats_"))
async def show_tournament_detailed_stats(callback: CallbackQuery, state: FSMContext):
    """Показ детальной статистики турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем информацию о турнире
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Получаем дополнительную статистику
        try:
            # Здесь можно добавить подсчет команд, матчей и т.д.
            registered_teams = 0  # await TeamRepository.count_by_tournament(tournament_id)
            completed_matches = 0  # await MatchRepository.count_completed_by_tournament(tournament_id)
            total_matches = 0  # await MatchRepository.count_total_by_tournament(tournament_id)
        except:
            registered_teams = 0
            completed_matches = 0 
            total_matches = 0
        
        # Статус эмодзи
        status_emoji = {
            'registration': '📝',
            'in_progress': '🏃', 
            'completed': '✅',
            'cancelled': '❌',
            'paused': '⏸️'
        }.get(tournament.status, '❓')
        
        # Формат на русском
        format_text = {
            'single_elimination': 'Одиночное исключение',
            'double_elimination': 'Двойное исключение', 
            'round_robin': 'Круговая система',
            'group_stage_playoffs': 'Групповой этап + плей-офф'
        }.get(tournament.format, tournament.format)
        
        text = f"""📊 **Детальная статистика турнира**

🏆 **{tournament.name}**

**📋 Основная информация:**
🎮 Игра: **{tournament.game.name if hasattr(tournament, 'game') and tournament.game else 'N/A'}**
🏆 Формат: **{format_text}**
{status_emoji} Статус: **{tournament.status.replace('_', ' ').title()}**

**👥 Участники:**
📝 Зарегистрировано команд: **{registered_teams}/{tournament.max_teams}**
📊 Заполненность: **{round((registered_teams/tournament.max_teams)*100, 1) if tournament.max_teams > 0 else 0}%**

**🏁 Матчи:**
✅ Завершено: **{completed_matches}**
📊 Всего: **{total_matches}**
📈 Прогресс: **{round((completed_matches/total_matches)*100, 1) if total_matches > 0 else 0}%**

**📅 Временные рамки:**
📝 Регистрация: **{tournament.registration_start.strftime('%d.%m.%Y %H:%M')} - {tournament.registration_end.strftime('%d.%m.%Y %H:%M')}**
🏁 Начало турнира: **{tournament.tournament_start.strftime('%d.%m.%Y %H:%M')}**
⏰ Дедлайн изменений: **{tournament.edit_deadline.strftime('%d.%m.%Y %H:%M')}**

**📝 Дополнительно:**
📋 Описание: {tournament.description or 'Не указано'}
📄 Правила: {'✅ Загружены' if hasattr(tournament, 'rules_file_id') and tournament.rules_file_id else ('📝 Текстовые' if tournament.rules_text else 'Не указаны')}
📅 Создан: **{tournament.created_at.strftime('%d.%m.%Y в %H:%M')}**"""

        if hasattr(tournament, 'challonge_id') and tournament.challonge_id:
            text += f"\n🔗 Challonge ID: **{tournament.challonge_id}**"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📊 Обновить данные",
                    callback_data=f"admin:tournament_detailed_stats_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад к турниру",
                    callback_data=f"admin:manage_tournament_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики турнира: {e}")
        await callback.answer("❌ Ошибка получения статистики", show_alert=True)


@router.callback_query(F.data.startswith("admin:edit_name_"))
async def edit_tournament_name_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование названия турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        await state.update_data(editing_tournament_id=tournament_id)
        
        text = f"""📝 **Редактирование названия турнира**

**Текущее название:** {tournament.name}

Введите новое название турнира:

▪️ Минимум 3 символа
▪️ Максимум 100 символов 
▪️ Должно быть уникальным"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔙 Отменить",
                    callback_data=f"admin:edit_tournament_details_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.editing_tournament_name)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала редактирования названия: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:edit_description_"))
async def edit_tournament_description_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование описания турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        await state.update_data(editing_tournament_id=tournament_id)
        
        text = f"""📄 **Редактирование описания турнира**

**Турнир:** {tournament.name}

**Текущее описание:** 
{tournament.description or 'Не указано'}

Введите новое описание турнира:

▪️ Максимум 1000 символов
▪️ Можно оставить пустым"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🗑️ Очистить описание",
                    callback_data=f"admin:clear_description_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Отменить",
                    callback_data=f"admin:edit_tournament_details_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.editing_tournament_description)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала редактирования описания: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:clear_description_"))
async def clear_tournament_description(callback: CallbackQuery, state: FSMContext):
    """Очистить описание турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        success = await TournamentRepository.update_field(tournament_id, 'description', '')
        
        if success:
            await callback.answer("✅ Описание очищено!", show_alert=True)
            callback.data = f"admin:edit_tournament_details_{tournament_id}"
            await edit_tournament_details_menu(callback, state)
        else:
            await callback.answer("❌ Ошибка очистки описания", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка очистки описания: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(AdminStates.editing_tournament_name))
async def process_tournament_name_edit(message: Message, state: FSMContext):
    """Обработка нового названия турнира"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение с новым названием.")
        return
    
    new_name = message.text.strip()
    
    # Валидация
    if len(new_name) < 3:
        await message.answer("❌ Название слишком короткое (минимум 3 символа).\n\nПопробуйте ещё раз:")
        return
    
    if len(new_name) > 100:
        await message.answer("❌ Название слишком длинное (максимум 100 символов).\n\nПопробуйте ещё раз:")
        return
    
    try:
        data = await state.get_data()
        tournament_id = data.get('editing_tournament_id')
        
        if not tournament_id:
            await message.answer("❌ Ошибка: ID турнира не найден.")
            await state.clear()
            return
        
        # Проверяем уникальность названия
        existing = await TournamentRepository.get_by_name(new_name)
        if existing and existing.id != tournament_id:
            await message.answer(f"❌ Турнир с названием '{new_name}' уже существует.\n\nВведите другое название:")
            return
        
        # Обновляем название
        success = await TournamentRepository.update_field(tournament_id, 'name', new_name)
        
        if success:
            await message.answer(f"✅ Название изменено на: **{new_name}**", parse_mode="Markdown")
            await state.clear()
            
            # Показываем меню редактирования
            text = f"""📝 **Название турнира обновлено**

Новое название: **{new_name}**

Что ещё хотите изменить?"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="🔙 К меню редактирования",
                        callback_data=f"admin:edit_tournament_details_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏆 К турниру",
                        callback_data=f"admin:manage_tournament_{tournament_id}"
                    )
                ]
            ]
            
            await message.answer(
                text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        else:
            await message.answer("❌ Ошибка обновления названия. Попробуйте позже.")
            
    except Exception as e:
        logger.error(f"Ошибка обновления названия турнира: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.message(StateFilter(AdminStates.editing_tournament_description))
async def process_tournament_description_edit(message: Message, state: FSMContext):
    """Обработка нового описания турнира"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение с новым описанием.")
        return
    
    new_description = message.text.strip()
    
    # Валидация
    if len(new_description) > 1000:
        await message.answer("❌ Описание слишком длинное (максимум 1000 символов).\n\nПопробуйте сократить:")
        return
    
    try:
        data = await state.get_data()
        tournament_id = data.get('editing_tournament_id')
        
        if not tournament_id:
            await message.answer("❌ Ошибка: ID турнира не найден.")
            await state.clear()
            return
        
        # Обновляем описание
        success = await TournamentRepository.update_field(tournament_id, 'description', new_description)
        
        if success:
            await message.answer("✅ Описание обновлено!")
            await state.clear()
            
            # Показываем меню редактирования  
            text = f"""📄 **Описание турнира обновлено**

Новое описание: 
{new_description}

Что ещё хотите изменить?"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="🔙 К меню редактирования",
                        callback_data=f"admin:edit_tournament_details_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏆 К турниру",
                        callback_data=f"admin:manage_tournament_{tournament_id}"
                    )
                ]
            ]
            
            await message.answer(
                text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        else:
            await message.answer("❌ Ошибка обновления описания. Попробуйте позже.")
            
    except Exception as e:
        logger.error(f"Ошибка обновления описания турнира: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data.startswith("admin:edit_max_teams_"))
async def edit_tournament_max_teams_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование максимального количества команд"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        await state.update_data(editing_tournament_id=tournament_id)
        
        text = f"""👥 **Редактирование количества команд**

**Турнир:** {tournament.name}

**Текущее количество:** {tournament.max_teams}

Введите новое максимальное количество команд:

▪️ Минимум: 2 команды
▪️ Максимум: 128 команд
▪️ Только целые числа"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔙 Отменить",
                    callback_data=f"admin:edit_tournament_details_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.editing_tournament_max_teams)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала редактирования количества команд: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(AdminStates.editing_tournament_max_teams))
async def process_tournament_max_teams_edit(message: Message, state: FSMContext):
    """Обработка нового количества команд"""
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите число от 2 до 128.")
        return
    
    new_max_teams = int(message.text.strip())
    
    # Валидация
    if new_max_teams < 2:
        await message.answer("❌ Минимальное количество команд: 2.\n\nПопробуйте ещё раз:")
        return
    
    if new_max_teams > 128:
        await message.answer("❌ Максимальное количество команд: 128.\n\nПопробуйте ещё раз:")
        return
    
    try:
        data = await state.get_data()
        tournament_id = data.get('editing_tournament_id')
        
        if not tournament_id:
            await message.answer("❌ Ошибка: ID турнира не найден.")
            await state.clear()
            return
        
        # Обновляем количество команд
        success = await TournamentRepository.update_field(tournament_id, 'max_teams', new_max_teams)
        
        if success:
            await message.answer(f"✅ Количество команд изменено на: **{new_max_teams}**", parse_mode="Markdown")
            await state.clear()
            
            # Показываем меню редактирования
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="🔙 К меню редактирования",
                        callback_data=f"admin:edit_tournament_details_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏆 К турниру",
                        callback_data=f"admin:manage_tournament_{tournament_id}"
                    )
                ]
            ]
            
            await message.answer(
                "👥 **Количество команд обновлено**\n\nЧто ещё хотите изменить?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        else:
            await message.answer("❌ Ошибка обновления количества команд. Попробуйте позже.")
            
    except Exception as e:
        logger.error(f"Ошибка обновления количества команд: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data.startswith("admin:edit_rules_"))
async def edit_tournament_rules_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование правил турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        tournament = await TournamentRepository.get_by_id(tournament_id)
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        await state.update_data(editing_tournament_id=tournament_id)
        
        text = f"""📋 **Редактирование правил турнира**

**Турнир:** {tournament.name}

**Текущие правила:**
{tournament.rules_text or 'Не указаны'}

Введите новые правила или загрузите файл регламента:

▪️ Максимум 2000 символов для текста
▪️ Файл: PDF, DOC, DOCX до 10 МБ"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🗑️ Очистить правила",
                    callback_data=f"admin:clear_rules_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Отменить",
                    callback_data=f"admin:edit_tournament_details_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.editing_tournament_rules)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала редактирования правил: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:clear_rules_"))
async def clear_tournament_rules(callback: CallbackQuery, state: FSMContext):
    """Очистить правила турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Очищаем текстовые правила
        success = await TournamentRepository.update_field(tournament_id, 'rules_text', '')
        
        if success:
            await callback.answer("✅ Правила очищены!", show_alert=True)
            callback.data = f"admin:edit_tournament_details_{tournament_id}"
            await edit_tournament_details_menu(callback, state)
        else:
            await callback.answer("❌ Ошибка очистки правил", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка очистки правил: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(AdminStates.editing_tournament_rules))
async def process_tournament_rules_edit(message: Message, state: FSMContext):
    """Обработка новых правил турнира"""
    try:
        data = await state.get_data()
        tournament_id = data.get('editing_tournament_id')
        
        if not tournament_id:
            await message.answer("❌ Ошибка: ID турнира не найден.")
            await state.clear()
            return
        
        if message.document:
            # Обработка файла
            file = message.document
            
            # Проверяем размер файла (10 МБ = 10 * 1024 * 1024 байт)
            if file.file_size > 10 * 1024 * 1024:
                await message.answer("❌ Файл слишком большой. Максимальный размер: 10 МБ.")
                return
            
            # Проверяем тип файла
            allowed_extensions = ['.pdf', '.doc', '.docx', '.txt']
            file_extension = None
            if file.file_name:
                file_extension = '.' + file.file_name.split('.')[-1].lower()
            
            if not file_extension or file_extension not in allowed_extensions:
                await message.answer("❌ Неподдерживаемый формат файла. Разрешены: PDF, DOC, DOCX, TXT.")
                return
            
            # Сохраняем файл ID
            success = await TournamentRepository.update_field(tournament_id, 'rules_file_id', file.file_id)
            
            if success:
                await message.answer("✅ Файл правил загружен!")
                await state.clear()
                
                keyboard = [
                    [
                        InlineKeyboardButton(
                            text="🔙 К меню редактирования",
                            callback_data=f"admin:edit_tournament_details_{tournament_id}"
                        )
                    ]
                ]
                
                await message.answer(
                    "📋 **Правила турнира обновлены**\n\nФайл регламента загружен.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
            else:
                await message.answer("❌ Ошибка сохранения файла. Попробуйте позже.")
                
        elif message.text:
            # Обработка текстовых правил
            new_rules = message.text.strip()
            
            if len(new_rules) > 2000:
                await message.answer("❌ Правила слишком длинные (максимум 2000 символов).\n\nПопробуйте сократить:")
                return
            
            # Обновляем правила
            success = await TournamentRepository.update_field(tournament_id, 'rules_text', new_rules)
            
            if success:
                await message.answer("✅ Правила обновлены!")
                await state.clear()
                
                keyboard = [
                    [
                        InlineKeyboardButton(
                            text="🔙 К меню редактирования",
                            callback_data=f"admin:edit_tournament_details_{tournament_id}"
                        )
                    ]
                ]
                
                await message.answer(
                    "📋 **Правила турнира обновлены**",
                    parse_mode="Markdown", 
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
            else:
                await message.answer("❌ Ошибка обновления правил. Попробуйте позже.")
        else:
            await message.answer("❌ Пожалуйста, отправьте текст правил или файл регламента.")
            
    except Exception as e:
        logger.error(f"Ошибка обновления правил турнира: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data == "admin:edit_tournament")


@router.callback_query(F.data == "admin:create_tournament")
async def start_tournament_creation(callback: CallbackQuery, state: FSMContext):
    """Начало создания турнира - запрос названия"""
    await state.clear()
    
    text = """➕ Создание турнира

📝 **Шаг 1 из 8: Название турнира**

Введите название турнира:

▪️ Минимум 3 символа
▪️ Максимум 100 символов
▪️ Избегайте специальных символов

**Пример:** Championship 2025"""
    
    # Создаем кнопку отмены
    keyboard = [[
        InlineKeyboardButton(
            text="❌ Отменить создание",
            callback_data="admin:cancel_tournament_creation"
        )
    ]]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_name)
    await callback.answer()


@router.callback_query(F.data == "admin:edit_tournament")
async def select_tournament_to_edit(callback: CallbackQuery, state: FSMContext):
    """Выбор турнира для редактирования"""
    await state.clear()
    
    try:
        # Получаем список всех турниров
        tournaments = await TournamentRepository.get_all()
        
        if not tournaments:
            text = """📋 **Турниры не найдены**
            
Сначала создайте турнир, чтобы его можно было редактировать."""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="➕ Создать турнир",
                        callback_data="admin:create_tournament"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад к настройкам",
                        callback_data="admin:tournament_settings"
                    )
                ]
            ]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            await callback.answer()
            return
        
        text = "📋 **Выберите турнир для редактирования:**\n\n"
        
        keyboard = []
        for tournament in tournaments[:10]:  # Показываем первые 10
            status_emoji = {
                'registration': '📝',
                'in_progress': '🏃',
                'completed': '✅',
                'cancelled': '❌'
            }.get(tournament.status, '❓')
            
            text += f"{status_emoji} **{tournament.name}**\n"
            text += f"   📅 {tournament.created_at.strftime('%d.%m.%Y')}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} {tournament.name}",
                    callback_data=f"admin:edit_tournament_{tournament.id}"
                )
            ])
        
        if len(tournaments) > 10:
            text += f"... и ещё {len(tournaments) - 10} турниров"
        
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 Назад к настройкам",
                callback_data="admin:tournament_settings"
            )
        ])
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения списка турниров: {e}")
        await callback.answer("❌ Ошибка получения списка турниров", show_alert=True)


@router.callback_query(F.data == "admin:delete_tournament")
async def select_tournament_to_delete(callback: CallbackQuery, state: FSMContext):
    """Выбор турнира для удаления"""
    await state.clear()
    
    try:
        # Получаем список всех турниров
        tournaments = await TournamentRepository.get_all()
        
        if not tournaments:
            text = """🗑️ **Турниры не найдены**
            
Нет турниров для удаления."""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="🔙 Назад к настройкам",
                        callback_data="admin:tournament_settings"
                    )
                ]
            ]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            await callback.answer()
            return
        
        text = "🗑️ **Выберите турнир для удаления:**\n\n"
        text += "⚠️ **Внимание!** Удаление необратимо.\n\n"
        
        keyboard = []
        for tournament in tournaments[:10]:  # Показываем первые 10
            status_emoji = {
                'registration': '📝',
                'in_progress': '🏃',
                'completed': '✅',
                'cancelled': '❌'
            }.get(tournament.status, '❓')
            
            text += f"{status_emoji} **{tournament.name}**\n"
            text += f"   📅 {tournament.created_at.strftime('%d.%m.%Y')}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🗑️ {tournament.name}",
                    callback_data=f"admin:confirm_delete_tournament_{tournament.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 Назад к настройкам",
                callback_data="admin:tournament_settings"
            )
        ])
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения списка турниров: {e}")
        await callback.answer("❌ Ошибка получения списка турниров", show_alert=True)


@router.callback_query(F.data == "admin:list_tournaments")
async def list_all_tournaments(callback: CallbackQuery, state: FSMContext):
    """Показать список всех турниров"""
    await state.clear()
    
    try:
        # Получаем список всех турниров
        tournaments = await TournamentRepository.get_all()
        
        if not tournaments:
            text = """📋 **Список турниров пуст**
            
Пока не создано ни одного турнира."""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="➕ Создать первый турнир",
                        callback_data="admin:create_tournament"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад к настройкам",
                        callback_data="admin:tournament_settings"
                    )
                ]
            ]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            await callback.answer()
            return
        
        text = f"📋 **Список турниров** ({len(tournaments)} шт.)\n\n"
        
        for i, tournament in enumerate(tournaments[:15], 1):  # Показываем первые 15
            status_emoji = {
                'registration': '📝',
                'in_progress': '🏃',
                'completed': '✅',
                'cancelled': '❌'
            }.get(tournament.status, '❓')
            
            text += f"{i}. {status_emoji} **{tournament.name}**\n"
            text += f"   🎮 Игра: {tournament.game.name if hasattr(tournament, 'game') else 'N/A'}\n"
            text += f"   📅 Создан: {tournament.created_at.strftime('%d.%m.%Y')}\n"
            text += f"   👥 Команд: {tournament.max_teams}\n\n"
        
        if len(tournaments) > 15:
            text += f"... и ещё {len(tournaments) - 15} турниров\n\n"
        
        text += "Для редактирования используйте кнопку выше."
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📝 Редактировать турнир",
                    callback_data="admin:edit_tournament"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад к настройкам",
                    callback_data="admin:tournament_settings"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения списка турниров: {e}")
        await callback.answer("❌ Ошибка получения списка турниров", show_alert=True)


@router.callback_query(F.data == "admin:cancel_tournament_creation")
async def cancel_tournament_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания турнира"""
    await state.clear()
    
    text = """❌ Создание турнира отменено

Возвращаемся в меню управления турнирами."""
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=get_tournament_management_keyboard()
    )
    await callback.answer()


def validate_tournament_name(name: str) -> tuple[bool, str]:
    """Валидация названия турнира"""
    if not name or not name.strip():
        return False, "❌ Название не может быть пустым"
    
    name = name.strip()
    
    if len(name) < 3:
        return False, "❌ Название слишком короткое (минимум 3 символа)"
    
    if len(name) > 100:
        return False, "❌ Название слишком длинное (максимум 100 символов)"
    
    # Проверяем на запрещенные символы
    forbidden_chars = ['<', '>', '&', '"', "'", '`']
    for char in forbidden_chars:
        if char in name:
            return False, f"❌ Символ '{char}' запрещен в названии"
    
    return True, ""


@router.message(StateFilter(AdminStates.creating_tournament_name))
async def process_tournament_name(message: Message, state: FSMContext):
    """Обработка ввода названия турнира"""
    if not message.text:
        await message.answer(
            "❌ Пожалуйста, отправьте текстовое сообщение с названием турнира.",
            parse_mode="Markdown"
        )
        return
    
    tournament_name = message.text.strip()
    
    # Валидация названия
    is_valid, error_message = validate_tournament_name(tournament_name)
    
    if not is_valid:
        await message.answer(
            f"{error_message}\n\nПопробуйте ещё раз:",
            parse_mode="Markdown"
        )
        return
    
    # Сохраняем название в состояние
    await state.update_data(tournament_name=tournament_name)
    
    # Переходим к следующему шагу - ввод описания
    text = f"""✅ **Название принято:** {tournament_name}

📝 **Шаг 2 из 8: Описание турнира**

Введите описание турнира:

▪️ Максимум 1000 символов
▪️ Опишите цели, правила, призы
▪️ Можете добавить эмодзи

**Пример:** Ежегодный турнир для начинающих игроков 🏆"""
    
    # Создаем кнопки навигации
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад к названию", 
                callback_data="admin:edit_tournament_name"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить создание",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await message.answer(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_description)


@router.callback_query(F.data == "admin:edit_tournament_name")
async def edit_tournament_name(callback: CallbackQuery, state: FSMContext):
    """Возврат к редактированию названия турнира"""
    text = """📝 **Шаг 1 из 8: Название турнира**

Введите название турнира:

▪️ Минимум 3 символа
▪️ Максимум 100 символов
▪️ Избегайте специальных символов

**Пример:** Championship 2025"""
    
    # Создаем кнопку отмены
    keyboard = [[
        InlineKeyboardButton(
            text="❌ Отменить создание",
            callback_data="admin:cancel_tournament_creation"
        )
    ]]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_name)
    await callback.answer()


def validate_tournament_description(description: str) -> tuple[bool, str]:
    """Валидация описания турнира"""
    if not description or not description.strip():
        return False, "❌ Описание не может быть пустым"
    
    description = description.strip()
    
    if len(description) > 1000:
        return False, "❌ Описание слишком длинное (максимум 1000 символов)"
    
    return True, ""


@router.message(StateFilter(AdminStates.creating_tournament_description))
async def process_tournament_description(message: Message, state: FSMContext):
    """Обработка ввода описания турнира"""
    if not message.text:
        await message.answer(
            "❌ Пожалуйста, отправьте текстовое сообщение с описанием турнира.",
            parse_mode="Markdown"
        )
        return
    
    tournament_description = message.text.strip()
    
    # Валидация описания
    is_valid, error_message = validate_tournament_description(tournament_description)
    
    if not is_valid:
        await message.answer(
            f"{error_message}\n\nПопробуйте ещё раз:",
            parse_mode="Markdown"
        )
        return
    
    # Сохраняем описание в состояние
    await state.update_data(tournament_description=tournament_description)
    
    # Получаем данные для показа прогресса
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    
    # Переходим к следующему шагу - выбор игры
    # Сначала получим список доступных игр
    try:
        from database.repositories import GameRepository
        games = await GameRepository.get_all_active()
        
        if not games:
            await message.answer(
                "❌ В системе нет доступных игр. Обратитесь к администратору.",
                parse_mode="Markdown"
            )
            return
        
        text = f"""✅ **Описание принято**

📝 **Шаг 3 из 8: Выбор игры**

**Турнир:** {tournament_name}
**Описание:** {tournament_description[:100]}{"..." if len(tournament_description) > 100 else ""}

🎮 Выберите игру для турнира:"""
        
        # Создаем клавиатуру с играми
        keyboard = []
        for game in games:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🎮 {game.name}",
                    callback_data=f"admin:select_game_{game.id}"
                )
            ])
        
        # Добавляем навигационные кнопки
        keyboard.extend([
            [
                InlineKeyboardButton(
                    text="🔙 Назад к описанию", 
                    callback_data="admin:edit_tournament_description"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить создание",
                    callback_data="admin:cancel_tournament_creation"
                )
            ]
        ])
        
        await message.answer(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.creating_tournament_game)
        
    except Exception as e:
        logger.error(f"Ошибка получения списка игр: {e}")
        await message.answer(
            "❌ Ошибка при получении списка игр. Попробуйте позже.",
            parse_mode="Markdown"
        )


@router.callback_query(F.data == "admin:edit_tournament_description")
async def edit_tournament_description(callback: CallbackQuery, state: FSMContext):
    """Возврат к редактированию описания турнира"""
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    
    text = f"""✅ **Название:** {tournament_name}

📝 **Шаг 2 из 8: Описание турнира**

Введите описание турнира:

▪️ Максимум 1000 символов
▪️ Опишите цели, правила, призы
▪️ Можете добавить эмодзи

**Пример:** Ежегодный турнир для начинающих игроков 🏆"""
    
    # Создаем кнопки навигации
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад к названию", 
                callback_data="admin:edit_tournament_name"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить создание",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_description)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:select_game_"))
async def process_game_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора игры для турнира"""
    game_id = callback.data.split("_")[-1]  # admin:select_game_123 -> 123
    
    try:
        from database.repositories import GameRepository
        game = await GameRepository.get_by_id(int(game_id))
        
        if not game:
            await callback.answer("❌ Игра не найдена")
            return
        
        # Сохраняем игру в состояние
        await state.update_data(tournament_game_id=game.id, tournament_game_name=game.name)
        
        # Получаем данные для показа прогресса
        data = await state.get_data()
        tournament_name = data.get('tournament_name', '')
        tournament_description = data.get('tournament_description', '')
        
        # Переходим к следующему шагу - выбор формата
        text = f"""✅ **Игра выбрана:** {game.name}

📝 **Шаг 4 из 8: Формат турнира**

**Турнир:** {tournament_name}
**Игра:** {game.name}

🏆 Выберите формат турнира:"""
        
        # Создаем клавиатуру с форматами
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🏁 Single Elimination",
                    callback_data="admin:select_format_single"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Double Elimination", 
                    callback_data="admin:select_format_double"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚡ Round Robin",
                    callback_data="admin:select_format_round_robin"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад к выбору игры",
                    callback_data="admin:edit_tournament_game"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить создание",
                    callback_data="admin:cancel_tournament_creation"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.creating_tournament_format)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при выборе игры: {e}")
        await callback.answer("❌ Ошибка при выборе игры")


@router.callback_query(F.data == "admin:edit_tournament_game")  
async def edit_tournament_game(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору игры"""
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    tournament_description = data.get('tournament_description', '')
    
    try:
        from database.repositories import GameRepository
        games = await GameRepository.get_all_active()
        
        text = f"""✅ **Описание принято**

📝 **Шаг 3 из 8: Выбор игры**

**Турнир:** {tournament_name}
**Описание:** {tournament_description[:100]}{"..." if len(tournament_description) > 100 else ""}

🎮 Выберите игру для турнира:"""
        
        # Создаем клавиатуру с играми
        keyboard = []
        for game in games:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🎮 {game.name}",
                    callback_data=f"admin:select_game_{game.id}"
                )
            ])
        
        # Добавляем навигационные кнопки
        keyboard.extend([
            [
                InlineKeyboardButton(
                    text="🔙 Назад к описанию", 
                    callback_data="admin:edit_tournament_description"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить создание",
                    callback_data="admin:cancel_tournament_creation"
                )
            ]
        ])
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.creating_tournament_game)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка получения списка игр: {e}")
        await callback.answer("❌ Ошибка при получении списка игр")


@router.callback_query(F.data.startswith("admin:select_format_"))
async def process_format_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора формата турнира"""
    format_type = callback.data.split("_")[-1]  # admin:select_format_single -> single
    
    format_names = {
        "single": "Single Elimination",
        "double": "Double Elimination", 
        "round": "Round Robin"  # from round_robin
    }
    
    if format_type == "robin":  # для round_robin
        format_type = "round_robin"
        format_display = "Round Robin"
    else:
        format_display = format_names.get(format_type, format_type)
    
    # Сохраняем формат в состояние
    await state.update_data(tournament_format=format_type, tournament_format_display=format_display)
    
    # Получаем данные для показа прогресса
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    tournament_game_name = data.get('tournament_game_name', '')
    
    # Переходим к следующему шагу - ввод количества команд
    text = f"""✅ **Формат выбран:** {format_display}

📝 **Шаг 5 из 8: Количество команд**

**Турнир:** {tournament_name}
**Игра:** {tournament_game_name}
**Формат:** {format_display}

👥 Введите максимальное количество команд:

▪️ Минимум: 2 команды
▪️ Максимум: 128 команд
▪️ Только числа

**Пример:** 16"""
    
    # Создаем кнопки навигации
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад к формату",
                callback_data="admin:edit_tournament_format"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить создание",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_max_teams)
    await callback.answer()


@router.callback_query(F.data == "admin:edit_tournament_format")
async def edit_tournament_format(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору формата"""
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    tournament_game_name = data.get('tournament_game_name', '')
    
    text = f"""📝 **Шаг 4 из 8: Формат турнира**

**Турнир:** {tournament_name}
**Игра:** {tournament_game_name}

🏆 Выберите формат турнира:"""
    
    # Создаем клавиатуру с форматами
    keyboard = [
        [
            InlineKeyboardButton(
                text="🏁 Single Elimination",
                callback_data="admin:select_format_single"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Double Elimination", 
                callback_data="admin:select_format_double"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚡ Round Robin",
                callback_data="admin:select_format_round_robin"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к выбору игры",
                callback_data="admin:edit_tournament_game"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить создание",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_format)
    await callback.answer()


def validate_team_count(count_str: str) -> tuple[bool, str, int]:
    """Валидация количества команд"""
    try:
        count = int(count_str.strip())
        
        if count < 2:
            return False, "❌ Минимальное количество команд: 2", 0
        
        if count > 128:
            return False, "❌ Максимальное количество команд: 128", 0
        
        return True, "", count
    except ValueError:
        return False, "❌ Введите корректное число", 0


@router.message(StateFilter(AdminStates.creating_tournament_max_teams))
async def process_tournament_max_teams(message: Message, state: FSMContext):
    """Обработка ввода максимального количества команд"""
    if not message.text:
        await message.answer(
            "❌ Пожалуйста, отправьте число команд.",
            parse_mode="Markdown"
        )
        return
    
    # Валидация количества команд
    is_valid, error_message, team_count = validate_team_count(message.text)
    
    if not is_valid:
        await message.answer(
            f"{error_message}\n\nПопробуйте ещё раз:",
            parse_mode="Markdown"
        )
        return
    
    # Сохраняем количество команд в состояние
    await state.update_data(tournament_max_teams=team_count)
    
    # Получаем данные для показа прогресса
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    tournament_game_name = data.get('tournament_game_name', '')
    tournament_format_display = data.get('tournament_format_display', '')
    
    # Переходим к следующему шагу - дата начала регистрации
    text = f"""✅ **Количество команд:** {team_count}

📝 **Шаг 6 из 8: Даты турнира**

**Турнир:** {tournament_name}
**Игра:** {tournament_game_name}
**Формат:** {tournament_format_display}
**Команд:** {team_count}

📅 Введите дату начала регистрации:

▪️ Формат: ДД.ММ.ГГГГ ЧЧ:ММ
▪️ Пример: 01.12.2024 10:00
▪️ Или: завтра 15:00"""
    
    # Создаем кнопки навигации
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад к количеству команд",
                callback_data="admin:edit_tournament_max_teams"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить создание",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await message.answer(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_registration_start)


@router.callback_query(F.data == "admin:edit_tournament_max_teams")
async def edit_tournament_max_teams(callback: CallbackQuery, state: FSMContext):
    """Возврат к вводу количества команд"""
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    tournament_game_name = data.get('tournament_game_name', '')
    tournament_format_display = data.get('tournament_format_display', '')
    
    text = f"""📝 **Шаг 5 из 8: Количество команд**

**Турнир:** {tournament_name}
**Игра:** {tournament_game_name}
**Формат:** {tournament_format_display}

👥 Введите максимальное количество команд:

▪️ Минимум: 2 команды
▪️ Максимум: 128 команд
▪️ Только числа

**Пример:** 16"""
    
    # Создаем кнопки навигации
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад к формату",
                callback_data="admin:edit_tournament_format"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить создание",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_max_teams)
    await callback.answer()