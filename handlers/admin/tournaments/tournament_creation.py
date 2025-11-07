"""
Создание турниров
"""
import logging
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.repositories import TournamentRepository, GameRepository
from utils.message_utils import safe_edit_message, safe_send_message
from ..states import AdminStates
from ..keyboards import get_game_selection_keyboard, get_tournament_format_keyboard, get_confirm_tournament_creation_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "admin:create_tournament")
async def create_tournament_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания турнира"""
    await state.clear()
    
    text = """🏆 **Создание турнира**

📋 **Введите название турнира:**

*Название должно быть понятным и привлекательным для участников*"""
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown"
    )
    
    await state.set_state(AdminStates.creating_tournament_name)
    await callback.answer()


@router.message(AdminStates.creating_tournament_name)
async def process_tournament_name(message: Message, state: FSMContext):
    """Обработка названия турнира"""
    tournament_name = message.text.strip()
    
    if len(tournament_name) < 3:
        await safe_send_message(
            message, 
            "❌ **Название слишком короткое**\n\nВведите название длиной минимум 3 символа:",
            parse_mode="Markdown"
        )
        return
    
    if len(tournament_name) > 100:
        await safe_send_message(
            message,
            "❌ **Название слишком длинное**\n\nМаксимальная длина: 100 символов\nТекущая длина: " + str(len(tournament_name)),
            parse_mode="Markdown"
        )
        return
    
    # Проверяем уникальность названия
    try:
        existing_tournament = await TournamentRepository.get_by_name(tournament_name)
        if existing_tournament:
            await safe_send_message(
                message,
                "❌ **Турнир с таким названием уже существует**\n\nВведите другое название:",
                parse_mode="Markdown"
            )
            return
    except Exception as e:
        logger.error(f"Ошибка проверки уникальности названия турнира: {e}")
    
    # Сохраняем название
    await state.update_data(tournament_name=tournament_name)
    
    text = """📝 **Введите описание турнира:**

*Опишите правила, призы, особенности турнира*
*Можно пропустить, нажав /skip*"""
    
    await safe_send_message(
        message, text, parse_mode="Markdown"
    )
    
    await state.set_state(AdminStates.creating_tournament_description)


@router.message(AdminStates.creating_tournament_description)
async def process_tournament_description(message: Message, state: FSMContext):
    """Обработка описания турнира"""
    # Проверяем, что это текстовое сообщение
    if not message.text:
        await safe_send_message(
            message,
            "❌ **Ожидается текстовое сообщение**\n\nВведите описание турнира или /skip для пропуска:",
            parse_mode="Markdown"
        )
        return
    
    if message.text.strip().lower() == '/skip':
        tournament_description = None
    else:
        tournament_description = message.text.strip()
        
        if len(tournament_description) > 1000:
            await safe_send_message(
                message,
                "❌ **Описание слишком длинное**\n\nМаксимальная длина: 1000 символов\nТекущая длина: " + str(len(tournament_description)),
                parse_mode="Markdown"
            )
            return
    
    # Сохраняем описание
    await state.update_data(tournament_description=tournament_description)
    
    # Предлагаем загрузить файл правил
    text = """📄 **Загрузите файл правил турнира (опционально):**

*Поддерживаемые форматы: PDF, DOC, DOCX*
*Максимальный размер: 20 МБ*

