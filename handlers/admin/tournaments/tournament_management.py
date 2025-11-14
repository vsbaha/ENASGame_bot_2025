"""
Основное управление турнирами
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database.repositories import TournamentRepository
from utils.message_utils import safe_edit_message
from utils.datetime_utils import format_datetime_for_user
from ..keyboards import get_tournament_management_keyboard, get_tournament_settings_keyboard, get_tournament_action_keyboard

router = Router()
logger = logging.getLogger(__name__)


def escape_html(text):
    """Экранирование специальных HTML символов"""
    if not text:
        return text
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


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


async def show_tournament_management_info(callback: CallbackQuery, tournament):
    """Показать информацию о турнире с кнопками управления (helper функция)"""
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
    
    game_name = tournament.game.name if hasattr(tournament, 'game') and tournament.game else 'N/A'
    description = tournament.description or 'Не указано'
    
    # Информация о файлах
    files_info = []
    if tournament.rules_file_id:
        files_info.append(f"📄 Правила: <b>{escape_html(tournament.rules_file_name or 'Загружены')}</b>")
    if tournament.logo_file_id:
        files_info.append("🖼️ Логотип: <b>Загружен</b>")
    
    files_text = "\n".join(files_info) if files_info else "❌ Файлы не загружены"
    
    text = f"""🏆 <b>{escape_html(tournament.name)}</b>

📊 <b>Подробная информация:</b>
🎮 Игра: <b>{escape_html(game_name)}</b>
🏆 Формат: <b>{escape_html(tournament.format)}</b>
📈 Статус: {status_emoji} <b>{status_text}</b>
👥 Максимум команд: <b>{tournament.max_teams}</b>
📅 Создан: <b>{format_datetime_for_user(tournament.created_at, 'Asia/Bishkek', '%d.%m.%Y в %H:%M')}</b>

📅 <b>Даты (GMT+6):</b>
📋 Регистрация: <b>{format_datetime_for_user(tournament.registration_start, 'Asia/Bishkek')}</b> - <b>{format_datetime_for_user(tournament.registration_end, 'Asia/Bishkek')}</b>
🏁 Начало турнира: <b>{format_datetime_for_user(tournament.tournament_start, 'Asia/Bishkek')}</b>

📝 <b>Описание:</b> {escape_html(description)}

📎 <b>Файлы:</b>
{files_text}

<b>Выберите действие:</b>"""
    
    # Отправляем логотип если есть
    if tournament.logo_file_id:
        try:
            await callback.message.answer_photo(
                photo=tournament.logo_file_id,
                caption=text,
                reply_markup=get_tournament_action_keyboard(tournament.id, tournament.status),
                parse_mode="HTML"
            )
            # Удаляем старое сообщение
            await callback.message.delete()
        except Exception as e:
            logger.error(f"Ошибка отправки логотипа: {e}")
            # Если не удалось отправить с логотипом, отправляем текстом
            await safe_edit_message(
                callback.message, text, parse_mode="HTML",
                reply_markup=get_tournament_action_keyboard(tournament.id, tournament.status)
            )
    else:
        await safe_edit_message(
            callback.message, text, parse_mode="HTML",
            reply_markup=get_tournament_action_keyboard(tournament.id, tournament.status)
        )
    
    # Отправляем файл правил если есть
    if tournament.rules_file_id:
        try:
            await callback.message.answer_document(
                document=tournament.rules_file_id,
                caption=f"📄 <b>Правила турнира:</b> {escape_html(tournament.rules_file_name or 'Правила.pdf')}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки файла правил: {e}")


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
        
        await show_tournament_management_info(callback, tournament)
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
            # Возвращаемся к управлению турниром - показываем обновленную информацию
            tournament = await TournamentRepository.get_by_id(tournament_id)
            if tournament:
                await show_tournament_management_info(callback, tournament)
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
            # Возвращаемся к управлению турниром - показываем обновленную информацию
            tournament = await TournamentRepository.get_by_id(tournament_id)
            if tournament:
                await show_tournament_management_info(callback, tournament)
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
            # Возвращаемся к управлению турниром - показываем обновленную информацию
            tournament = await TournamentRepository.get_by_id(tournament_id)
            if tournament:
                await show_tournament_management_info(callback, tournament)
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
📅 **Создан:** {format_datetime_for_user(tournament.created_at, 'Asia/Bishkek', '%d.%m.%Y')}
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
        
        # Удаляем предыдущее сообщение и отправляем новое
        try:
            await callback.message.delete()
        except:
            pass
        
        await callback.message.answer(
            text, parse_mode="Markdown",
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
            
            # Получаем обновленный список турниров
            await state.clear()
            
            total_tournaments = await TournamentRepository.get_total_count()
            active_tournaments = await TournamentRepository.get_active_count()
            completed_tournaments = total_tournaments - active_tournaments
            
            tournaments = await TournamentRepository.get_all()
            
            text = f"""⚙️ **Настройки турниров**

