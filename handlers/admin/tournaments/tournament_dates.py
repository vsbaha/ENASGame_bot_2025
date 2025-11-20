"""
Дополнительные обработчики для дат и правил турнира
"""
import logging
from datetime import datetime, timedelta
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from utils.message_utils import safe_edit_message
from utils.datetime_utils import format_datetime_for_user
from ..states import AdminStates
from database.repositories import TournamentRepository
from database.models import TournamentFormat
from integrations.challonge_api import ChallongeAPI
from config import settings

router = Router()
logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> tuple[bool, str, str]:
    """Парсинг и валидация даты"""
    date_str = date_str.strip()
    
    # Обработка "завтра", "послезавтра", "сегодня"
    today = datetime.now()
    if "завтра" in date_str.lower():
        base_date = today + timedelta(days=1)
        time_match = re.search(r'(\d{1,2}):(\d{2})', date_str)
        if time_match:
            hour, minute = int(time_match.group(1)), int(time_match.group(2))
            result_date = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        else:
            result_date = base_date.replace(hour=12, minute=0, second=0, microsecond=0)
        
        return True, "", result_date.strftime("%Y-%m-%d %H:%M:%S")
    
    # Парсинг стандартного формата ДД.ММ.ГГГГ ЧЧ:ММ
    pattern = r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})'
    match = re.match(pattern, date_str)
    
    if not match:
        return False, "❌ Неверный формат даты. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ", ""
    
    day, month, year, hour, minute = match.groups()
    
    try:
        result_date = datetime(int(year), int(month), int(day), int(hour), int(minute))
        
        if result_date < today:
            return False, "❌ Дата не может быть в прошлом", ""
        
        return True, "", result_date.strftime("%Y-%m-%d %H:%M:%S")
    
    except ValueError:
        return False, "❌ Некорректная дата", ""


@router.message(StateFilter(AdminStates.creating_tournament_registration_start))
async def process_registration_start_date(message: Message, state: FSMContext):
    """Обработка даты начала регистрации"""
    if not message.text:
        await message.answer("❌ Пожалуйста, введите дату начала регистрации.")
        return
    
    # Валидация даты
    is_valid, error_message, parsed_date = parse_date(message.text)
    
    if not is_valid:
        await message.answer(f"{error_message}\n\nПопробуйте ещё раз:")
        return
    
    # Сохраняем дату в состояние
    await state.update_data(registration_start_date=parsed_date)
    
    # Получаем данные для показа прогресса
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    
    # Переходим к следующему шагу - дата окончания регистрации
    text = f"""✅ **Дата начала регистрации установлена**

📝 **Шаг 6.2: Дата окончания регистрации**

**Турнир:** {tournament_name}

📅 Введите дату окончания регистрации:

▪️ Должна быть после даты начала
▪️ Формат: ДД.ММ.ГГГГ ЧЧ:ММ
▪️ Пример: 05.12.2025 23:59"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад к дате начала",
                callback_data="admin:edit_registration_start"
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
    await state.set_state(AdminStates.creating_tournament_registration_end)


@router.message(StateFilter(AdminStates.creating_tournament_registration_end))
async def process_registration_end_date(message: Message, state: FSMContext):
    """Обработка даты окончания регистрации"""
    if not message.text:
        await message.answer("❌ Пожалуйста, введите дату окончания регистрации.")
        return
    
    # Валидация даты
    is_valid, error_message, parsed_date = parse_date(message.text)
    
    if not is_valid:
        await message.answer(f"{error_message}\n\nПопробуйте ещё раз:")
        return
    
    # Проверяем, что дата окончания после даты начала
    data = await state.get_data()
    start_date_str = data.get('registration_start_date', '')
    
    start_date = datetime.fromisoformat(start_date_str)
    end_date = datetime.fromisoformat(parsed_date)
    
    if end_date <= start_date:
        await message.answer("❌ Дата окончания должна быть после даты начала регистрации.\n\nПопробуйте ещё раз:")
        return
    
    # Сохраняем дату в состояние
    await state.update_data(registration_end_date=parsed_date)
    
    # Получаем данные для показа прогресса
    tournament_name = data.get('tournament_name', '')
    
    # Переходим к следующему шагу - дата начала турнира
    text = f"""✅ **Дата окончания регистрации установлена**

📝 **Шаг 6.3: Дата начала турнира**

**Турнир:** {tournament_name}

📅 Введите дату начала турнира:

