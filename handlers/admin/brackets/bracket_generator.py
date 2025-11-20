"""
Генератор турнирных сеток с интеграцией Challonge API
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database.repositories.tournament_repository import TournamentRepository
from database.repositories.team_repository import TeamRepository
from integrations.challonge_api import ChallongeAPI
from config.settings import settings
from utils.message_utils import safe_edit_message
from handlers.admin.states import AdminStates

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("admin:generate_bracket_"))
async def show_bracket_generation_menu(callback: CallbackQuery, state: FSMContext):
    """Показать меню генерации сетки"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем турнир
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Проверяем что турнир ещё не начат
        if tournament.status != "registration":
            await callback.answer("❌ Генерация доступна только для турниров в статусе регистрации", show_alert=True)
            return
        
        # Получаем одобренные команды
        approved_teams = await TeamRepository.get_approved_teams_by_tournament(tournament_id)
        
        if not approved_teams:
            await callback.answer("❌ Нет одобренных команд для генерации сетки", show_alert=True)
            return
        
        if len(approved_teams) < 2:
            await callback.answer(f"❌ Недостаточно команд (минимум 2, сейчас {len(approved_teams)})", show_alert=True)
            return
        
        # Проверяем есть ли уже Challonge турнир
        challonge_status = "✅ Создан" if tournament.challonge_id else "❌ Не создан"
        
        # Экранируем специальные символы для HTML
        tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Получаем информацию о формате
        from utils.bracket_formatter import get_tournament_format_info
        format_info = get_tournament_format_info(tournament.format)
        
        text = f"""{format_info['icon']} <b>Генерация турнирной сетки</b>

<b>Турнир:</b> {tournament_name}
<b>Формат:</b> {format_info['name']}
<b>Описание:</b> <i>{format_info['description']}</i>
<b>Команд одобрено:</b> {len(approved_teams)}/{tournament.max_teams}
<b>Challonge:</b> {challonge_status}

<b>Шаги генерации:</b>
1. Создать турнир в Challonge (если не создан)
2. Добавить все одобренные команды
3. Рандомизировать сиды
4. Запустить турнир

⚠️ <b>Внимание:</b> После генерации сетки турнир будет переведён в статус "В процессе" и регистрация закроется.

<b>Готовы начать?</b>"""
        
        keyboard = []
        
        if tournament.challonge_id:
            # Турнир уже есть в Challonge, можем синхронизировать
            keyboard.append([
                InlineKeyboardButton(
                    text="🔄 Синхронизировать участников",
                    callback_data=f"admin:sync_participants_{tournament_id}"
                )
            ])
            keyboard.append([
                InlineKeyboardButton(
                    text="✏️ Редактор сетки",
                    callback_data=f"admin:edit_bracket_{tournament_id}"
                )
            ])
            keyboard.append([
                InlineKeyboardButton(
                    text="🚀 Запустить турнир",
                    callback_data=f"admin:start_bracket_{tournament_id}"
                )
            ])
        else:
            # Нужно создать турнир в Challonge
            keyboard.append([
                InlineKeyboardButton(
                    text="✨ Создать сетку в Challonge",
                    callback_data=f"admin:create_challonge_{tournament_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=f"admin:manage_tournament_{tournament_id}"
            )
        ])
        
        await safe_edit_message(
            callback.message, text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка показа меню генерации: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:create_challonge_"))
async def create_challonge_tournament(callback: CallbackQuery, state: FSMContext):
    """Создание турнира в Challonge и добавление участников"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем турнир
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Показываем процесс
        text = f"""⏳ **Создание сетки в Challonge...**

**Турнир:** {tournament.name}

Пожалуйста, подождите...

**Шаги:**
⏳ Создание турнира...
⏳ Добавление участников...
⏳ Настройка параметров..."""
        
        await safe_edit_message(callback.message, text, parse_mode="Markdown")
        
        # Получаем команды
        approved_teams = await TeamRepository.get_approved_teams_by_tournament(tournament_id)
        
        if len(approved_teams) < 2:
            await callback.answer("❌ Недостаточно команд", show_alert=True)
            return
        
        # Создаем API клиент
        if not settings.challonge_client_id or not settings.challonge_username:
            text = """❌ **Ошибка конфигурации**

Challonge API не настроен.

Проверьте параметры:
• CHALLONGE_CLIENT_ID
• CHALLONGE_CLIENT_SECRET

в файле .env"""
            
            keyboard = [[
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=f"admin:generate_bracket_{tournament_id}"
                )
            ]]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            return
        
        challonge = ChallongeAPI(settings.challonge_client_id, settings.challonge_client_secret, settings.challonge_username)
        
        # Определяем формат для Challonge
        format_mapping = {
            'single_elimination': 'single elimination',
            'double_elimination': 'double elimination',
            'round_robin': 'round robin',
            'group_stage_playoffs': 'single elimination'  # Пока как single
        }
        
        challonge_format = format_mapping.get(tournament.format, 'single elimination')
        
        # Создаем турнир в Challonge
        logger.info(f"Создаём турнир {tournament.name} в Challonge...")
        
        challonge_tournament = await challonge.create_tournament(
            name=tournament.name,
            tournament_type=challonge_format,
            description=tournament.description or "",
            private=False
        )
        
        if not challonge_tournament:
            text = """❌ **Ошибка создания турнира в Challonge**

Проверьте:
1. API ключ корректен
2. Username корректен
3. Интернет соединение работает

Попробуйте ещё раз."""
            
            keyboard = [[
                InlineKeyboardButton(
                    text="🔄 Попробовать снова",
                    callback_data=f"admin:create_challonge_{tournament_id}"
                )
            ],[
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=f"admin:generate_bracket_{tournament_id}"
                )
            ]]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            return
        
        # Сохраняем ID турнира Challonge
        await TournamentRepository.update_challonge_id(tournament.id, challonge_tournament['id'])
        
        logger.info(f"Турнир создан в Challonge: ID={challonge_tournament['id']}")
        
        # Добавляем участников
        text = f"""⏳ **Добавление участников...**

**Турнир:** {tournament.name}
**Challonge ID:** {challonge_tournament['id']}

Добавлено: 0/{len(approved_teams)}"""
        
        await safe_edit_message(callback.message, text, parse_mode="Markdown")
        
        added_count = 0
        failed_teams = []
        
        for team in approved_teams:
            try:
                participant = await challonge.add_participant(
                    tournament_id=challonge_tournament['id'],
                    participant_name=team.name
                )
                
                if participant:
                    added_count += 1
                    logger.info(f"Добавлена команда: {team.name}")
                else:
                    failed_teams.append(team.name)
                    logger.error(f"Не удалось добавить команду: {team.name}")
                
            except Exception as e:
                failed_teams.append(team.name)
                logger.error(f"Ошибка добавления команды {team.name}: {e}")
        
        # Результат
        if failed_teams:
            failed_list = "\n".join([f"• {name}" for name in failed_teams])
            tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            challonge_url = str(challonge_tournament.get('full_challonge_url', 'N/A')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            text = f"""⚠️ <b>Турнир создан с ошибками</b>

<b>Турнир:</b> {tournament_name}
<b>Challonge ID:</b> {challonge_tournament['id']}
<b>URL:</b> {challonge_url}

<b>Добавлено команд:</b> {added_count}/{len(approved_teams)}

<b>Не удалось добавить:</b>
{failed_list}

Вы можете попробовать синхронизировать участников снова или запустить турнир как есть."""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="🔄 Синхронизировать снова",
                        callback_data=f"admin:sync_participants_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🚀 Запустить турнир",
                        callback_data=f"admin:start_bracket_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data=f"admin:generate_bracket_{tournament_id}"
                    )
                ]
            ]
        else:
            tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            challonge_url = str(challonge_tournament.get('full_challonge_url', 'N/A')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            text = f"""✅ <b>Сетка успешно создана!</b>

<b>Турнир:</b> {tournament_name}
<b>Challonge ID:</b> {challonge_tournament['id']}
<b>URL:</b> {challonge_url}

<b>Добавлено команд:</b> {added_count}/{len(approved_teams)}

Сетка готова! Теперь вы можете:
1. Запустить турнир (сгенерирует матчи)
2. Синхронизировать участников (если нужно)

⚠️ После запуска турнира изменить участников будет нельзя!"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="🚀 Запустить турнир",
                        callback_data=f"admin:start_bracket_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Синхронизировать участников",
                        callback_data=f"admin:sync_participants_{tournament_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data=f"admin:generate_bracket_{tournament_id}"
                    )
                ]
            ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания турнира в Challonge: {e}", exc_info=True)
        text = f"""❌ **Критическая ошибка**

{str(e)}

Обратитесь к разработчику."""
        
        keyboard = [[
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=f"admin:generate_bracket_{tournament_id}"
            )
        ]]
        
        await safe_edit_message(
            callback.message, text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data.startswith("admin:sync_participants_"))