📊 **Статистика:**
📋 Всего турниров: **{total_tournaments}**
🏃 Активных: **{active_tournaments}**
✅ Завершенных: **{completed_tournaments}**

"""
            
            if tournaments:
                text += "**Список турниров:**\n\n"
                for tournament in tournaments[:10]:
                    status_emoji = "🟢" if tournament.status == "registration" else "🔴"
                    text += f"{status_emoji} **{tournament.name}** (ID: {tournament.id})\n"
                
                if len(tournaments) > 10:
                    text += f"\n_...и еще {len(tournaments) - 10} турниров_"
            else:
                text += "📭 **Турниров пока нет**"
            
            # Удаляем предыдущее сообщение и отправляем новое
            try:
                await callback.message.delete()
            except:
                pass
            
            await callback.message.answer(
                text, parse_mode="Markdown",
                reply_markup=get_tournament_settings_keyboard(tournaments)
            )
        else:
            await callback.answer("❌ Ошибка удаления турнира", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка удаления турнира: {e}")
        await callback.answer("❌ Ошибка удаления турнира", show_alert=True)


@router.callback_query(F.data.startswith("admin:tournament_detailed_stats_"))
async def show_tournament_detailed_stats(callback: CallbackQuery, state: FSMContext):
    """Показать детальную статистику турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем информацию о турнире
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Получаем статистику (пока заглушка)
        text = f"""📊 **Детальная статистика**

🏆 **{tournament.name}**

📈 **Основные метрики:**
👥 Зарегистрировано команд: 0 / {tournament.max_teams}
🎮 Проведено матчей: 0
⏱️ Длительность турнира: -

📊 **Активность:**
👀 Просмотров страницы: -
📱 Уникальных участников: -
💬 Сообщений в чате: -

🏅 **Результаты:**
🥇 Победитель: Не определен
🥈 Финалист: Не определен
🥉 3-е место: Не определен

*Статистика будет обновляться по мере развития турнира*"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔄 Обновить статистику",
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
        
        # Удаляем предыдущее сообщение и отправляем новое
        try:
            await callback.message.delete()
        except:
            pass
        
        await callback.message.answer(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка показа статистики турнира: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


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
                    callback_data=f"admin:edit_tournament_game_{tournament_id}"
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
                    text="🖼️ Логотип",
                    callback_data=f"admin:edit_logo_{tournament_id}"
                ),
                InlineKeyboardButton(
                    text="📋 Правила",
                    callback_data=f"admin:edit_rules_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Обязательные каналы",
                    callback_data=f"admin:edit_required_channels_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад к турниру",
                    callback_data=f"admin:manage_tournament_{tournament_id}"
                )
            ]
        ]
        
        # Удаляем предыдущее сообщение и отправляем новое
        try:
            await callback.message.delete()
        except:
            pass
        
        await callback.message.answer(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка меню редактирования турнира: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:edit_rules_"))
async def edit_tournament_rules_menu(callback: CallbackQuery, state: FSMContext):
    """Меню управления правилами турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем информацию о турнире
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Проверяем наличие файла правил
        rules_info = await TournamentRepository.get_rules_file_info(tournament_id)
        
        text = f"""📋 **Управление правилами турнира**

🏆 **{tournament.name}**

"""
        
        keyboard = []
        
        if rules_info:
            file_id, file_name = rules_info
            text += f"""✅ **Файл правил загружен**
📎 **Название:** {file_name}

**Доступные действия:**"""
            
            keyboard.extend([
                [
                    InlineKeyboardButton(
                        text="👁️ Просмотреть файл",
                        callback_data=f"admin:view_rules_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Заменить файл",
                        callback_data=f"admin:upload_rules_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑️ Удалить файл",
                        callback_data=f"admin:delete_rules_{tournament_id}"
                    )
                ]
            ])
        else:
            text += """❌ **Файл правил не загружен**

Вы можете загрузить файл с правилами турнира в формате PDF, DOC или DOCX."""
            
            keyboard.append([
                InlineKeyboardButton(
                    text="📎 Загрузить файл правил",
                    callback_data=f"admin:upload_rules_{tournament_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 Назад к редактированию",
                callback_data=f"admin:edit_tournament_details_{tournament_id}"
            )
        ])
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка меню правил турнира: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)