▪️ Должна быть после окончания регистрации
▪️ Формат: ДД.ММ.ГГГГ ЧЧ:ММ
▪️ Пример: 06.12.2025 15:00"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад к дате окончания",
                callback_data="admin:edit_registration_end"
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
    await state.set_state(AdminStates.creating_tournament_start_date)


@router.message(StateFilter(AdminStates.creating_tournament_start_date))
async def process_tournament_start_date(message: Message, state: FSMContext):
    """Обработка даты начала турнира"""
    if not message.text:
        await message.answer("❌ Пожалуйста, введите дату начала турнира.")
        return
    
    # Валидация даты
    is_valid, error_message, parsed_date = parse_date(message.text)
    
    if not is_valid:
        await message.answer(f"{error_message}\n\nПопробуйте ещё раз:")
        return
    
    # Проверяем, что дата начала турнира после окончания регистрации
    data = await state.get_data()
    reg_end_date_str = data.get('registration_end_date', '')
    
    reg_end_date = datetime.fromisoformat(reg_end_date_str)
    tournament_start = datetime.fromisoformat(parsed_date)
    
    if tournament_start <= reg_end_date:
        await message.answer("❌ Дата начала турнира должна быть после окончания регистрации.\n\nПопробуйте ещё раз:")
        return
    
    # Сохраняем дату в состояние
    await state.update_data(tournament_start_date=parsed_date)
    
    # Получаем данные для показа прогресса
    tournament_name = data.get('tournament_name', '')
    
    # Переходим к следующему шагу - правила турнира
    text = f"""✅ **Дата начала турнира установлена**

📝 **Шаг 7 из 8: Правила турнира**

**Турнир:** {tournament_name}

📋 Введите правила турнира (необязательно):

▪️ **Текстом:** Максимум 2000 символов
▪️ **Файлом:** Загрузите документ с регламентом
▪️ Описывает правила игры, штрафы, призы
▪️ Можно пропустить, нажав "Пропустить"

**Пример:** Запрещается использование читов. За нарушения - дисквалификация."""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="📎 Загрузить файл регламента",
                callback_data="admin:upload_rules_file"
            )
        ],
        [
            InlineKeyboardButton(
                text="⏩ Пропустить правила",
                callback_data="admin:skip_rules"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к дате турнира",
                callback_data="admin:edit_tournament_start"
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
    await state.set_state(AdminStates.creating_tournament_rules)


@router.callback_query(F.data == "admin:upload_rules_file")
async def upload_rules_file(callback: CallbackQuery, state: FSMContext):
    """Переход к загрузке файла правил"""
    text = """📎 **Загрузка файла регламента**

Отправьте документ с правилами турнира:

▪️ **Поддерживаемые форматы:** PDF, DOC, DOCX, TXT
▪️ **Максимальный размер:** 20 МБ
▪️ Файл будет доступен всем участникам турнира

После загрузки вы сможете добавить краткое описание правил."""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="✏️ Ввести текстом",
                callback_data="admin:enter_rules_text"
            )
        ],
        [
            InlineKeyboardButton(
                text="⏩ Пропустить правила",
                callback_data="admin:skip_rules"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к дате турнира",
                callback_data="admin:edit_tournament_start"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_rules_file)
    await callback.answer()


@router.callback_query(F.data == "admin:enter_rules_text")
async def enter_rules_text(callback: CallbackQuery, state: FSMContext):
    """Возврат к вводу правил текстом"""
    # Получаем данные и возвращаемся к предыдущему шагу
    data = await state.get_data()
    tournament_name = data.get('tournament_name', '')
    
    text = f"""✅ **Дата начала турнира установлена**

📝 **Шаг 7 из 8: Правила турнира**

**Турнир:** {tournament_name}

📋 Введите правила турнира текстом:

▪️ Максимум 2000 символов
▪️ Описывает правила игры, штрафы, призы

**Пример:** Запрещается использование читов. За нарушения - дисквалификация."""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="📎 Загрузить файлом",
                callback_data="admin:upload_rules_file"
            )
        ],
        [
            InlineKeyboardButton(
                text="⏩ Пропустить правила",
                callback_data="admin:skip_rules"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к дате турнира",
                callback_data="admin:edit_tournament_start"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_rules)
    await callback.answer()


@router.message(StateFilter(AdminStates.creating_tournament_rules_file))
async def process_rules_file(message: Message, state: FSMContext):
    """Обработка загруженного файла правил"""
    if not message.document:
        await message.answer("❌ Пожалуйста, отправьте документ с правилами или используйте кнопки ниже.")
        return
    
    document = message.document
    
    # Проверяем размер файла (20 МБ = 20 * 1024 * 1024 байт)
    if document.file_size > 20 * 1024 * 1024:
        await message.answer("❌ Файл слишком большой. Максимальный размер: 20 МБ.")
        return
    
    # Проверяем формат файла
    allowed_mime_types = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    ]
    
    allowed_extensions = ['.pdf', '.doc', '.docx', '.txt']
    
    file_extension = document.file_name.lower()[-4:] if document.file_name else ''
    
    if (document.mime_type not in allowed_mime_types and 
        not any(file_extension.endswith(ext) for ext in allowed_extensions)):
        await message.answer("❌ Неподдерживаемый формат файла. Используйте: PDF, DOC, DOCX, TXT")
        return
    
    try:
        # Сохраняем информацию о файле в состояние
        await state.update_data(
            tournament_rules_file_id=document.file_id,
            tournament_rules_file_name=document.file_name,
            tournament_rules_file_size=document.file_size
        )
        
        # Предлагаем добавить краткое описание
        text = f"""✅ **Файл регламента загружен!**

📎 **Файл:** {document.file_name}
📏 **Размер:** {document.file_size // 1024} КБ

Теперь введите краткое описание правил (необязательно):

▪️ Максимум 500 символов
▪️ Краткая выжимка основных правил
▪️ Будет показана вместе со ссылкой на файл

**Пример:** Турнир 5v5, запрещены читы, призовой фонд 50000 сом."""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⏩ Оставить только файл",
                    callback_data="admin:skip_rules_description"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Загрузить другой файл",
                    callback_data="admin:upload_rules_file"
                )
            ]
        ]
        
        await message.answer(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(AdminStates.creating_tournament_rules)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки файла правил: {e}")
        await message.answer("❌ Ошибка загрузки файла. Попробуйте еще раз.")


@router.callback_query(F.data == "admin:skip_rules_description")
async def skip_rules_description(callback: CallbackQuery, state: FSMContext):
    """Пропуск описания правил при загруженном файле"""
    await state.update_data(tournament_rules="")
    await show_tournament_confirmation(callback, state)


@router.callback_query(F.data == "admin:skip_rules")
async def skip_tournament_rules(callback: CallbackQuery, state: FSMContext):
    """Пропуск ввода правил турнира"""
    await state.update_data(
        tournament_rules="",
        tournament_rules_file_id="",
        tournament_rules_file_name="",
        tournament_rules_file_size=0
    )
    await show_required_channels_prompt(callback, state)


@router.message(StateFilter(AdminStates.creating_tournament_rules))
async def process_tournament_rules(message: Message, state: FSMContext):
    """Обработка ввода правил турнира"""
    if not message.text:
        await message.answer("❌ Пожалуйста, введите правила турнира или нажмите 'Пропустить'.")
        return
    
    rules = message.text.strip()
    
    # Проверяем длину в зависимости от наличия файла
    data = await state.get_data()
    has_file = bool(data.get('tournament_rules_file_id'))
    
    max_length = 500 if has_file else 2000
    
    if len(rules) > max_length:
        await message.answer(f"❌ Описание слишком длинное (максимум {max_length} символов).\n\nПопробуйте сократить:")
        return
    
    # Сохраняем правила в состояние
    await state.update_data(tournament_rules=rules)
    
    # Переходим к обязательным каналам
    await show_required_channels_prompt_as_message(message, state)


# ========== ОБЯЗАТЕЛЬНЫЕ КАНАЛЫ ==========

async def show_required_channels_prompt(callback: CallbackQuery, state: FSMContext):
    """Показ запроса на добавление обязательных каналов (через callback)"""
    data = await state.get_data()
    channels = data.get('required_channels', [])
    
    if channels:
        channels_list = "\n".join([f"• @{ch}" for ch in channels])
        text = f"""📢 **Обязательные каналы** ({len(channels)})

**Текущие каналы:**
{channels_list}

Добавьте username канала (без @) или пропустите этот шаг.

**Формат:** channelname

**Пример:** enasgame_official

Пользователи должны быть подписаны на эти каналы для регистрации команды."""
    else:
        text = """📢 **Обязательные каналы** (опционально)

Вы можете добавить обязательные каналы для подписки.

Пользователи должны быть подписаны на эти каналы для регистрации команды.

**Формат:** channelname (без @)

**Пример:** enasgame_official

Или пропустите этот шаг."""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="🗑️ Очистить список" if channels else "⏭️ Пропустить",
                callback_data="admin:skip_channels" if not channels else "admin:clear_channels"
            )
        ]
    ]
    
    if channels:
        keyboard.insert(0, [
            InlineKeyboardButton(
                text="✅ Завершить добавление",
                callback_data="admin:finish_channels"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="❌ Отменить создание",
            callback_data="admin:cancel_tournament_creation"
        )
    ])
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_required_channels)
    await callback.answer()