Вы можете:
▪️ Отправить файл документа
▪️ Пропустить этап, нажав /skip"""
    
    await safe_send_message(
        message, text, parse_mode="Markdown"
    )
    
    await state.set_state(AdminStates.creating_tournament_rules_file)


@router.message(AdminStates.creating_tournament_rules_file)
async def process_tournament_rules_file(message: Message, state: FSMContext):
    """Обработка загрузки файла правил турнира"""
    # Проверка на пропуск
    if message.text and message.text.strip().lower() == '/skip':
        await state.update_data(tournament_rules_file_id=None, tournament_rules_file_name=None)
        await proceed_to_game_selection(message, state)
        return
    
    # Проверяем наличие документа
    if not message.document:
        await safe_send_message(
            message,
            "❌ **Ожидается файл документа**\n\nОтправьте PDF, DOC или DOCX файл, либо пропустите командой /skip",
            parse_mode="Markdown"
        )
        return
    
    document = message.document
    
    # Проверка типа файла
    allowed_mime_types = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    
    if document.mime_type not in allowed_mime_types:
        await safe_send_message(
            message,
            "❌ **Неподдерживаемый формат файла**\n\nПринимаются только PDF, DOC и DOCX файлы",
            parse_mode="Markdown"
        )
        return
    
    # Проверка размера файла (20 МБ)
    max_size = 20 * 1024 * 1024  # 20 MB
    if document.file_size > max_size:
        await safe_send_message(
            message,
            f"❌ **Файл слишком большой**\n\nМаксимальный размер: 20 МБ\nВаш файл: {document.file_size / 1024 / 1024:.1f} МБ",
            parse_mode="Markdown"
        )
        return
    
    # Сохраняем информацию о файле
    await state.update_data(
        tournament_rules_file_id=document.file_id,
        tournament_rules_file_name=document.file_name
    )
    
    await safe_send_message(
        message,
        f"✅ **Файл правил сохранен:** {document.file_name}",
        parse_mode="Markdown"
    )
    
    # Переходим к загрузке логотипа
    await proceed_to_logo_upload(message, state)


async def proceed_to_logo_upload(message: Message, state: FSMContext):
    """Переход к загрузке логотипа турнира"""
    text = """🖼️ **Загрузите логотип турнира (опционально):**

*Поддерживаемые форматы: JPG, JPEG, PNG*
*Максимальный размер: 5 МБ*
*Рекомендуемое разрешение: 512x512 px*

Вы можете:
▪️ Отправить изображение
▪️ Пропустить этап, нажав /skip"""
    
    await safe_send_message(
        message, text, parse_mode="Markdown"
    )
    
    await state.set_state(AdminStates.creating_tournament_logo)


@router.message(AdminStates.creating_tournament_logo)
async def process_tournament_logo(message: Message, state: FSMContext):
    """Обработка загрузки логотипа турнира"""
    # Проверка на пропуск
    if message.text and message.text.strip().lower() == '/skip':
        await state.update_data(tournament_logo_file_id=None)
        await proceed_to_game_selection(message, state)
        return
    
    # Проверяем наличие фото
    if not message.photo:
        await safe_send_message(
            message,
            "❌ **Ожидается изображение**\n\nОтправьте фото (JPG/PNG), либо пропустите командой /skip",
            parse_mode="Markdown"
        )
        return
    
    # Берем самое большое фото
    photo = message.photo[-1]
    
    # Проверка размера файла (5 МБ)
    max_size = 5 * 1024 * 1024  # 5 MB
    if photo.file_size and photo.file_size > max_size:
        await safe_send_message(
            message,
            f"❌ **Изображение слишком большое**\n\nМаксимальный размер: 5 МБ\nВаше изображение: {photo.file_size / 1024 / 1024:.1f} МБ",
            parse_mode="Markdown"
        )
        return
    
    # Сохраняем file_id логотипа
    await state.update_data(tournament_logo_file_id=photo.file_id)
    
    await safe_send_message(
        message,
        "✅ **Логотип турнира сохранен**",
        parse_mode="Markdown"
    )
    
    # Переходим к выбору игры
    await proceed_to_game_selection(message, state)


async def proceed_to_game_selection(message: Message, state: FSMContext):
    """Переход к выбору игры для турнира"""
    try:
        games = await GameRepository.get_all_games()
        
        if not games:
            await safe_send_message(
                message,
                "❌ **Нет доступных игр**\n\nСначала добавьте игры в систему.",
                parse_mode="Markdown"
            )
            await state.clear()
            return
        
        text = """🎮 **Выберите игру для турнира:**"""
        
        await safe_send_message(
            message, text,
            reply_markup=get_game_selection_keyboard(games),
            parse_mode="Markdown"
        )
        
        await state.set_state(AdminStates.creating_tournament_game)
        
    except Exception as e:
        logger.error(f"Ошибка получения списка игр: {e}")
        await safe_send_message(
            message,
            "❌ **Ошибка загрузки игр**\n\nПопробуйте позже.",
            parse_mode="Markdown"
        )
        await state.clear()


@router.callback_query(AdminStates.creating_tournament_game, F.data.startswith("select_game_"))
async def process_tournament_game(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора игры"""
    try:
        game_id = int(callback.data.split("_")[-1])
        
        # Получаем информацию об игре
        game = await GameRepository.get_by_id(game_id)
        
        if not game:
            await callback.answer("❌ Игра не найдена", show_alert=True)
            return
        
        # Сохраняем выбранную игру
        await state.update_data(tournament_game_id=game_id)
        
        text = f"""🏆 **Выберите формат турнира:**

🎮 Игра: **{game.name}**

Доступные форматы:"""
        
        await safe_edit_message(
            callback.message, text,
            reply_markup=get_tournament_format_keyboard(),
            parse_mode="Markdown"
        )
        
        await state.set_state(AdminStates.creating_tournament_format)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка обработки выбора игры: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(AdminStates.creating_tournament_format, F.data.startswith("format_"))
