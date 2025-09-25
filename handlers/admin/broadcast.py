"""
Хендлеры для рассылки сообщений
"""
import logging
import asyncio
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database.repositories import UserRepository, TeamRepository, TournamentRepository
from utils.localization import _
from utils.message_utils import safe_edit_message
from .states import AdminStates
from .keyboards import get_broadcast_keyboard, get_confirmation_keyboard, get_broadcast_cancel_keyboard
from .attachment_keyboards import get_attachment_keyboard, get_attachment_options_keyboard, get_attachment_confirm_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "admin:broadcast")
async def broadcast_menu(callback: CallbackQuery, state: FSMContext):
    """Меню рассылки"""
    await state.clear()

    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    language = user.language if user else "ru"
    
    text = _("""
📢 Рассылка сообщений

⚠️ Внимание! Рассылка отправляет сообщения всем выбранным пользователям. Используйте с осторожностью.

Выберите целевую аудиторию:
""", language)
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_broadcast_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin:broadcast_all")
async def start_broadcast_all(callback: CallbackQuery, state: FSMContext):
    """Начало рассылки всем пользователям"""
    
    total_users = await UserRepository.get_total_count()
    active_users = await UserRepository.get_active_count()
    
    text = _("""
📢 Рассылка всем пользователям

🎯 Целевая аудитория:
👥 Всего пользователей: {total}
✅ Активных: {active}

📝 Введите текст сообщения для рассылки:

⚠️ *Сообщение будет отправлено всем пользователям!*
""", "ru").format(total=total_users, active=active_users)
    
    await safe_edit_message(
        callback.message, text, 
        reply_markup=get_broadcast_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.creating_broadcast_message)
    await state.update_data(broadcast_type="all")
    await callback.answer()

@router.callback_query(F.data == "admin:broadcast_tournament_users")
async def start_broadcast_tournament_users(callback: CallbackQuery, state: FSMContext):
    """Начало рассылки участникам турниров"""
    
    tournament_users = await TeamRepository.get_tournament_participants_count()
    
    text = _("""
📢 Рассылка участникам турниров

🎯 Целевая аудитория:
🏆 Участники турниров: {count}

📝 Введите текст сообщения для рассылки:

*Сообщение получат пользователи, которые участвуют в турнирах*
""", "ru").format(count=tournament_users)
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_broadcast_cancel_keyboard(), 
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.creating_broadcast_message)
    await state.update_data(broadcast_type="tournament_users")
    await callback.answer()

@router.callback_query(F.data == "admin:broadcast_team_captains")
async def start_broadcast_team_captains(callback: CallbackQuery, state: FSMContext):
    """Начало рассылки капитанам команд"""
    
    captains_count = await TeamRepository.get_captains_count()
    
    text = _("""
📢 Рассылка капитанам команд

🎯 Целевая аудитория:
👑 Капитаны команд: {count}

📝 Введите текст сообщения для рассылки:

*Сообщение получат только капитаны команд*
""", "ru").format(count=captains_count)
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_broadcast_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.creating_broadcast_message)
    await state.update_data(broadcast_type="team_captains")
    await callback.answer()

@router.message(StateFilter(AdminStates.creating_broadcast_message))
async def process_broadcast_message(message: Message, state: FSMContext):
    """Обработка текста рассылки"""
    if not message.text:
        await message.answer(_(
            "❌ Пожалуйста, отправьте текстовое сообщение для рассылки.", "ru"
        ), parse_mode="Markdown")
        return
    
    broadcast_text = message.text.strip()
    
    if len(broadcast_text) > 4000:
        await message.answer(_(
            "❌ Сообщение слишком длинное (максимум 4000 символов). Попробуйте сократить:", "ru"
        ), parse_mode="Markdown")
        return
    
    await state.update_data(broadcast_message=broadcast_text)
    
    # Предлагаем добавить вложение
    text = _("""
📝 Текст рассылки сохранен!

Хотите добавить вложение к рассылке?

📎 Поддерживаются: фото, видео, документы, аудио
""", "ru")
    
    await message.answer(
        text,
        reply_markup=get_attachment_keyboard(),
        parse_mode="Markdown"
    )
    
    await state.set_state(AdminStates.broadcast_adding_attachment)