async def show_required_channels_prompt_as_message(message: Message, state: FSMContext):
    """Показ запроса на добавление обязательных каналов (через message)"""
    data = await state.get_data()
    channels = data.get('required_channels', [])
    
    if channels:
        channels_list = "\n".join([f"• @{ch}" for ch in channels])
        text = f"""📢 **Обязательные каналы** ({len(channels)})

**Текущие каналы:**
{channels_list}

Добавьте username канала (без @) или пропустите этот шаг.

**Формат:** channelname

**Пример:** enasgame_official"""
    else:
        text = """📢 **Обязательные каналы** (опционально)

Вы можете добавить обязательные каналы для подписки.

Пользователи должны быть подписаны на эти каналы для регистрации команды.

**Формат:** channelname (без @)

**Пример:** enasgame_official

Или пропустите этот шаг."""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="🗑️ Очистить список" if channels else "⏭️ Пропустить",
                callback_data="admin:skip_channels" if not channels else "admin:clear_channels"
            )
        ]
    ]
    
    if channels:
        keyboard.insert(0, [
            InlineKeyboardButton(
                text="✅ Завершить добавление",
                callback_data="admin:finish_channels"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="❌ Отменить создание",
            callback_data="admin:cancel_tournament_creation"
        )
    ])
    
    await message.answer(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_required_channels)