async def sync_participants(callback: CallbackQuery, state: FSMContext):
    """Синхронизация участников с Challonge"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем турнир
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament or not tournament.challonge_id:
            await callback.answer("❌ Турнир не найден или нет Challonge ID", show_alert=True)
            return
        
        text = "⏳ Синхронизация участников с Challonge..."
        await safe_edit_message(callback.message, text, parse_mode="Markdown")
        
        # Получаем команды из БД
        approved_teams = await TeamRepository.get_approved_teams_by_tournament(tournament_id)
        
        # Создаем API клиент
        challonge = ChallongeAPI(settings.challonge_client_id, settings.challonge_client_secret, settings.challonge_username)
        
        # Получаем текущих участников из Challonge
        current_participants = await challonge.get_participants(tournament.challonge_id)
        # API v2.1 возвращает данные напрямую в attributes (без вложенности 'participant')
        current_names = {p.get('name', '') for p in current_participants if p.get('name')}
        
        # Определяем кого нужно добавить
        db_names = {team.name for team in approved_teams}
        to_add = db_names - current_names
        
        added = 0
        failed = []
        
        for team_name in to_add:
            try:
                participant = await challonge.add_participant(
                    tournament_id=tournament.challonge_id,
                    participant_name=team_name
                )
                if participant:
                    added += 1
                else:
                    failed.append(team_name)
            except Exception as e:
                logger.error(f"Ошибка добавления {team_name}: {e}")
                failed.append(team_name)
        
        if failed:
            failed_list = "\n".join([f"• {name}" for name in failed])
            text = f"""⚠️ **Синхронизация завершена с ошибками**

