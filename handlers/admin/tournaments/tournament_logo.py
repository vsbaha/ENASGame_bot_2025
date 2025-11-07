"""
Управление логотипом турнира
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database.repositories import TournamentRepository
from utils.message_utils import safe_edit_message, safe_send_message
from ..states import AdminStates

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("admin:edit_logo_"))
async def edit_tournament_logo_menu(callback: CallbackQuery, state: FSMContext):
    """Меню управления логотипом турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем информацию о турнире
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Формируем меню
        keyboard = []
        
        if tournament.logo_file_id:
            # Если логотип есть, показываем кнопки просмотра, замены и удаления
            text = f"""🖼️ **Логотип турнира**

🏆 **{tournament.name}**

📊 **Статус:** Логотип загружен

Выберите действие:"""
            
            keyboard.extend([
                [
                    InlineKeyboardButton(
                        text="👁️ Просмотреть логотип",
                        callback_data=f"admin:view_logo_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Заменить логотип",
                        callback_data=f"admin:replace_logo_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑️ Удалить логотип",
                        callback_data=f"admin:delete_logo_{tournament_id}"
                    )
                ]
            ])
        else:
            # Если логотипа нет, показываем кнопку загрузки
            text = f"""🖼️ **Логотип турнира**

🏆 **{tournament.name}**

📊 **Статус:** Логотип не загружен

Загрузите логотип для турнира:"""
            
            keyboard.append([
                InlineKeyboardButton(
                    text="📤 Загрузить логотип",
                    callback_data=f"admin:upload_logo_{tournament_id}"
                )
            ])
        
        # Кнопка возврата
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
        logger.error(f"Ошибка меню логотипа турнира: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:view_logo_"))
async def view_tournament_logo(callback: CallbackQuery, state: FSMContext):
    """Просмотр текущего логотипа турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем информацию о турнире
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament or not tournament.logo_file_id:
            await callback.answer("❌ Логотип не найден", show_alert=True)
            return
        
        # Отправляем логотип
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔙 Назад к управлению логотипом",
                    callback_data=f"admin:edit_logo_{tournament_id}"
                )
            ]
        ]
        
        try:
            await callback.message.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=tournament.logo_file_id,
                caption=f"🖼️ **Логотип турнира:** {tournament.name}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
            await callback.answer("✅ Логотип отправлен")
        except Exception as e:
            logger.error(f"Ошибка отправки логотипа: {e}")
            await callback.answer("❌ Ошибка отправки логотипа", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка просмотра логотипа: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:upload_logo_"))
async def start_upload_logo(callback: CallbackQuery, state: FSMContext):
    """Начало загрузки логотипа турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Сохраняем ID турнира в состояние
        await state.update_data(editing_tournament_id=tournament_id)
        
        text = """🖼️ **Загрузите логотип турнира:**

*Поддерживаемые форматы: JPG, JPEG, PNG*
*Максимальный размер: 5 МБ*
*Рекомендуемое разрешение: 512x512 px*

Отправьте изображение:"""
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown"
        )
        
        await state.set_state(AdminStates.editing_tournament_logo)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала загрузки логотипа: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:replace_logo_"))
async def start_replace_logo(callback: CallbackQuery, state: FSMContext):
    """Начало замены логотипа турнира"""
    # Используем тот же обработчик, что и для загрузки
    await start_upload_logo(callback, state)


@router.message(AdminStates.editing_tournament_logo)
async def handle_logo_upload(message: Message, state: FSMContext):
    """Обработка загруженного логотипа"""
    try:
        data = await state.get_data()
        tournament_id = data.get('editing_tournament_id')
        
        if not tournament_id:
            await safe_send_message(
                message.chat.id,
                "❌ **Ошибка:** Не найден ID турнира",
                parse_mode="Markdown"
            )
            await state.clear()
            return
        
        # Проверяем наличие фото
        if not message.photo:
            await safe_send_message(
                message.chat.id,
                "❌ **Ожидается изображение**\n\nОтправьте фото (JPG/PNG)",
                parse_mode="Markdown"
            )
            return
        
        # Берем самое большое фото
        photo = message.photo[-1]
        
        # Проверка размера файла (5 МБ)
        max_size = 5 * 1024 * 1024  # 5 MB
        if photo.file_size and photo.file_size > max_size:
            await safe_send_message(
                message.chat.id,
                f"❌ **Изображение слишком большое**\n\nМаксимальный размер: 5 МБ\nВаше изображение: {photo.file_size / 1024 / 1024:.1f} МБ",
                parse_mode="Markdown"
            )
            return
        
        # Сохраняем логотип в базу данных
        success = await TournamentRepository.update_logo(tournament_id, photo.file_id)
        
        if success:
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="🔙 Назад к управлению логотипом",
                        callback_data=f"admin:edit_logo_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏆 К турниру",
                        callback_data=f"admin:manage_tournament_{tournament_id}"
                    )
                ]
            ]
            
            await safe_send_message(
                message.chat.id,
                "✅ **Логотип успешно загружен!**",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        else:
            await safe_send_message(
                message.chat.id,
                "❌ **Ошибка сохранения логотипа**\n\nПопробуйте еще раз",
                parse_mode="Markdown"
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка загрузки логотипа: {e}")
        await safe_send_message(
            message.chat.id,
            "❌ **Ошибка обработки логотипа**",
            parse_mode="Markdown"
        )
        await state.clear()


@router.callback_query(F.data.startswith("admin:delete_logo_"))
async def confirm_delete_logo(callback: CallbackQuery, state: FSMContext):
    """Подтверждение удаления логотипа"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        text = """🗑️ **Удаление логотипа**

Вы уверены, что хотите удалить логотип турнира?

⚠️ Это действие нельзя отменить."""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"admin:delete_logo_confirmed_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"admin:edit_logo_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка подтверждения удаления логотипа: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:delete_logo_confirmed_"))
async def delete_logo_confirmed(callback: CallbackQuery, state: FSMContext):
    """Окончательное удаление логотипа"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Удаляем логотип
        success = await TournamentRepository.remove_logo(tournament_id)
        
        if success:
            await callback.answer("✅ Логотип удален", show_alert=True)
            
            # Возвращаемся к меню логотипа
            callback.data = f"admin:edit_logo_{tournament_id}"
            await edit_tournament_logo_menu(callback, state)
        else:
            await callback.answer("❌ Ошибка удаления", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка удаления логотипа: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