@router.callback_query(F.data == "admin:skip_channels")
async def skip_required_channels(callback: CallbackQuery, state: FSMContext):
    """Пропуск обязательных каналов"""
    await state.update_data(required_channels=[])
    await show_tournament_confirmation(callback, state)


@router.callback_query(F.data == "admin:clear_channels")
async def clear_required_channels(callback: CallbackQuery, state: FSMContext):
    """Очистка списка каналов"""
    await state.update_data(required_channels=[])
    await callback.answer("✅ Список очищен")
    await show_required_channels_prompt(callback, state)


@router.callback_query(F.data == "admin:finish_channels")
async def finish_adding_channels(callback: CallbackQuery, state: FSMContext):
    """Завершение добавления каналов"""
    data = await state.get_data()
    channels = data.get('required_channels', [])
    
    if not channels:
        await callback.answer("❌ Добавьте хотя бы один канал или пропустите", show_alert=True)
        return
    
    await show_tournament_confirmation(callback, state)


@router.message(StateFilter(AdminStates.creating_tournament_required_channels))
async def process_required_channel(message: Message, state: FSMContext):
    """Обработка добавления обязательного канала"""
    if not message.text:
        await message.answer("❌ Пожалуйста, введите username канала.")
        return
    
    channel_username = message.text.strip().replace("@", "")
    
    # Валидация
    if len(channel_username) < 5:
        await message.answer("❌ Username канала слишком короткий (минимум 5 символов).")
        return
    
    if len(channel_username) > 32:
        await message.answer("❌ Username канала слишком длинный (максимум 32 символа).")
        return
    
    # Проверяем что username содержит только разрешенные символы
    import re
    if not re.match(r'^[a-zA-Z0-9_]+$', channel_username):
        await message.answer("❌ Username может содержать только буквы, цифры и подчеркивания.")
        return
    
    try:
        data = await state.get_data()
        channels = data.get('required_channels', [])
        
        # Проверка дубликатов
        if channel_username.lower() in [ch.lower() for ch in channels]:
            await message.answer(f"❌ Канал @{channel_username} уже добавлен.")
            return
        
        # Добавляем канал
        channels.append(channel_username)
        await state.update_data(required_channels=channels)
        
        channels_list = "\n".join([f"• @{ch}" for ch in channels])
        
        text = f"""✅ **Канал добавлен!**

**Обязательные каналы** ({len(channels)}):
{channels_list}

Добавьте ещё каналы или завершите."""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Завершить добавление",
                    callback_data="admin:finish_channels"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Очистить список",
                    callback_data="admin:clear_channels"
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
        
    except Exception as e:
        logger.error(f"Ошибка добавления канала: {e}")
        await message.answer("❌ Ошибка добавления канала.")