**Добавлено:** {added}
**Не удалось добавить:** {len(failed)}

{failed_list}"""
        else:
            text = f"""✅ **Синхронизация завершена!**

**Добавлено новых участников:** {added}
**Всего участников:** {len(db_names)}"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🚀 Запустить турнир",
                    callback_data=f"admin:start_bracket_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=f"admin:generate_bracket_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка синхронизации: {e}")
        await callback.answer("❌ Ошибка синхронизации", show_alert=True)


@router.callback_query(F.data.startswith("admin:start_bracket_"))
async def start_tournament_bracket(callback: CallbackQuery, state: FSMContext):
    """Запуск турнира (генерация матчей)"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем турнир
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament or not tournament.challonge_id:
            await callback.answer("❌ Турнир не найден или нет Challonge ID", show_alert=True)
            return
        
        # Показываем подтверждение
        text = f"""⚠️ **Подтверждение запуска турнира**

**Турнир:** {tournament.name}
**Challonge ID:** {tournament.challonge_id}

После запуска:
✅ Будут сгенерированы все матчи
✅ Турнир перейдёт в статус "В процессе"
✅ Регистрация будет закрыта
❌ Добавить участников будет нельзя

**Вы уверены?**"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Да, запустить",
                    callback_data=f"admin:confirm_start_bracket_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"admin:generate_bracket_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка показа подтверждения: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:refresh_bracket_status_"))
