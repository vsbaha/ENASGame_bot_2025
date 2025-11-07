"""
Обработка файлов правил турниров
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Document, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database.repositories import TournamentRepository
from utils.message_utils import safe_edit_message, safe_send_message
from ..states import AdminStates

router = Router()
logger = logging.getLogger(__name__)

# Допустимые типы файлов и их MIME-типы
ALLOWED_MIME_TYPES = {
    'application/pdf': '.pdf',
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
}

# Максимальный размер файла (20 МБ)
MAX_FILE_SIZE = 20 * 1024 * 1024


def is_valid_document(document: Document) -> tuple[bool, str]:
    """
    Проверка валидности документа
    
    Returns:
        tuple[bool, str]: (валиден ли файл, сообщение об ошибке)
    """
    # Проверка размера файла
    if document.file_size > MAX_FILE_SIZE:
        return False, f"❌ Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE // (1024 * 1024)} МБ"
    
    # Проверка типа файла
    if document.mime_type not in ALLOWED_MIME_TYPES:
        allowed_exts = ', '.join(ALLOWED_MIME_TYPES.values())
        return False, f"❌ Неподдерживаемый тип файла. Разрешены: {allowed_exts}"
    
    return True, ""


@router.callback_query(F.data.startswith("admin:upload_rules_"))
async def start_upload_rules(callback: CallbackQuery, state: FSMContext):
    """Начало загрузки файла правил"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем информацию о турнире
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Сохраняем ID турнира в состояние
        await state.update_data(tournament_id=tournament_id)
        
        text = f"""📋 **Загрузка файла правил**

🏆 Турнир: **{tournament.name}**

📎 **Отправьте файл с правилами турнира**

✅ Поддерживаемые форматы: PDF, DOC, DOCX
📏 Максимальный размер: 20 МБ

Отправьте файл документа в этот чат."""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"admin:edit_tournament_details_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        await state.set_state(AdminStates.creating_tournament_rules_file)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка начала загрузки правил: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(AdminStates.creating_tournament_rules_file, F.document)
async def handle_rules_file_upload(message: Message, state: FSMContext):
    """Обработка загруженного файла правил"""
    try:
        document = message.document
        
        # Валидация файла
        is_valid, error_message = is_valid_document(document)
        
        if not is_valid:
            await safe_send_message(
                message.chat.id, error_message, parse_mode="Markdown"
            )
            return
        
        # Получаем данные из состояния
        data = await state.get_data()
        tournament_id = data.get('tournament_id')
        
        if not tournament_id:
            await safe_send_message(
                message.chat.id,
                "❌ **Ошибка**\n\nНе найден ID турнира. Попробуйте начать заново.",
                parse_mode="Markdown"
            )
            await state.clear()
            return
        
        # Сохраняем файл в базу данных
        file_id = document.file_id
        file_name = document.file_name or f"rules_{tournament_id}.{ALLOWED_MIME_TYPES[document.mime_type]}"
        
        success = await TournamentRepository.update_rules_file(tournament_id, file_id, file_name)
        
        if success:
            file_size_mb = document.file_size / (1024 * 1024)
            
            text = f"""✅ **Файл правил успешно загружен!**

📎 **Название файла:** {file_name}
📏 **Размер:** {file_size_mb:.2f} МБ
📄 **Формат:** {ALLOWED_MIME_TYPES.get(document.mime_type, 'Unknown')}

Файл сохранен и будет доступен участникам турнира."""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="🔙 К редактированию турнира",
                        callback_data=f"admin:edit_tournament_details_{tournament_id}"
                    )
                ]
            ]
            
            await safe_send_message(
                message.chat.id, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            await state.clear()
        else:
            await safe_send_message(
                message.chat.id,
                "❌ **Ошибка сохранения файла**\n\nНе удалось сохранить файл в базу данных.",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Ошибка обработки файла правил: {e}")
        await safe_send_message(
            message.chat.id,
            "❌ **Ошибка**\n\nПроизошла ошибка при обработке файла.",
            parse_mode="Markdown"
        )


@router.message(AdminStates.creating_tournament_rules_file)
async def handle_invalid_rules_file(message: Message, state: FSMContext):
    """Обработка неверного типа сообщения при загрузке правил"""
    await safe_send_message(
        message.chat.id,
        "❌ **Неверный формат**\n\nОтправьте файл документа (PDF, DOC или DOCX).",
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("admin:view_rules_"))
async def view_rules_file(callback: CallbackQuery):
    """Просмотр загруженного файла правил"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем информацию о файле правил
        rules_info = await TournamentRepository.get_rules_file_info(tournament_id)
        
        if not rules_info:
            await callback.answer("❌ Файл правил не загружен", show_alert=True)
            return
        
        file_id, file_name = rules_info
        
        # Отправляем файл пользователю
        await callback.message.answer_document(
            document=file_id,
            caption=f"📋 **Правила турнира**\n\n📎 {file_name}",
            parse_mode="Markdown"
        )
        
        await callback.answer("✅ Файл отправлен")
        
    except Exception as e:
        logger.error(f"Ошибка просмотра файла правил: {e}")
        await callback.answer("❌ Ошибка загрузки файла", show_alert=True)


@router.callback_query(F.data.startswith("admin:delete_rules_"))
async def confirm_delete_rules(callback: CallbackQuery):
    """Подтверждение удаления файла правил"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем информацию о турнире
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Проверяем наличие файла
        rules_info = await TournamentRepository.get_rules_file_info(tournament_id)
        
        if not rules_info:
            await callback.answer("❌ Файл правил не загружен", show_alert=True)
            return
        
        file_id, file_name = rules_info
        
        text = f"""🗑️ **Подтверждение удаления**

⚠️ Вы действительно хотите удалить файл правил?

🏆 **Турнир:** {tournament.name}
📎 **Файл:** {file_name}

**Это действие необратимо!**"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"admin:delete_rules_confirmed_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"admin:edit_tournament_details_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка подтверждения удаления правил: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:delete_rules_confirmed_"))
async def delete_rules_confirmed(callback: CallbackQuery):
    """Окончательное удаление файла правил"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        success = await TournamentRepository.remove_rules_file(tournament_id)
        
        if success:
            await callback.answer("✅ Файл правил удален!", show_alert=True)
            
            # Возвращаемся к редактированию турнира
            from .tournament_management import edit_tournament_details_menu
            callback.data = f"admin:edit_tournament_details_{tournament_id}"
            await edit_tournament_details_menu(callback, None)
        else:
            await callback.answer("❌ Ошибка удаления файла", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка удаления файла правил: {e}")
        await callback.answer("❌ Ошибка удаления", show_alert=True)