async def show_tournament_confirmation(callback: CallbackQuery, state: FSMContext):
    """Показ подтверждения турнира через callback"""
    data = await state.get_data()
    
    # Форматируем данные для отображения
    reg_start = datetime.fromisoformat(data.get('registration_start_date', ''))
    reg_end = datetime.fromisoformat(data.get('registration_end_date', ''))
    tournament_start = datetime.fromisoformat(data.get('tournament_start_date', ''))
    
    # Форматируем обязательные каналы
    required_channels = data.get('required_channels', [])
    channels_text = ""
    if required_channels:
        channels_list = "\n".join([f"• @{ch}" for ch in required_channels])
        channels_text = f"\n\n**📢 Обязательные каналы** ({len(required_channels)}):\n{channels_list}"
    
    text = f"""📋 **Подтверждение создания турнира**

**📝 Название:** {data.get('tournament_name', '')}
**📄 Описание:** {data.get('tournament_description', '')[:100]}{"..." if len(data.get('tournament_description', '')) > 100 else ""}
**🎮 Игра:** {data.get('tournament_game_name', '')}
**🏆 Формат:** {data.get('tournament_format_display', '')}
**👥 Команд:** {data.get('tournament_max_teams', 0)}

**📅 Даты (UTC):**
🟢 Начало регистрации: {format_datetime_for_user(reg_start, 'UTC')}
🔴 Окончание регистрации: {format_datetime_for_user(reg_end, 'UTC')}
🏁 Начало турнира: {format_datetime_for_user(tournament_start, 'UTC')}

**📋 Правила:** {"Не указаны" if not data.get('tournament_rules', '') else f"{data.get('tournament_rules', '')[:50]}..."}{channels_text}

⚠️ После создания турнир будет автоматически создан в Challonge"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Создать турнир",
                callback_data="admin:confirm_create_tournament"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Редактировать",
                callback_data="admin:edit_tournament_data"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_confirmation)
    await callback.answer()


async def show_tournament_confirmation_as_message(message: Message, state: FSMContext):
    """Показ подтверждения турнира через message"""
    data = await state.get_data()
    
    # Форматируем данные для отображения
    reg_start = datetime.fromisoformat(data.get('registration_start_date', ''))
    reg_end = datetime.fromisoformat(data.get('registration_end_date', ''))
    tournament_start = datetime.fromisoformat(data.get('tournament_start_date', ''))
    
    # Форматируем обязательные каналы
    required_channels = data.get('required_channels', [])
    channels_text = ""
    if required_channels:
        channels_list = "\n".join([f"• @{ch}" for ch in required_channels])
        channels_text = f"\n\n**📢 Обязательные каналы** ({len(required_channels)}):\n{channels_list}"
    
    text = f"""📋 **Подтверждение создания турнира**

**📝 Название:** {data.get('tournament_name', '')}
**📄 Описание:** {data.get('tournament_description', '')[:100]}{"..." if len(data.get('tournament_description', '')) > 100 else ""}
**🎮 Игра:** {data.get('tournament_game_name', '')}
**🏆 Формат:** {data.get('tournament_format_display', '')}
**👥 Максимум команд:** {data.get('tournament_max_teams', '')}

**📅 Даты (UTC):**
🟢 Начало регистрации: {format_datetime_for_user(reg_start, 'UTC')}
🔴 Окончание регистрации: {format_datetime_for_user(reg_end, 'UTC')}
🏁 Начало турнира: {format_datetime_for_user(tournament_start, 'UTC')}

**📋 Правила:** {"Не указаны" if not data.get('tournament_rules', '') else f"{data.get('tournament_rules', '')[:50]}..."}{channels_text}