# Обработчики вложений
@router.callback_query(F.data == "admin:add_attachment", StateFilter(AdminStates.broadcast_adding_attachment))
async def add_attachment(callback: CallbackQuery, state: FSMContext):
    """Добавление вложения"""
    text = _("""
📎 Выберите тип вложения

Поддерживаемые форматы:
🖼️ Фото: JPG, PNG, GIF
📄 Документы: PDF, DOC, TXT и др.
🎥 Видео: MP4, AVI, MOV
🎵 Аудио: MP3, WAV, OGG
""", "ru")
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_attachment_options_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin:skip_attachment", StateFilter(AdminStates.broadcast_adding_attachment))
async def skip_attachment(callback: CallbackQuery, state: FSMContext):
    """Пропуск добавления вложения"""
    await show_broadcast_confirmation(callback, state)

@router.callback_query(F.data.startswith("admin:attachment_"), StateFilter(AdminStates.broadcast_adding_attachment))
async def select_attachment_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа вложения"""
    attachment_type = callback.data.split("_")[1]
    
    await state.update_data(expected_attachment_type=attachment_type)
    
    type_names = {
        "photo": "фото",
        "document": "документ", 
        "video": "видео",
        "audio": "аудио"
    }
    
    text = _("""
📎 Отправьте {type}

Просто отправьте файл в следующем сообщении.
""", "ru").format(type=type_names.get(attachment_type, "файл"))
    
    await safe_edit_message(
        callback.message, text,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(StateFilter(AdminStates.broadcast_adding_attachment))
async def process_attachment(message: Message, state: FSMContext):
    """Обработка полученного вложения"""
    data = await state.get_data()
    expected_type = data.get('expected_attachment_type')
    
    attachment_info = None
    
    # Проверяем тип полученного сообщения
    if message.photo and expected_type == "photo":
        attachment_info = {
            "type": "photo",
            "file_id": message.photo[-1].file_id,
            "caption": message.caption
        }
    elif message.document and expected_type == "document":
        attachment_info = {
            "type": "document",
            "file_id": message.document.file_id,
            "caption": message.caption,
            "filename": message.document.file_name
        }
    elif message.video and expected_type == "video":
        attachment_info = {
            "type": "video",
            "file_id": message.video.file_id,
            "caption": message.caption
        }
    elif message.audio and expected_type == "audio":
        attachment_info = {
            "type": "audio",
            "file_id": message.audio.file_id,
            "caption": message.caption
        }
    else:
        await message.answer(_(
            "❌ Неверный тип файла. Отправьте файл нужного типа или выберите другой тип вложения.", "ru"
        ), parse_mode="Markdown")
        return
    
    await state.update_data(attachment=attachment_info)
    
    # Показываем превью вложения
    text = _("""
✅ Вложение получено!

📎 Тип: {type}
""", "ru").format(type=attachment_info["type"])
    
    if attachment_info.get("filename"):
        text += f"\n📄 Имя файла: {attachment_info['filename']}"
    
    if attachment_info.get("caption"):
        text += f"\n💬 Подпись: {attachment_info['caption']}"
    
    await message.answer(
        text,
        reply_markup=get_attachment_confirm_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin:confirm_attachment", StateFilter(AdminStates.broadcast_adding_attachment))
async def confirm_attachment(callback: CallbackQuery, state: FSMContext):
    """Подтверждение вложения"""
    await show_broadcast_confirmation(callback, state)

@router.callback_query(F.data == "admin:replace_attachment", StateFilter(AdminStates.broadcast_adding_attachment))
async def replace_attachment(callback: CallbackQuery, state: FSMContext):
    """Замена вложения"""
    await add_attachment(callback, state)

@router.callback_query(F.data == "admin:remove_attachment", StateFilter(AdminStates.broadcast_adding_attachment))
async def remove_attachment(callback: CallbackQuery, state: FSMContext):
    """Удаление вложения"""
    data = await state.get_data()
    if 'attachment' in data:
        del data['attachment']
        await state.set_data(data)
    
    await show_broadcast_confirmation(callback, state)

async def show_broadcast_confirmation(callback_or_message, state: FSMContext):
    """Показывает подтверждение рассылки"""
    data = await state.get_data()
    broadcast_type = data.get('broadcast_type')
    broadcast_message = data.get('broadcast_message')
    attachment = data.get('attachment')
    
    # Получаем количество получателей

    if broadcast_type == "all":
        recipients_count = await UserRepository.get_active_count()
        audience = "всем активным пользователям"
    elif broadcast_type == "tournament_users":
        recipients_count = await TeamRepository.get_tournament_participants_count()
        audience = "участникам турниров"
    elif broadcast_type == "team_captains":
        recipients_count = await TeamRepository.get_captains_count()
        audience = "капитанам команд"
    else:
        recipients_count = 0
        audience = "неизвестной аудитории"
    
    # Показываем превью сообщения
    preview_text = broadcast_message[:200] + "..." if len(broadcast_message) > 200 else broadcast_message
    
    text = _("""
