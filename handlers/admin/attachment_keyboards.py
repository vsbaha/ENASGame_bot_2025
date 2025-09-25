"""
Дополнительные клавиатуры для вложений в рассылках
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_attachment_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для добавления вложений"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="📎 Добавить вложение",
                callback_data="admin:add_attachment"
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Продолжить без вложения",
                callback_data="admin:skip_attachment"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="admin:broadcast"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_attachment_options_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с опциями вложений"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="🖼️ Фото",
                callback_data="admin:attachment_photo"
            ),
            InlineKeyboardButton(
                text="📄 Документ",
                callback_data="admin:attachment_document"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎥 Видео",
                callback_data="admin:attachment_video"
            ),
            InlineKeyboardButton(
                text="🎵 Аудио",
                callback_data="admin:attachment_audio"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="admin:skip_attachment"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_attachment_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения вложения"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Использовать это вложение",
                callback_data="admin:confirm_attachment"
            )
        ],
        [
            InlineKeyboardButton(
                text="📎 Заменить вложение",
                callback_data="admin:replace_attachment"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Убрать вложение",
                callback_data="admin:remove_attachment"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)