async def refresh_bracket_status(callback: CallbackQuery, state: FSMContext):
    """Обновление статуса турнира после ручного запуска"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем турнир
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament or not tournament.challonge_id:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        # Создаем API клиент
        challonge = ChallongeAPI(settings.challonge_client_id, settings.challonge_client_secret, settings.challonge_username)
        
        # Проверяем статус турнира
        tournament_info = await challonge.get_tournament_info(tournament.challonge_id)
        
        if not tournament_info:
            await callback.answer("❌ Не удалось получить информацию о турнире", show_alert=True)
            return
        
        current_state = tournament_info.get('state', 'pending')
        
        if current_state == 'underway':
            # Турнир запущен! Обновляем статус в БД
            await TournamentRepository.update_status(tournament_id, 'in_progress')
            
            tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # Получаем матчи и синхронизируем
            matches = await challonge.get_matches(tournament.challonge_id)
            
            # Синхронизируем матчи с БД
            from database.repositories import MatchRepository
            from database.models import TeamStatus
            
            # Получаем участников для маппинга
            participants = await challonge.get_participants(tournament.challonge_id)
            teams = await TeamRepository.get_teams_by_tournament(tournament_id, status=TeamStatus.APPROVED)
            
            # Создаём маппинг
            participants_map = {}
            for participant in participants:
                p_id = str(participant.get("id"))
                p_name = participant.get("name")
                for team in teams:
                    if team.name == p_name:
                        participants_map[p_id] = team.id
                        break
            
            # Синхронизируем
            synced = await MatchRepository.sync_matches_from_challonge(
                tournament_id=tournament_id,
                challonge_matches=matches,
                participants_map=participants_map
            )
            
            # Подсчитываем назначенные матчи
            assigned = sum(1 for m in synced if m.team1_id or m.team2_id)
            
            text = f"""✅ **Турнир успешно запущен!**

**{tournament_name}**

📊 Сетка сформирована
🎮 Создано матчей: {len(matches)}
👥 Команды назначены: {assigned}/{len(matches)}
🔗 Ссылка: {tournament_info.get('full_challonge_url', '')}

"""
            
            if assigned == 0:
                text += """ℹ️ <i>Команды ещё не назначены на матчи.