📢 Подтверждение рассылки

🎯 Аудитория: {audience}
👥 Получателей: {count}

📝 Текст сообщения:
{preview}
""", "ru").format(
        audience=audience,
        count=recipients_count,
        preview=preview_text
    )
    
    # Добавляем информацию о вложении
    if attachment:
        text += f"\n📎 Вложение: {attachment['type']}"
        if attachment.get('filename'):
            text += f" ({attachment['filename']})"
    
    text += f"\n\n⚠️ Внимание! После подтверждения сообщение будет отправлено {recipients_count} пользователям.\n\nПодтвердить рассылку?"
    
    if hasattr(callback_or_message, 'message'):
        # Это callback
        await safe_edit_message(
            callback_or_message.message, text,
            reply_markup=get_confirmation_keyboard("broadcast"),
            parse_mode="Markdown"
        )
        await callback_or_message.answer()
    else:
        # Это message
        await callback_or_message.answer(
            text,
            reply_markup=get_confirmation_keyboard("broadcast"),
            parse_mode="Markdown"
        )

@router.callback_query(F.data == "admin:confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и выполнение рассылки"""
    data = await state.get_data()
    broadcast_type = data.get('broadcast_type')
    broadcast_message = data.get('broadcast_message')
    attachment = data.get('attachment')
    
    if not broadcast_message:
        await callback.answer(_("❌ Сообщение не найдено", "ru"))
        return
    
    # Показываем сообщение о начале рассылки
    text = _("""
📤 Рассылка запущена

Сообщение отправляется получателям...
Это может занять несколько минут.

Статус будет обновлен после завершения.
""", "ru")
    
    await safe_edit_message(callback.message, text, parse_mode="Markdown")
    await callback.answer()
    
    # Запускаем рассылку в фоне
    asyncio.create_task(
        perform_broadcast(
            callback.bot,
            callback.from_user.id,
            callback.message.chat.id,
            callback.message.message_id,
            broadcast_type,
            broadcast_message,
            attachment
        )
    )
    
    await state.clear()