async def process_tournament_format(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора формата турнира"""
    tournament_format = callback.data.replace("format_", "")
    
    # Сохраняем формат
    await state.update_data(tournament_format=tournament_format)
    
    format_names = {
        'single_elimination': 'Одиночное исключение',
        'double_elimination': 'Двойное исключение',
        'round_robin': 'Круговая система',
        'swiss': 'Швейцарская система'
    }
    
    text = f"""👥 **Введите максимальное количество команд:**

🏆 Формат: **{format_names.get(tournament_format, tournament_format)}**

*Введите число от 4 до 128*"""
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown"
    )
    
    await state.set_state(AdminStates.creating_tournament_max_teams)
    await callback.answer()


@router.message(AdminStates.creating_tournament_max_teams)
async def process_tournament_max_teams(message: Message, state: FSMContext):
    """Обработка максимального количества команд"""
    try:
        max_teams = int(message.text.strip())
        
        if max_teams < 4:
            await safe_send_message(
                message,
                "❌ **Минимальное количество команд: 4**\n\nВведите корректное число:",
                parse_mode="Markdown"
            )
            return
        
        if max_teams > 128:
            await safe_send_message(
                message,
                "❌ **Максимальное количество команд: 128**\n\nВведите корректное число:",
                parse_mode="Markdown"
            )
            return
        
        # Сохраняем количество команд
        await state.update_data(tournament_max_teams=max_teams)
        
        text = """📅 **Введите дату начала регистрации:**

*Формат: ДД.ММ.ГГГГ ЧЧ:ММ*
*Например: 15.03.2024 10:00*"""
        
        await safe_send_message(
            message, text, parse_mode="Markdown"
        )
        
        await state.set_state(AdminStates.creating_tournament_registration_start)
        
    except ValueError:
        await safe_send_message(
            message,
            "❌ **Некорректное число**\n\nВведите число от 4 до 128:",
            parse_mode="Markdown"
        )


@router.message(AdminStates.creating_tournament_registration_start)
async def process_tournament_registration_start(message: Message, state: FSMContext):
    """Обработка даты начала регистрации"""
    try:
        # Парсим дату
        registration_start = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
        registration_start = registration_start.replace(tzinfo=timezone.utc)
        
        # Проверяем, что дата в будущем
        if registration_start <= datetime.now(timezone.utc):
            await safe_send_message(
                message,
                "❌ **Дата начала регистрации должна быть в будущем**\n\nВведите корректную дату:",
                parse_mode="Markdown"
            )
            return
        
        # Сохраняем дату
        await state.update_data(tournament_registration_start=registration_start)
        
        text = """📅 **Введите дату окончания регистрации:**

*Формат: ДД.ММ.ГГГГ ЧЧ:ММ*
*Должна быть позже начала регистрации*"""
        
        await safe_send_message(
            message, text, parse_mode="Markdown"
        )
        
        await state.set_state(AdminStates.creating_tournament_registration_end)
        
    except ValueError:
        await safe_send_message(
            message,
            "❌ **Некорректный формат даты**\n\nИспользуйте формат: ДД.ММ.ГГГГ ЧЧ:ММ",
            parse_mode="Markdown"
        )


@router.message(AdminStates.creating_tournament_registration_end)
async def process_tournament_registration_end(message: Message, state: FSMContext):
    """Обработка даты окончания регистрации"""
    try:
        # Парсим дату
        registration_end = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
        registration_end = registration_end.replace(tzinfo=timezone.utc)
        
        # Получаем дату начала регистрации
        data = await state.get_data()
        registration_start = data['tournament_registration_start']
        
        # Проверяем корректность даты
        if registration_end <= registration_start:
            await safe_send_message(
                message,
                "❌ **Дата окончания должна быть позже начала регистрации**\n\nВведите корректную дату:",
                parse_mode="Markdown"
            )
            return
        
        # Сохраняем дату
        await state.update_data(tournament_registration_end=registration_end)
        
        text = """📅 **Введите дату начала турнира:**

*Формат: ДД.ММ.ГГГГ ЧЧ:ММ*
*Должна быть после окончания регистрации*"""
        
        await safe_send_message(
            message, text, parse_mode="Markdown"
        )
        
        await state.set_state(AdminStates.creating_tournament_start_date)
        
    except ValueError:
        await safe_send_message(
            message,
            "❌ **Некорректный формат даты**\n\nИспользуйте формат: ДД.ММ.ГГГГ ЧЧ:ММ",
            parse_mode="Markdown"
        )


@router.message(AdminStates.creating_tournament_start_date)
async def process_tournament_start_date(message: Message, state: FSMContext):
    """Обработка даты начала турнира"""
    try:
        # Парсим дату
        tournament_start = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
        tournament_start = tournament_start.replace(tzinfo=timezone.utc)
        
        # Получаем дату окончания регистрации
        data = await state.get_data()
        registration_end = data['tournament_registration_end']
        
        # Проверяем корректность даты
        if tournament_start <= registration_end:
            await safe_send_message(
                message,
                "❌ **Дата начала турнира должна быть после окончания регистрации**\n\nВведите корректную дату:",
                parse_mode="Markdown"
            )
            return
        
        # Сохраняем дату и показываем подтверждение
        await state.update_data(tournament_start_date=tournament_start)
        await show_tournament_confirmation(message, state)
        
    except ValueError:
        await safe_send_message(
            message,
            "❌ **Некорректный формат даты**\n\nИспользуйте формат: ДД.ММ.ГГГГ ЧЧ:ММ",
            parse_mode="Markdown"
        )


async def show_tournament_confirmation(message: Message, state: FSMContext):
    """Показать подтверждение создания турнира"""
    try:
        data = await state.get_data()
        
        # Получаем информацию об игре
        game = await GameRepository.get_by_id(data['tournament_game_id'])
        
        format_names = {
            'single_elimination': 'Одиночное исключение',
            'double_elimination': 'Двойное исключение', 
            'round_robin': 'Круговая система',
            'swiss': 'Швейцарская система'
        }
        
        # Информация о файле правил
        rules_file_info = ""
        if data.get('tournament_rules_file_id'):
            rules_file_info = f"\n📄 **Файл правил:** {data.get('tournament_rules_file_name', 'Загружен')}"
        
        # Информация о логотипе
        logo_info = ""
        if data.get('tournament_logo_file_id'):
            logo_info = "\n🖼️ **Логотип:** Загружен"
        
        text = f"""✅ **Подтверждение создания турнира**

🏆 **Название:** {data['tournament_name']}
📝 **Описание:** {data.get('tournament_description') or 'Не указано'}
🎮 **Игра:** {game.name if game else 'N/A'}
🏆 **Формат:** {format_names.get(data['tournament_format'], data['tournament_format'])}
👥 **Макс. команд:** {data['tournament_max_teams']}{rules_file_info}{logo_info}

📅 **Даты:**
📋 Регистрация: {data['tournament_registration_start'].strftime('%d.%m.%Y %H:%M')} - {data['tournament_registration_end'].strftime('%d.%m.%Y %H:%M')}
🏁 Начало: {data['tournament_start_date'].strftime('%d.%m.%Y %H:%M')}

**Все данные корректны?**"""
        
        # Если есть логотип, отправляем его вместе с сообщением
        if data.get('tournament_logo_file_id'):
            try:
                await message.bot.send_photo(
                    chat_id=message.chat.id,
                    photo=data['tournament_logo_file_id'],
                    caption=text,
                    reply_markup=get_confirm_tournament_creation_keyboard(),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки логотипа: {e}")
                # Если не удалось отправить с логотипом, отправляем без него
                await safe_send_message(
                    message, text,
                    reply_markup=get_confirm_tournament_creation_keyboard(),
                    parse_mode="Markdown"
                )
        else:
            await safe_send_message(
                message, text,
                reply_markup=get_confirm_tournament_creation_keyboard(),
                parse_mode="Markdown"
            )
        
        await state.set_state(AdminStates.confirming_tournament_creation)
        
    except Exception as e:
        logger.error(f"Ошибка показа подтверждения турнира: {e}")
        await safe_send_message(
            message,
            "❌ **Ошибка**\n\nНе удалось показать данные турнира.",
            parse_mode="Markdown"
        )
        await state.clear()


@router.callback_query(AdminStates.confirming_tournament_creation, F.data == "confirm_create_tournament")
async def confirm_create_tournament(callback: CallbackQuery, state: FSMContext):
    """Подтверждение создания турнира"""
    try:
        data = await state.get_data()
        
        # Логируем данные для отладки
        logger.info(f"Создание турнира с данными: {data}")
        
        # Вычисляем edit_deadline (за 1 день до начала турнира)
        from datetime import timedelta
        tournament_start = data['tournament_start_date']
        edit_deadline = tournament_start - timedelta(days=1)
        
        # Создаем турнир с правильными параметрами
        from database.models import TournamentFormat
        
        logo_file_id = data.get('tournament_logo_file_id')
        rules_file_id = data.get('tournament_rules_file_id')
        rules_file_name = data.get('tournament_rules_file_name')
        
        logger.info(f"Файлы: logo={logo_file_id}, rules={rules_file_id}, rules_name={rules_file_name}")
        
        tournament = await TournamentRepository.create_tournament(
            game_id=data['tournament_game_id'],
            name=data['tournament_name'],
            description=data.get('tournament_description') or '',
            format_type=TournamentFormat[data['tournament_format'].upper()],
            max_teams=data['tournament_max_teams'],
            registration_start=data['tournament_registration_start'],
            registration_end=data['tournament_registration_end'],
            tournament_start=tournament_start,
            edit_deadline=edit_deadline,
            rules_text='',
            required_channels=[],
            created_by=callback.from_user.id,
            logo_file_id=logo_file_id,
            rules_file_id=rules_file_id,
            rules_file_name=rules_file_name
        )
        
        logger.info(f"Турнир создан: {tournament}")
        logger.info(f"Турнир логотип: {tournament.logo_file_id if tournament else 'None'}")
        logger.info(f"Турнир правила: {tournament.rules_file_id if tournament else 'None'}")
        
        if tournament:
            # Формируем сообщение с информацией
            rules_info = ""
            if tournament.rules_file_id:
                rules_info = f"\n📄 Файл правил: {tournament.rules_file_name}"
            
            logo_info = ""
            if tournament.logo_file_id:
                logo_info = "\n🖼️ Логотип: Загружен"
            
            text = f"""✅ **Турнир успешно создан!**

🏆 **{tournament.name}** (ID: {tournament.id}){rules_info}{logo_info}

Турнир добавлен в систему и готов к регистрации участников."""
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown"
            )
            await callback.answer("✅ Турнир создан!", show_alert=True)
        else:
            await callback.answer("❌ Ошибка создания турнира", show_alert=True)
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка создания турнира: {e}")
        await callback.answer("❌ Ошибка создания турнира", show_alert=True)
        await state.clear()


@router.callback_query(AdminStates.confirming_tournament_creation, F.data == "cancel_create_tournament")
async def cancel_create_tournament(callback: CallbackQuery, state: FSMContext):
    """Отмена создания турнира"""
    await safe_edit_message(
        callback.message,
        "❌ **Создание турнира отменено**\n\nВсе данные очищены.",
        parse_mode="Markdown"
    )
    await callback.answer("Создание отменено")
    await state.clear()