В Double Elimination турнирах команды назначаются
по мере начала матчей. Начните первые матчи в Challonge
и нажмите "Синхронизировать матчи".</i>"""
            else:
                text += "Теперь вы можете управлять матчами."
            
            keyboard = [
                [InlineKeyboardButton(
                    text="👁️ Посмотреть сетку",
                    url=tournament_info.get('full_challonge_url', 'https://challonge.com')
                )],
                [InlineKeyboardButton(
                    text="🔄 Синхронизировать матчи",
                    callback_data=f"admin:sync_matches_{tournament_id}"
                )],
                [InlineKeyboardButton(
                    text="🎮 Управление матчами",
                    callback_data=f"admin:manage_matches_{tournament_id}"
                )],
                [InlineKeyboardButton(
                    text="🔙 К турниру",
                    callback_data=f"admin:manage_tournament_{tournament_id}"
                )]
            ]
            
            await safe_edit_message(
                callback.message, text, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            logger.info(f"Турнир {tournament.name} успешно запущен и синхронизирован! Назначено команд: {assigned}/{len(matches)}")
            
        else:
            # Турнир ещё не запущен
            await callback.answer(
                f"⚠️ Турнир ещё не запущен (статус: {current_state}). "
                "Откройте турнир в браузере и нажмите Start Tournament.",
                show_alert=True
            )
        
    except Exception as e:
        logger.error(f"Ошибка обновления статуса: {e}", exc_info=True)
        await callback.answer("❌ Ошибка обновления статуса", show_alert=True)


@router.callback_query(F.data.startswith("admin:confirm_start_bracket_"))
async def confirm_start_tournament_bracket(callback: CallbackQuery, state: FSMContext):
    """Подтверждение запуска турнира"""
    try:
        tournament_id = int(callback.data.split("_")[-1])
        
        # Получаем турнир
        tournament = await TournamentRepository.get_by_id(tournament_id)
        
        if not tournament or not tournament.challonge_id:
            await callback.answer("❌ Турнир не найден", show_alert=True)
            return
        
        text = "⏳ Запуск турнира в Challonge..."
        await safe_edit_message(callback.message, text, parse_mode="Markdown")
        
        # Создаем API клиент
        challonge = ChallongeAPI(settings.challonge_client_id, settings.challonge_client_secret, settings.challonge_username)
        
        # Проверяем статус турнира в Challonge
        # ВАЖНО: API v2.1 не поддерживает автоматический запуск турниров
        success = await challonge.start_tournament(tournament.challonge_id)
        
        if not success:
            # Получаем URL турнира для ручного запуска
            tournament_info = await challonge.get_tournament_info(tournament.challonge_id)
            tournament_url = tournament_info.get('full_challonge_url', f"https://challonge.com/{tournament.challonge_id}") if tournament_info else f"https://challonge.com/{tournament.challonge_id}"
            
            tournament_name_escaped = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            text = f"""⚠️ **Требуется ручной запуск турнира**

**{tournament_name_escaped}**

Challonge API v2.1 не поддерживает автоматический запуск турниров.

**Инструкция:**
1. Откройте турнир в браузере:
   {tournament_url}

2. Нажмите кнопку **"Start Tournament"**

3. После запуска вернитесь сюда и нажмите "Обновить"

ℹ️ Все участники уже добавлены в турнир."""
            
            keyboard = [
                [InlineKeyboardButton(
                    text="🔗 Открыть турнир",
                    url=tournament_url
                )],
                [InlineKeyboardButton(
                    text="🔄 Обновить статус",
                    callback_data=f"admin:refresh_bracket_status_{tournament_id}"
                )],
                [InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=f"admin:generate_bracket_{tournament_id}"
                )]
            ]
            
            await safe_edit_message(
                callback.message, text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            return
        
        # Обновляем статус турнира в БД
        await TournamentRepository.update_status(tournament_id, 'in_progress')
        
        # Получаем инфо о турнире
        tournament_info = await challonge.get_tournament(tournament.challonge_id)
        
        tournament_name = tournament.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        challonge_url = str(tournament_info.get('full_challonge_url', 'N/A')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        text = f"""✅ <b>Турнир успешно запущен!</b>

<b>Турнир:</b> {tournament_name}
<b>Статус:</b> В процессе
<b>Challonge URL:</b> {challonge_url}

Сетка сгенерирована! Теперь вы можете:
• Управлять матчами
• Вводить результаты
• Отслеживать прогресс

Удачного турнира! 🏆"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="👁️ Посмотреть сетку",
                    url=tournament_info.get('full_challonge_url', 'https://challonge.com')
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎮 Управление матчами",
                    callback_data=f"admin:manage_matches_{tournament_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 К турниру",
                    callback_data=f"admin:manage_tournament_{tournament_id}"
                )
            ]
        ]
        
        await safe_edit_message(
            callback.message, text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        logger.info(f"Турнир {tournament.name} успешно запущен!")
        
    except Exception as e:
        logger.error(f"Ошибка запуска турнира: {e}", exc_info=True)
        error_msg = str(e).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        text = f"""❌ <b>Критическая ошибка</b>

{error_msg}

Обратитесь к разработчику."""
        
        keyboard = [[
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=f"admin:generate_bracket_{tournament_id}"
            )
        ]]
        
        await safe_edit_message(
            callback.message, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