async def perform_broadcast(bot, admin_id: int, chat_id: int, message_id: int, broadcast_type: str, message_text: str, attachment: dict = None):
    """Выполнение рассылки"""
    try:

        # Получаем список получателей
        if broadcast_type == "all":
            recipients = await UserRepository.get_all_active_users()
        elif broadcast_type == "tournament_users":
            recipients = await TeamRepository.get_tournament_participants()
        elif broadcast_type == "team_captains":
            recipients = await TeamRepository.get_all_captains()
        else:
            recipients = []
        
        total_recipients = len(recipients)
        sent_count = 0
        failed_count = 0
        
        logger.info(f"Начата рассылка администратором {admin_id}. Получателей: {total_recipients}")
        
        # Отправляем сообщения
        for i, recipient in enumerate(recipients):
            try:
                # Отправляем сообщение с вложением или без
                if attachment:
                    if attachment['type'] == 'photo':
                        await bot.send_photo(
                            recipient.telegram_id, 
                            attachment['file_id'],
                            caption=message_text,
                            parse_mode="Markdown"
                        )
                    elif attachment['type'] == 'document':
                        await bot.send_document(
                            recipient.telegram_id, 
                            attachment['file_id'],
                            caption=message_text,
                            parse_mode="Markdown"
                        )
                    elif attachment['type'] == 'video':
                        await bot.send_video(
                            recipient.telegram_id, 
                            attachment['file_id'],
                            caption=message_text,
                            parse_mode="Markdown"
                        )
                    elif attachment['type'] == 'audio':
                        await bot.send_audio(
                            recipient.telegram_id, 
                            attachment['file_id'],
                            caption=message_text,
                            parse_mode="Markdown"
                        )
                else:
                    await bot.send_message(recipient.telegram_id, message_text, parse_mode="Markdown")
                sent_count += 1
                
                # Небольшая задержка между сообщениями
                await asyncio.sleep(0.1)
                
                # Обновляем статус каждые 10 сообщений
                if (i + 1) % 10 == 0:
                    progress_text = _("""
📤 Рассылка в процессе

📊 Прогресс: {sent}/{total}
✅ Отправлено: {sent}
❌ Ошибок: {failed}

⏳ Продолжается отправка...
""", "ru").format(
                        sent=sent_count,
                        total=total_recipients,
                        failed=failed_count
                    )
                    
                    try:
                        await bot.edit_message_text(
            progress_text,
                            chat_id=chat_id,
                            message_id=message_id,
            parse_mode="Markdown"
        )
                    except Exception:
                        pass  # Игнорируем ошибки обновления статуса
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Ошибка отправки сообщения пользователю {recipient.telegram_id}: {e}")
        
        # Отправляем финальный отчет
        final_text = _("""
✅ Рассылка завершена

📊 Результаты:
👥 Всего получателей: {total}
✅ Успешно отправлено: {sent}
❌ Ошибок: {failed}
📈 Успешность: {success_rate}%

📅 Завершено: {completed}
""", "ru").format(
            total=total_recipients,
            sent=sent_count,
            failed=failed_count,
            success_rate=round((sent_count / total_recipients * 100) if total_recipients > 0 else 0, 1),
            completed=datetime.now().strftime("%d.%m.%Y %H:%M")
        )
        
        keyboard = [[
            InlineKeyboardButton(
                text=_("🔙 К рассылке", "ru"),
                callback_data="admin:broadcast"
            )
        ]]
        
        await bot.edit_message_text(
            final_text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="Markdown"
        )
        
        logger.info(f"Рассылка завершена. Отправлено: {sent_count}/{total_recipients}")
        
    except Exception as e:
        logger.error(f"Критическая ошибка в рассылке: {e}")
        
        try:
            error_text = _("""
❌ Ошибка рассылки

Произошла критическая ошибка при выполнении рассылки.
Проверьте логи для получения подробной информации.
""", "ru")
            
            keyboard = [[
                InlineKeyboardButton(
                    text=_("🔙 К рассылке", "ru"),
                    callback_data="admin:broadcast"
                )
            ]]
            
            await bot.edit_message_text(
                error_text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception:
            pass

@router.callback_query(F.data == "admin:cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    await state.clear()
    
    text = _("""
❌ Рассылка отменена

Возвращаемся в меню рассылки.
""", "ru")
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_broadcast_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin:broadcast_selective")
async def start_selective_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начало выборочной рассылки"""
    await state.clear()
    
    text = _("""
🎯 Выборочная рассылка

Выберите критерий для отбора получателей:

🆔 По списку ID - указать конкретные Telegram ID
🌍 По языку - пользователи с определенным языком
📍 По региону - пользователи из определенного региона
""", "ru")
    
    from .keyboards import get_selective_broadcast_keyboard
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_selective_broadcast_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin:selective_by_ids")
async def selective_by_ids(callback: CallbackQuery, state: FSMContext):
    """Рассылка по списку ID"""
    text = _("""
🆔 Рассылка по списку ID

Введите Telegram ID пользователей через запятую или пробел.

Пример:
`123456789, 987654321, 555666777`

Или:
`123456789 987654321 555666777`
""", "ru")
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_broadcast_cancel_keyboard(), 
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.selective_broadcast_entering_ids)
    await callback.answer()

@router.callback_query(F.data == "admin:selective_by_language")
async def selective_by_language(callback: CallbackQuery, state: FSMContext):
    """Рассылка по языку"""
    text = _("""
🌍 Рассылка по языку

Выберите язык пользователей для рассылки:
""", "ru")
    
    from .keyboards import get_language_selection_keyboard
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_language_selection_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin:selective_by_region")
async def selective_by_region(callback: CallbackQuery, state: FSMContext):
    """Рассылка по региону"""
    text = _("""
📍 Рассылка по региону

Выберите регион пользователей для рассылки:
""", "ru")
    
    from .keyboards import get_region_selection_keyboard
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_region_selection_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin:lang_"))
async def process_language_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора языка"""
    language = callback.data.split("_")[1]  # admin:lang_ru -> ru

    users = await UserRepository.get_users_by_language(language)
    
    lang_names = {
        "ru": "русский",
        "ky": "кыргызский", 
        "en": "английский"
    }
    
    text = _("""
🌍 Рассылка пользователям на {language}

👥 Найдено пользователей: {count}

📝 Введите текст сообщения для рассылки:
""", "ru").format(
        language=lang_names.get(language, language),
        count=len(users)
    )
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_broadcast_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.selective_broadcast_entering_message)
    await state.update_data(
        selective_type="language",
        selective_value=language,
        recipients_count=len(users)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin:region_"))
async def process_region_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора региона"""
    region = callback.data.split("_")[1]  # admin:region_kg -> kg

    users = await UserRepository.get_users_by_region(region)
    
    region_names = {
        "kg": "Кыргызстан",
        "kz": "Казахстан",
        "ru": "Россия",
        "other": "Другие страны"
    }
    
    text = _("""
📍 Рассылка пользователям из региона {region}

👥 Найдено пользователей: {count}

📝 Введите текст сообщения для рассылки:
""", "ru").format(
        region=region_names.get(region, region),
        count=len(users)
    )
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_broadcast_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.selective_broadcast_entering_message)
    await state.update_data(
        selective_type="region",
        selective_value=region,
        recipients_count=len(users)
    )
    await callback.answer()


# Новые хендлеры для наших кнопок
@router.callback_query(F.data.startswith("admin:broadcast_lang_"))
async def process_broadcast_language_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора языка для рассылки"""
    language = callback.data.split("_")[-1]  # admin:broadcast_lang_ru -> ru

    users = await UserRepository.get_users_by_language(language)
    
    lang_names = {
        "ru": "русский",
        "ky": "кыргызский", 
        "kk": "казахский"
    }
    
    text = _("""
🌍 Рассылка пользователям на {language}

👥 Найдено пользователей: {count}

📝 Введите текст сообщения для рассылки:
""", "ru").format(
        language=lang_names.get(language, language),
        count=len(users)
    )
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_broadcast_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.selective_broadcast_entering_message)
    await state.update_data(
        selective_type="language",
        selective_value=language,
        recipients_count=len(users)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:broadcast_region_"))
async def process_broadcast_region_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора региона для рассылки"""
    region = callback.data.split("_")[-1]  # admin:broadcast_region_kg -> kg

    users = await UserRepository.get_users_by_region(region)
    
    region_names = {
        "kg": "Кыргызстан",
        "kz": "Казахстан",
        "ru": "Россия"
    }
    
    text = _("""
📍 Рассылка пользователям из региона {region}

👥 Найдено пользователей: {count}

📝 Введите текст сообщения для рассылки:
""", "ru").format(
        region=region_names.get(region, region),
        count=len(users)
    )
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_broadcast_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.selective_broadcast_entering_message)
    await state.update_data(
        selective_type="region",
        selective_value=region,
        recipients_count=len(users)
    )
    await callback.answer()


@router.message(StateFilter(AdminStates.selective_broadcast_entering_ids))
async def process_ids_input(message: Message, state: FSMContext):
    """Обработка ввода списка ID"""
    import re
    
    if not message.text:
        await message.answer(_(
            "❌ Пожалуйста, отправьте текстовое сообщение со списком ID.", "ru"
        ))
        return
    
    # Парсим ID из текста
    text = message.text.strip()
    # Находим все числа в тексте
    ids = re.findall(r'\d+', text)
    
    if not ids:
        await message.answer(_(
            "❌ Не найдено ни одного ID. Введите числа через запятую или пробел.", "ru"
        ))
        return
    
    # Конвертируем в int
    try:
        user_ids = [int(id_str) for id_str in ids]
    except ValueError:
        await message.answer(_(
            "❌ Ошибка в формате ID. Используйте только числа.", "ru"
        ))
        return

    users = await UserRepository.get_users_by_ids(user_ids)
    
    found_ids = [user.telegram_id for user in users]
    not_found_ids = [uid for uid in user_ids if uid not in found_ids]
    
    info_text = f"🆔 Рассылка по списку ID\n\n"
    info_text += f"📤 Указано ID: {len(user_ids)}\n"
    info_text += f"✅ Найдено пользователей: {len(users)}\n"
    
    if not_found_ids:
        info_text += f"❌ Не найдено: {len(not_found_ids)} ID\n"
        if len(not_found_ids) <= 5:
            info_text += f"   ({', '.join(map(str, not_found_ids))})\n"
    
    info_text += "\n📝 Введите текст сообщения для рассылки:"
    
    await message.answer(
        info_text,
        reply_markup=get_broadcast_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.selective_broadcast_entering_message)
    await state.update_data(
        selective_type="ids",
        selective_value=user_ids,
        recipients_count=len(users)
    )

@router.message(StateFilter(AdminStates.selective_broadcast_entering_message))
async def process_selective_message(message: Message, state: FSMContext):
    """Обработка текста для выборочной рассылки"""
    if not message.text:
        await message.answer(_(
            "❌ Пожалуйста, отправьте текстовое сообщение для рассылки.", "ru"
        ), parse_mode="Markdown")
        return
    
    broadcast_text = message.text.strip()
    
    if len(broadcast_text) > 4000:
        await message.answer(_(
            "❌ Сообщение слишком длинное (максимум 4000 символов).", "ru"
        ), parse_mode="Markdown")
        return
    
    await state.update_data(broadcast_message=broadcast_text)
    
    # Предлагаем добавить вложение
    text = _("""
📝 Текст рассылки сохранен!

Хотите добавить вложение к рассылке?

📎 Поддерживаются: фото, видео, документы, аудио
""", "ru")
    
    await message.answer(
        text,
        reply_markup=get_attachment_keyboard(),
        parse_mode="Markdown"
    )
    
    await state.set_state(AdminStates.selective_broadcast_adding_attachment)

# Обработчики вложений для выборочной рассылки
@router.callback_query(F.data == "admin:add_attachment", StateFilter(AdminStates.selective_broadcast_adding_attachment))
async def add_selective_attachment(callback: CallbackQuery, state: FSMContext):
    """Добавление вложения к выборочной рассылке"""
    text = _("""
📎 Выберите тип вложения

Поддерживаемые форматы:
🖼️ Фото: JPG, PNG, GIF
📄 Документы: PDF, DOC, TXT и др.
🎥 Видео: MP4, AVI, MOV
🎵 Аудио: MP3, WAV, OGG
""", "ru")
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_attachment_options_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin:skip_attachment", StateFilter(AdminStates.selective_broadcast_adding_attachment))
async def skip_selective_attachment(callback: CallbackQuery, state: FSMContext):
    """Пропуск добавления вложения к выборочной рассылке"""
    await show_selective_broadcast_confirmation(callback, state)

@router.callback_query(F.data.startswith("admin:attachment_"), StateFilter(AdminStates.selective_broadcast_adding_attachment))
async def select_selective_attachment_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа вложения для выборочной рассылки"""
    attachment_type = callback.data.split("_")[1]
    
    await state.update_data(expected_attachment_type=attachment_type)
    
    type_names = {
        "photo": "фото",
        "document": "документ", 
        "video": "видео",
        "audio": "аудио"
    }
    
    text = _("""
📎 Отправьте {type}

Просто отправьте файл в следующем сообщении.
""", "ru").format(type=type_names.get(attachment_type, "файл"))
    
    await safe_edit_message(
        callback.message, text,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(StateFilter(AdminStates.selective_broadcast_adding_attachment))
async def process_selective_attachment(message: Message, state: FSMContext):
    """Обработка полученного вложения для выборочной рассылки"""
    data = await state.get_data()
    expected_type = data.get('expected_attachment_type')
    
    attachment_info = None
    
    # Проверяем тип полученного сообщения
    if message.photo and expected_type == "photo":
        attachment_info = {
            "type": "photo",
            "file_id": message.photo[-1].file_id,
            "caption": message.caption
        }
    elif message.document and expected_type == "document":
        attachment_info = {
            "type": "document",
            "file_id": message.document.file_id,
            "caption": message.caption,
            "filename": message.document.file_name
        }
    elif message.video and expected_type == "video":
        attachment_info = {
            "type": "video",
            "file_id": message.video.file_id,
            "caption": message.caption
        }
    elif message.audio and expected_type == "audio":
        attachment_info = {
            "type": "audio",
            "file_id": message.audio.file_id,
            "caption": message.caption
        }
    else:
        await message.answer(_(
            "❌ Неверный тип файла. Отправьте файл нужного типа или выберите другой тип вложения.", "ru"
        ), parse_mode="Markdown")
        return
    
    await state.update_data(attachment=attachment_info)
    
    # Показываем превью вложения
    text = _("""
✅ Вложение получено!

📎 Тип: {type}
""", "ru").format(type=attachment_info["type"])
    
    if attachment_info.get("filename"):
        text += f"\n📄 Имя файла: {attachment_info['filename']}"
    
    if attachment_info.get("caption"):
        text += f"\n💬 Подпись: {attachment_info['caption']}"
    
    await message.answer(
        text,
        reply_markup=get_attachment_confirm_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin:confirm_attachment", StateFilter(AdminStates.selective_broadcast_adding_attachment))
async def confirm_selective_attachment(callback: CallbackQuery, state: FSMContext):
    """Подтверждение вложения для выборочной рассылки"""
    await show_selective_broadcast_confirmation(callback, state)

@router.callback_query(F.data == "admin:replace_attachment", StateFilter(AdminStates.selective_broadcast_adding_attachment))
async def replace_selective_attachment(callback: CallbackQuery, state: FSMContext):
    """Замена вложения для выборочной рассылки"""
    await add_selective_attachment(callback, state)

@router.callback_query(F.data == "admin:remove_attachment", StateFilter(AdminStates.selective_broadcast_adding_attachment))
async def remove_selective_attachment(callback: CallbackQuery, state: FSMContext):
    """Удаление вложения для выборочной рассылки"""
    data = await state.get_data()
    if 'attachment' in data:
        del data['attachment']
        await state.set_data(data)
    
    await show_selective_broadcast_confirmation(callback, state)

async def show_selective_broadcast_confirmation(callback_or_message, state: FSMContext):
    """Показывает подтверждение выборочной рассылки"""
    data = await state.get_data()
    selective_type = data.get('selective_type')
    selective_value = data.get('selective_value')
    recipients_count = data.get('recipients_count', 0)
    broadcast_message = data.get('broadcast_message')
    attachment = data.get('attachment')
    
    type_names = {
        "ids": "по списку ID",
        "language": f"по языку ({selective_value})",
        "region": f"по региону ({selective_value})"
    }
    
    # Показываем превью
    preview_text = broadcast_message[:200] + "..." if len(broadcast_message) > 200 else broadcast_message
    
    text = _("""
📤 Подтверждение выборочной рассылки

🎯 Критерий: {criteria}
👥 Получателей: {count}

📝 Текст сообщения:
{preview}
""", "ru").format(
        criteria=type_names.get(selective_type, "неизвестно"),
        count=recipients_count,
        preview=preview_text
    )
    
    # Добавляем информацию о вложении
    if attachment:
        text += f"\n📎 Вложение: {attachment['type']}"
        if attachment.get('filename'):
            text += f" ({attachment['filename']})"
    
    text += f"\n\n⚠️ Внимание! После подтверждения сообщение будет отправлено {recipients_count} пользователям.\n\nПодтвердить рассылку?"
    
    if hasattr(callback_or_message, 'message'):
        # Это callback
        await safe_edit_message(
            callback_or_message.message, text,
            reply_markup=get_confirmation_keyboard("selective_broadcast"),
            parse_mode="Markdown"
        )
        await callback_or_message.answer()
    else:
        # Это message
        await callback_or_message.answer(
            text,
            reply_markup=get_confirmation_keyboard("selective_broadcast"),
            parse_mode="Markdown"
        )

@router.callback_query(F.data == "admin:confirm_selective_broadcast")
async def confirm_selective_broadcast(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выборочной рассылки"""
    data = await state.get_data()
    selective_type = data.get('selective_type')
    selective_value = data.get('selective_value')
    broadcast_message = data.get('broadcast_message')
    attachment = data.get('attachment')
    
    if not broadcast_message:
        await callback.answer(_("❌ Сообщение не найдено", "ru"))
        return
    
    text = _("""
📤 Выборочная рассылка запущена

Сообщение отправляется выбранным получателям...
Это может занять несколько минут.

Статус будет обновлен после завершения.
""", "ru")
    
    await safe_edit_message(callback.message, text, parse_mode="Markdown")
    await callback.answer()
    
    # Запускаем рассылку в фоне
    asyncio.create_task(
        perform_selective_broadcast(
            callback.bot,
            callback.from_user.id,
            callback.message.chat.id,
            callback.message.message_id,
            selective_type,
            selective_value,
            broadcast_message,
            attachment
        )
    )
    
    await state.clear()

async def perform_selective_broadcast(
    bot,
    admin_id: int, 
    chat_id: int, 
    message_id: int, 
    selective_type: str,
    selective_value,
    message_text: str,
    attachment: dict = None
):
    """Выполнение выборочной рассылки"""
    try:

        # Получаем список получателей в зависимости от типа
        if selective_type == "ids":
            recipients = await UserRepository.get_users_by_ids(selective_value)
        elif selective_type == "language":
            recipients = await UserRepository.get_users_by_language(selective_value)
        elif selective_type == "region":
            recipients = await UserRepository.get_users_by_region(selective_value)
        else:
            recipients = []
        
        total_recipients = len(recipients)
        sent_count = 0
        failed_count = 0
        
        logger.info(f"Начата выборочная рассылка администратором {admin_id}. Получателей: {total_recipients}")
        
        # Отправляем сообщения
        for i, recipient in enumerate(recipients):
            try:
                # Отправляем сообщение с вложением или без
                if attachment:
                    if attachment['type'] == 'photo':
                        await bot.send_photo(
                            recipient.telegram_id, 
                            attachment['file_id'],
                            caption=message_text,
                            parse_mode="Markdown"
                        )
                    elif attachment['type'] == 'document':
                        await bot.send_document(
                            recipient.telegram_id, 
                            attachment['file_id'],
                            caption=message_text,
                            parse_mode="Markdown"
                        )
                    elif attachment['type'] == 'video':
                        await bot.send_video(
                            recipient.telegram_id, 
                            attachment['file_id'],
                            caption=message_text,
                            parse_mode="Markdown"
                        )
                    elif attachment['type'] == 'audio':
                        await bot.send_audio(
                            recipient.telegram_id, 
                            attachment['file_id'],
                            caption=message_text,
                            parse_mode="Markdown"
                        )
                else:
                    await bot.send_message(recipient.telegram_id, message_text, parse_mode="Markdown")
                sent_count += 1
                
                # Небольшая задержка
                await asyncio.sleep(0.1)
                
                # Обновляем статус каждые 5 сообщений
                if (i + 1) % 5 == 0:
                    progress_text = _("""
📤 Выборочная рассылка в процессе

📊 Прогресс: {sent}/{total}
✅ Отправлено: {sent}
❌ Ошибок: {failed}

⏳ Продолжается отправка...
""", "ru").format(
                        sent=sent_count,
                        total=total_recipients,
                        failed=failed_count
                    )
                    
                    try:
                        await bot.edit_message_text(
            progress_text,
                            chat_id=chat_id,
                            message_id=message_id,
            parse_mode="Markdown"
        )
                    except Exception:
                        pass
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Ошибка отправки сообщения пользователю {recipient.telegram_id}: {e}")
        
        # Финальный отчет
        final_text = _("""
✅ Выборочная рассылка завершена

📊 Результаты:
👥 Всего получателей: {total}
✅ Успешно отправлено: {sent}
❌ Ошибок: {failed}
📈 Успешность: {success_rate}%

📅 Завершено: {completed}
""", "ru").format(
            total=total_recipients,
            sent=sent_count,
            failed=failed_count,
            success_rate=round((sent_count / total_recipients * 100) if total_recipients > 0 else 0, 1),
            completed=datetime.now().strftime("%d.%m.%Y %H:%M")
        )
        
        keyboard = [[
            InlineKeyboardButton(
                text=_("🔙 К рассылке", "ru"),
                callback_data="admin:broadcast"
            )
        ]]
        
        await bot.edit_message_text(
            final_text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="Markdown"
        )
        
        logger.info(f"Выборочная рассылка завершена. Отправлено: {sent_count}/{total_recipients}")
        
    except Exception as e:
        logger.error(f"Критическая ошибка в выборочной рассылке: {e}")

@router.callback_query(F.data == "admin:cancel_selective_broadcast")
async def cancel_selective_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отмена выборочной рассылки"""
    await state.clear()
    
    text = _("""
❌ Выборочная рассылка отменена

Возвращаемся в меню рассылки.
""", "ru")
    
    await safe_edit_message(
        callback.message, text,
        reply_markup=get_broadcast_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


# Обработчик кнопки назад для ввода текста рассылки  
@router.callback_query(F.data == "admin:broadcast")
async def handle_broadcast_back(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки Назад при создании рассылки"""
    current_state = await state.get_state()
    
    # Если находимся в состоянии создания рассылки, возвращаемся к меню выбора типа рассылки
    if current_state in [
        AdminStates.creating_broadcast_message,
        AdminStates.selective_broadcast_entering_ids,
        AdminStates.selective_broadcast_entering_message
    ]:
        await broadcast_menu(callback, state)
    else:
        # Иначе просто очищаем состояние и показываем меню рассылки
        await state.clear()
        await broadcast_menu(callback, state)