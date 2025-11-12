"""
Тестирование Генератора сеток (Фаза 2 - часть 1)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database.db_manager import init_database, close_database
from database.repositories.tournament_repository import TournamentRepository
from database.repositories.team_repository import TeamRepository
from database.repositories.user_repository import UserRepository
from database.repositories.game_repository import GameRepository
from integrations.challonge_api import ChallongeAPI
from config.settings import settings
from datetime import datetime, timedelta


async def test_bracket_generator():
    """Тест генератора сеток"""
    print("🧪 Тестирование генератора сеток...\n")
    
    await init_database()
    print("✅ БД инициализирована\n")
    
    # Тест 1: Проверка конфигурации Challonge
    print("🔑 Тест 1: Проверка Challonge API...")
    if not settings.challonge_api_key or not settings.challonge_username:
        print("❌ Challonge API не настроен!")
        print("   Установите CHALLONGE_API_KEY и CHALLONGE_USERNAME в .env")
        return False
    
    print(f"✅ API Key: {'*' * (len(settings.challonge_api_key)-4) + settings.challonge_api_key[-4:]}")
    print(f"✅ Username: {settings.challonge_username}\n")
    
    # Тест 2: Получение существующего турнира с командами
    print("🏆 Тест 2: Поиск турнира с одобренными командами...")
    tournaments = await TournamentRepository.get_all()
    
    tournament = None
    for t in tournaments:
        approved_count = await TeamRepository.get_approved_teams_count(t.id)
        if approved_count >= 2 and t.status == "registration":
            tournament = t
            print(f"✅ Найден турнир: {t.name} ({approved_count} команд)")
            break
    
    if not tournament:
        print("⚠️  Нет подходящего турнира. Создаём тестовый...")
        
        # Создаём игру если нужно
        game = await GameRepository.get_by_short_name("ML")
        if not game:
            game = await GameRepository.create_game(
                name="Mobile Legends Test",
                short_name="ML",
                max_players=5,
                max_substitutes=2
            )
        
        # Создаём турнир
        now = datetime.now()
        from database.models import TournamentFormat
        tournament = await TournamentRepository.create_tournament(
            game_id=game.id,
            name=f"Test Bracket Tournament {int(now.timestamp())}",
            description="Тестовый турнир для генератора сеток",
            format_type=TournamentFormat.SINGLE_ELIMINATION,
            max_teams=8,
            registration_start=now,
            registration_end=now + timedelta(days=1),
            tournament_start=now + timedelta(days=2),
            edit_deadline=now + timedelta(days=2, hours=-1),
            rules_text="Test rules",
            required_channels=[],
            created_by=1
        )
        print(f"✅ Создан турнир: {tournament.name}")
        
        # Создаём пользователя-капитана если нужно
        user = await UserRepository.get_by_telegram_id(888888888)
        if not user:
            user = await UserRepository.create_user(
                telegram_id=888888888,
                username="test_bracket_captain",
                full_name="Test Bracket Captain"
            )
        
        # Создаём и одобряем тестовые команды
        for i in range(4):
            team = await TeamRepository.create_team(
                tournament_id=tournament.id,
                name=f"Test Team {i+1}",
                captain_id=user.id
            )
            await TeamRepository.approve_team(team.id)
            print(f"   ✅ Создана команда: {team.name}")
    
    print()
    
    # Тест 3: Получение одобренных команд
    print("👥 Тест 3: Получение одобренных команд...")
    approved_teams = await TeamRepository.get_approved_teams_by_tournament(tournament.id)
    print(f"✅ Одобренных команд: {len(approved_teams)}")
    for team in approved_teams:
        print(f"   • {team.name}")
    print()
    
    if len(approved_teams) < 2:
        print("❌ Недостаточно команд для генерации сетки (минимум 2)")
        return False
    
    # Тест 4: Создание турнира в Challonge
    print("🌐 Тест 4: Создание турнира в Challonge...")
    
    if tournament.challonge_id:
        print(f"ℹ️  Турнир уже создан в Challonge: {tournament.challonge_id}")
        print("   Пропускаем создание...")
    else:
        challonge = ChallongeAPI(settings.challonge_api_key, settings.challonge_username)
        
        challonge_tournament = await challonge.create_tournament(
            name=tournament.name,
            tournament_type="single elimination",
            description=tournament.description or ""
        )
        
        if not challonge_tournament:
            print("❌ Ошибка создания турнира в Challonge")
            return False
        
        print(f"✅ Турнир создан в Challonge")
        print(f"   ID: {challonge_tournament['id']}")
        print(f"   URL: {challonge_tournament.get('full_challonge_url', 'N/A')}")
        
        # Сохраняем ID
        await TournamentRepository.update_challonge_id(tournament.id, challonge_tournament['id'])
        tournament.challonge_id = challonge_tournament['id']
    
    print()
    
    # Тест 5: Добавление участников
    print("➕ Тест 5: Добавление участников в Challonge...")
    
    challonge = ChallongeAPI(settings.challonge_api_key, settings.challonge_username)
    
    # Получаем текущих участников
    current_participants = await challonge.get_participants(tournament.challonge_id)
    current_names = {p['participant']['name'] for p in current_participants}
    
    print(f"   Текущих участников: {len(current_names)}")
    
    added = 0
    for team in approved_teams:
        if team.name not in current_names:
            participant = await challonge.add_participant(
                tournament_id=tournament.challonge_id,
                participant_name=team.name
            )
            if participant:
                added += 1
                print(f"   ✅ Добавлена: {team.name}")
            else:
                print(f"   ❌ Ошибка: {team.name}")
        else:
            print(f"   ℹ️  Уже добавлена: {team.name}")
    
    print(f"✅ Добавлено новых участников: {added}")
    print()
    
    # Тест 6: Запуск турнира (генерация сетки)
    print("🚀 Тест 6: Запуск турнира в Challonge...")
    
    # Проверяем статус
    tournament_info = await challonge.get_tournament(tournament.challonge_id)
    
    if tournament_info and tournament_info.get('state') == 'underway':
        print("ℹ️  Турнир уже запущен")
    else:
        success = await challonge.start_tournament(tournament.challonge_id)
        
        if success:
            print("✅ Турнир запущен! Сетка сгенерирована")
            
            # Обновляем статус в БД
            await TournamentRepository.update_status(tournament.id, 'in_progress')
            print("✅ Статус в БД обновлён: in_progress")
        else:
            print("❌ Ошибка запуска турнира")
            return False
    
    print()
    
    # Тест 7: Получение информации о турнире
    print("📊 Тест 7: Получение информации о турнире...")
    
    tournament_info = await challonge.get_tournament(tournament.challonge_id)
    
    if tournament_info:
        print(f"✅ Информация получена:")
        print(f"   Название: {tournament_info['name']}")
        print(f"   Статус: {tournament_info['state']}")
        print(f"   Участников: {tournament_info['participants_count']}")
        print(f"   URL: {tournament_info.get('full_challonge_url', 'N/A')}")
    else:
        print("❌ Не удалось получить информацию")
        return False
    
    print()
    print("=" * 60)
    print("🎉 ВСЕ ТЕСТЫ ГЕНЕРАТОРА СЕТОК ПРОЙДЕНЫ!")
    print("=" * 60)
    print()
    print("✅ Реализовано:")
    print("   ✅ Создание турнира в Challonge")
    print("   ✅ Добавление участников")
    print("   ✅ Синхронизация команд")
    print("   ✅ Запуск турнира (генерация сетки)")
    print("   ✅ Получение информации о турнире")
    print()
    print(f"🌐 Сетка доступна по адресу:")
    print(f"   {tournament_info.get('full_challonge_url', 'N/A')}")
    print()
    
    await close_database()
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_bracket_generator())
        if result:
            print("✅ Тестирование завершено успешно!")
            sys.exit(0)
        else:
            print("❌ Тестирование провалилось!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