⚠️ После создания турнир будет автоматически создан в Challonge"""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Создать турнир",
                callback_data="admin:confirm_create_tournament"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Редактировать",
                callback_data="admin:edit_tournament_data"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="admin:cancel_tournament_creation"
            )
        ]
    ]
    
    await message.answer(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AdminStates.creating_tournament_confirmation)


# Обработчик финального создания турнира с интеграцией Challonge
@router.callback_query(F.data == "admin:confirm_create_tournament")
async def confirm_create_tournament(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и создание турнира в БД и Challonge"""
    data = await state.get_data()
    
    # Показываем сообщение о начале создания
    text = "🏗️ **Создание турнира...**\n\nПожалуйста, подождите. Создается турнир в системе и на Challonge."
    
    await safe_edit_message(callback.message, text, parse_mode="Markdown")
    await callback.answer()
    
    try:
        from database.repositories import TournamentRepository
        from integrations.challonge_api import ChallongeAPI
        from config.settings import settings
        
        # Создаем турнир в базе данных
        # Преобразуем формат в enum
        format_mapping = {
            'single': TournamentFormat.SINGLE_ELIMINATION,
            'double': TournamentFormat.DOUBLE_ELIMINATION,
            'round_robin': TournamentFormat.ROUND_ROBIN,
            'group_playoffs': TournamentFormat.GROUP_STAGE_PLAYOFFS
        }
        
        tournament_format = format_mapping.get(
            data.get('tournament_format'), 
            TournamentFormat.SINGLE_ELIMINATION
        )
        
        # Получаем дату начала турнира и вычисляем дедлайн редактирования
        tournament_start_datetime = data.get('tournament_start_date')
        if isinstance(tournament_start_datetime, str):
            # Если дата сохранена как строка, парсим её
            tournament_start_datetime = datetime.fromisoformat(tournament_start_datetime)
        
        # Вычисляем дедлайн редактирования (за 1 час до начала)
        edit_deadline = tournament_start_datetime - timedelta(hours=1)
        
        # Аналогично обрабатываем остальные даты
        reg_start = data.get('registration_start_date')
        if isinstance(reg_start, str):
            reg_start = datetime.fromisoformat(reg_start)
            
        reg_end = data.get('registration_end_date')
        if isinstance(reg_end, str):
            reg_end = datetime.fromisoformat(reg_end)
        
        tournament = await TournamentRepository.create_tournament(
            game_id=data.get('tournament_game_id'),
            name=data.get('tournament_name'),
            description=data.get('tournament_description', ''),
            format_type=tournament_format,
            max_teams=data.get('tournament_max_teams'),
            registration_start=reg_start,
            registration_end=reg_end,
            tournament_start=tournament_start_datetime,
            edit_deadline=edit_deadline,
            rules_text=data.get('tournament_rules', ''),
            required_channels=data.get('required_channels', []),  # Сохраняем обязательные каналы
            created_by=callback.from_user.id,  # ID админа
            rules_file_id=data.get('tournament_rules_file_id'),
            rules_file_name=data.get('tournament_rules_file_name')
        )
        
        # Создаем турнир в Challonge
        if not settings.challonge_client_id or not settings.challonge_client_secret:
            raise Exception("Challonge API не настроен. Проверьте CHALLONGE_CLIENT_ID и CHALLONGE_CLIENT_SECRET в .env файле")
        
        challonge = ChallongeAPI(settings.challonge_client_id, settings.challonge_client_secret, settings.challonge_username)
        
        # Определяем формат для Challonge
        challonge_format = {
            'single': 'single elimination',
            'double': 'double elimination', 
            'round_robin': 'round robin'
        }.get(data.get('tournament_format'), 'single elimination')
        
        challonge_tournament = await challonge.create_tournament(
            name=data.get('tournament_name'),
            tournament_type=challonge_format,
            description=data.get('tournament_description', '')
        )
        
        # Сохраняем ID турнира Challonge в базе
        await TournamentRepository.update_challonge_id(tournament.id, challonge_tournament['id'])
        
        # Успешное создание
        success_text = f"""✅ **Турнир успешно создан!**

**📝 Название:** {data.get('tournament_name')}
**🆔 ID в системе:** {tournament.id}
**🔗 Challonge ID:** {challonge_tournament['id']}
**📱 URL:** {challonge_tournament.get('full_challonge_url', 'N/A')}

Турнир готов к регистрации участников!"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🏆 Управление турнирами",
                    callback_data="admin:tournaments"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, success_text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        await state.clear()
        logger.info(f"Турнир создан: ID={tournament.id}, Challonge ID={challonge_tournament['id']}")
        
    except Exception as e:
        logger.error(f"Ошибка создания турнира: {e}")
        
        error_text = f"""❌ **Ошибка создания турнира**

Произошла ошибка при создании турнира:
{str(e)[:200]}

Попробуйте создать турнир заново или обратитесь к разработчику."""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔄 Попробовать снова",
                    callback_data="admin:create_tournament"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 К турнирам",
                    callback_data="admin:tournaments"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, error_text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )