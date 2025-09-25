"""
Хендлеры для управления пользователями
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database.repositories import UserRepository
from utils.message_utils import safe_edit_message
from utils.admin_commands import set_admin_commands, remove_admin_commands
from .states import AdminStates
from .keyboards import get_user_management_keyboard, get_user_action_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "admin:users")
async def user_management_menu(callback: CallbackQuery, state: FSMContext):
    """Меню управления пользователями"""
    await state.clear()

    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    language = user.language if user else "ru"
    
    # Получаем статистику
    total_users = await UserRepository.get_total_count()
    admin_users = await UserRepository.get_admins()
    blocked_users_list = await UserRepository.get_blocked_users()
    blocked_count = len(blocked_users_list)
    
    text = """👤 Управление пользователями

📊 Статистика:
👥 Всего пользователей: {total}
👑 Администраторов: {admins}
🚫 Заблокированных: {blocked}

Выберите действие:""".format(
        total=total_users,
        admins=len(admin_users),
        blocked=blocked_count
    )
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=get_user_management_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "admin:search_user")
async def start_user_search(callback: CallbackQuery, state: FSMContext):
    """Начало поиска пользователя"""
    
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    language = user.language if user else "ru"
    
    text = """🔍 Поиск пользователя

Введите для поиска:
• Username (без @)
• Telegram ID
• Имя пользователя

Например: username или 123456789"""
    
    await safe_edit_message(callback.message, text, parse_mode="Markdown")
    await state.set_state(AdminStates.selecting_user_to_manage)
    await callback.answer()

@router.message(StateFilter(AdminStates.selecting_user_to_manage))
async def process_user_search(message: Message, state: FSMContext):
    """Обработка поиска пользователя"""
    search_query = message.text.strip()

    found_users = []
    
    try:
        # Поиск по Telegram ID
        if search_query.isdigit():
            user = await UserRepository.get_by_telegram_id(int(search_query))
            if user:
                found_users.append(user)
        
        # Поиск по username
        if search_query.startswith('@'):
            search_query = search_query[1:]
        
        users_by_username = await UserRepository.search_by_username(search_query)
        found_users.extend(users_by_username)
        
        # Поиск по имени
        users_by_name = await UserRepository.search_by_name(search_query)
        found_users.extend(users_by_name)
        
        # Убираем дубликаты
        found_users = list({user.id: user for user in found_users}.values())
        
    except Exception as e:
        logger.error(f"Ошибка поиска пользователей: {e}")
        await message.answer("❌ Ошибка поиска. Попробуйте снова.")
        return
    
    if not found_users:
        text = """❌ Пользователи не найдены

По запросу "{query}" пользователи не найдены.
Попробуйте другой запрос:""".format(query=search_query)
        
        await message.answer(text, parse_mode="Markdown")
        return
    
    if len(found_users) == 1:
        # Если найден один пользователь, показываем его детали
        await show_user_details(message, found_users[0], state)
    else:
        # Если найдено несколько, сохраняем результаты поиска и показываем с пагинацией
        await state.update_data(search_results=[(user.id, user.telegram_id, user.username, user.full_name) for user in found_users])
        await show_search_results(message, found_users, 0, search_query, state)
    
    await state.clear()

async def show_search_results(message_or_callback, users: list, page: int, query: str, state: FSMContext):
    """Показать результаты поиска с пагинацией"""
    users_per_page = 10
    total_users = len(users)
    total_pages = (total_users + users_per_page - 1) // users_per_page
    
    start_idx = page * users_per_page
    end_idx = min(start_idx + users_per_page, total_users)
    page_users = users[start_idx:end_idx]
    
    text = f"""🔍 Результаты поиска: "{query}"

👥 Найдено: {total_users} пользователей
📄 Страница: {page + 1} из {total_pages}

Выберите пользователя:"""
    
    keyboard = []
    
    # Кнопки с пользователями
    for user in page_users:
        user_info = f"@{user.username}" if user.username else f"ID: {user.telegram_id}"
        full_name = user.full_name[:20] + "..." if len(user.full_name) > 20 else user.full_name
        
        role_emoji = "👑" if user.is_admin else "👤"
        status_emoji = "🚫" if user.is_blocked else "✅"
        
        button_text = f"{role_emoji}{status_emoji} {user_info} - {full_name}"
        
        keyboard.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"admin:user_details_{user.id}"
            )
        ])
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Предыдущая",
                callback_data=f"admin:search_page_{page-1}"
            )
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Следующая", 
                callback_data=f"admin:search_page_{page+1}"
            )
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопка "Новый поиск" и "Назад"
    keyboard.append([
        InlineKeyboardButton(
            text="🔍 Новый поиск",
            callback_data="admin:search_user"
        ),
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="admin:users"
        )
    ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    if hasattr(message_or_callback, 'message'):  # Это callback
        await safe_edit_message(
            message_or_callback.message, text,
            reply_markup=reply_markup
        )
    else:  # Это message
        await message_or_callback.answer(
            text,
            reply_markup=reply_markup
        )

async def show_user_details(message_or_callback, user, state: FSMContext):
    """Показать детали пользователя"""
    # Получаем дополнительную статистику
    
    user_teams_count = await UserRepository.get_user_teams_count(user.id)
    user_tournaments_count = await UserRepository.get_user_tournaments_count(user.id)
    
    user_info = f"@{user.username}" if user.username else "Не указан"
    role = "👑 Администратор" if user.is_admin else "👤 Пользователь"
    status = "🚫 Заблокирован" if user.is_blocked else "✅ Активен"
    
    text = """👤 Информация о пользователе

ID: {telegram_id}
Username: {username}
Имя: {first_name}
Роль: {role}
Статус: {status}
Язык: {language}
Регион: {region}

📊 Статистика:
👥 Команд: {teams}
🏆 Турниров: {tournaments}

📅 Регистрация: {created}
📅 Последняя активность: {last_seen}""".format(
        telegram_id=user.telegram_id,
        username=user_info,
        first_name=user.first_name or "Не указано",
        role=role,
        status=status,
        language=user.language.upper(),
        region=user.region.upper(),
        teams=user_teams_count,
        tournaments=user_tournaments_count,
        created=user.created_at.strftime("%d.%m.%Y %H:%M"),
        last_seen=user.last_seen.strftime("%d.%m.%Y %H:%M") if user.last_seen else "Никогда"
    )
    
    # Подготавливаем данные о пользователе для клавиатуры
    user_data = {
        'is_admin': user.is_admin,
        'is_blocked': user.is_blocked
    }
    
    if hasattr(message_or_callback, 'message'):  # Это callback
        await safe_edit_message(
            message_or_callback.message, text,
            reply_markup=get_user_action_keyboard(user.id, "ru", user_data)
        )
    else:  # Это message
        await message_or_callback.answer(
            text,
            reply_markup=get_user_action_keyboard(user.id, "ru", user_data)
        )

@router.callback_query(F.data.regexp(r"^admin:user_details_\d+$"))
async def view_user_details(callback: CallbackQuery, state: FSMContext):
    """Просмотр деталей пользователя"""
    user_id = int(callback.data.split("_")[2])

    user = await UserRepository.get_by_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    await show_user_details(callback, user, state)
    await callback.answer()

@router.callback_query(F.data.regexp(r"^admin:make_admin_\d+$"))
async def make_admin(callback: CallbackQuery, state: FSMContext):
    """Назначение администратором"""
    user_id = int(callback.data.split("_")[2])

    user = await UserRepository.get_by_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    # Проверяем, не заблокирован ли пользователь
    if user.is_blocked:
        await callback.answer("❌ Нельзя назначить админом заблокированного пользователя")
        return
    
    # Проверяем, не является ли уже администратором
    if user.is_admin:
        await callback.answer("❌ Пользователь уже является администратором")
        return
    
    try:
        await UserRepository.make_admin(user.telegram_id)
        
        # Устанавливаем админские команды для пользователя
        await set_admin_commands(callback.bot, user.telegram_id)
        
        # Уведомляем пользователя
        notification_text = """👑 Вы назначены администратором!

Теперь у вас есть доступ к админ-панели бота.
Используйте команду /admin для входа."""
        
        try:
            await callback.bot.send_message(user.telegram_id, notification_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления пользователю {user.telegram_id}: {e}")
        
        # Обновляем информацию о пользователе
        updated_user = await UserRepository.get_by_id(user_id)
        if updated_user:
            await show_user_details(callback, updated_user, state)
        else:
            text = """✅ Пользователь назначен администратором

Пользователь получил права администратора и уведомление."""
            
            keyboard = [[
                InlineKeyboardButton(
                    text="🔙 К пользователям",
                    callback_data="admin:users"
                )
            ]]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        
        logger.info(f"Пользователь {user.telegram_id} назначен администратором пользователем {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка назначения администратора {user_id}: {e}")
        await callback.answer("❌ Ошибка при назначении администратора")
    
    await callback.answer()

@router.callback_query(F.data.regexp(r"^admin:remove_admin_\d+$"))
async def remove_admin(callback: CallbackQuery, state: FSMContext):
    """Снятие прав администратора"""
    user_id = int(callback.data.split("_")[2])

    user = await UserRepository.get_by_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    # Проверяем, не пытается ли админ снять права у себя
    if user.telegram_id == callback.from_user.id:
        await callback.answer("❌ Нельзя снять права у самого себя")
        return
    
    # Проверяем, является ли пользователь администратором
    if not user.is_admin:
        await callback.answer("❌ Пользователь не является администратором")
        return
    
    try:
        await UserRepository.remove_admin(user.telegram_id)
        
        # Удаляем админские команды для пользователя
        await remove_admin_commands(callback.bot, user.telegram_id)
        
        # Обновляем информацию о пользователе
        updated_user = await UserRepository.get_by_id(user_id)
        if updated_user:
            await show_user_details(callback, updated_user, state)
        else:
            text = """✅ Права администратора сняты

Пользователь больше не является администратором."""
            
            keyboard = [[
                InlineKeyboardButton(
                    text="🔙 К пользователям",
                    callback_data="admin:users"
                )
            ]]
            
            await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        logger.info(f"У пользователя {user.telegram_id} сняты права администратора пользователем {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка снятия прав администратора {user_id}: {e}")
        await callback.answer("❌ Ошибка при снятии прав")
    
    await callback.answer()

@router.callback_query(F.data.regexp(r"^admin:block_user_\d+$"))
async def block_user(callback: CallbackQuery, state: FSMContext):
    """Блокировка пользователя"""
    user_id = int(callback.data.split("_")[2])

    user = await UserRepository.get_by_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    # Проверяем, не пытается ли админ заблокировать себя
    if user.telegram_id == callback.from_user.id:
        await callback.answer("❌ Нельзя заблокировать самого себя")
        return
    
    # Проверяем, не является ли пользователь администратором
    if user.is_admin:
        await callback.answer("❌ Нельзя заблокировать администратора")
        return
    
    try:
        await UserRepository.block_user(user.telegram_id)
        
        # Обновляем информацию о пользователе
        updated_user = await UserRepository.get_by_id(user_id)
        if updated_user:
            await show_user_details(callback, updated_user, state)
        else:
            text = """🚫 Пользователь заблокирован

Пользователь заблокирован и не может использовать бота."""
            
            keyboard = [[
                InlineKeyboardButton(
                    text="🔙 К пользователям",
                    callback_data="admin:users"
                )
            ]]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        
        logger.info(f"Пользователь {user.telegram_id} заблокирован администратором {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка блокировки пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при блокировке")
    
    await callback.answer()

@router.callback_query(F.data.regexp(r"^admin:unblock_user_\d+$"))
async def unblock_user(callback: CallbackQuery, state: FSMContext):
    """Разблокировка пользователя"""
    user_id = int(callback.data.split("_")[2])

    user = await UserRepository.get_by_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    try:
        await UserRepository.unblock_user(user.telegram_id)
        
        # Обновляем информацию о пользователе
        updated_user = await UserRepository.get_by_id(user_id)
        if updated_user:
            await show_user_details(callback, updated_user, state)
        else:
            text = """✅ Пользователь разблокирован

Пользователь снова может использовать бота."""
            
            keyboard = [[
                InlineKeyboardButton(
                    text="🔙 К пользователям",
                    callback_data="admin:users"
                )
            ]]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        
        logger.info(f"Пользователь {user.telegram_id} разблокирован администратором {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка разблокировки пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при разблокировке")
    
    await callback.answer()

@router.callback_query(F.data.regexp(r"^admin:list_users(?:_page_\d+)?$"))
async def list_users(callback: CallbackQuery, state: FSMContext):
    """Список всех пользователей с пагинацией"""
    
    # Извлекаем номер страницы из callback_data
    page = 1
    if "_page_" in callback.data:
        try:
            page = int(callback.data.split("_page_")[1])
        except (ValueError, IndexError):
            page = 1
    
    users_per_page = 10
    offset = (page - 1) * users_per_page
    
    # Получаем пользователей с пагинацией
    users = await UserRepository.get_all_users(limit=users_per_page, offset=offset)
    total_users = await UserRepository.get_total_count()
    
    if not users:
        text = """👥 Список пользователей

Пользователи не найдены."""
        
        keyboard = [[
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="admin:users"
            )
        ]]
    else:
        total_pages = (total_users + users_per_page - 1) // users_per_page
        
        text = """👥 Список пользователей

📃 Страница {page} из {total_pages}
👤 Всего пользователей: {total}

Пользователи:""".format(page=page, total_pages=total_pages, total=total_users)
        
        keyboard = []
        for user in users:
            user_info = f"@{user.username}" if user.username else f"ID: {user.telegram_id}"
            status_emoji = "🚫" if user.is_blocked else ("👑" if user.is_admin else "👤")
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} {user_info}",
                    callback_data=f"admin:user_details_{user.id}"
                )
            ])
        
        # Добавляем кнопки навигации
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Предыдущая",
                    callback_data=f"admin:list_users_page_{page-1}"
                )
            )
        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Следующая",
                    callback_data=f"admin:list_users_page_{page+1}"
                )
            )
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="admin:users"
            )
        ])
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data.regexp(r"^admin:blocked_users(?:_page_\d+)?$"))
async def list_blocked_users(callback: CallbackQuery, state: FSMContext):
    """Список заблокированных пользователей с пагинацией"""
    
    # Извлекаем номер страницы из callback_data
    page = 1
    if "_page_" in callback.data:
        try:
            page = int(callback.data.split("_page_")[1])
        except (ValueError, IndexError):
            page = 1
    
    users_per_page = 10
    offset = (page - 1) * users_per_page
    
    # Получаем заблокированных пользователей
    blocked_users = await UserRepository.get_blocked_users()
    total_blocked = len(blocked_users)
    
    # Применяем пагинацию к результатам
    paginated_users = blocked_users[offset:offset + users_per_page]
    
    if not blocked_users:
        text = """🚫 Заблокированные пользователи

Заблокированных пользователей нет."""
        
        keyboard = [[
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="admin:users"
            )
        ]]
    else:
        total_pages = (total_blocked + users_per_page - 1) // users_per_page
        
        text = """🚫 Заблокированные пользователи

📃 Страница {page} из {total_pages}
👤 Всего заблокировано: {total}

Заблокированные пользователи:""".format(page=page, total_pages=total_pages, total=total_blocked)
        
        keyboard = []
        for user in paginated_users:
            user_info = f"@{user.username}" if user.username else f"ID: {user.telegram_id}"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🚫 {user_info}",
                    callback_data=f"admin:user_details_{user.id}"
                )
            ])
        
        # Добавляем кнопки навигации
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Предыдущая",
                    callback_data=f"admin:blocked_users_page_{page-1}"
                )
            )
        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Следующая",
                    callback_data=f"admin:blocked_users_page_{page+1}"
                )
            )
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="admin:users"
            )
        ])
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "admin:list_admins")
async def list_admins(callback: CallbackQuery, state: FSMContext):
    """Список администраторов"""
    
    admins = await UserRepository.get_admins()
    
    if not admins:
        text = """👑 Администраторы

Нет администраторов в системе."""
        
        keyboard = [[
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="admin:users"
            )
        ]]
    else:
        text = """👑 Администраторы ({count})

Список администраторов:""".format(count=len(admins))
        
        keyboard = []
        for admin in admins:
            admin_info = f"@{admin.username}" if admin.username else f"ID: {admin.telegram_id}"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"👑 {admin_info}",
                    callback_data=f"admin:user_details_{admin.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="admin:users"
            )
        ])
    
    await safe_edit_message(
        callback.message, text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()
@router.callback_query(F.data.regexp(r"^admin:search_page_\d+$"))
async def search_pagination(callback: CallbackQuery, state: FSMContext):
    """Пагинация результатов поиска"""
    page = int(callback.data.split("_")[2])
    
    # Получаем сохраненные результаты поиска
    data = await state.get_data()
    search_results = data.get('search_results', [])
    
    if not search_results:
        await callback.answer("❌ Результаты поиска не найдены")
        return
    
    # Восстанавливаем объекты пользователей из сохраненных данных
    users = []
    for user_data in search_results:
        user = await UserRepository.get_by_id(user_data[0])
        if user:
            users.append(user)
    
    if not users:
        await callback.answer("❌ Пользователи не найдены")
        return
    
    # Показываем результаты на новой странице
    await show_search_results(callback, users, page, "поиск", state)
    await callback.answer()
