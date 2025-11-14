"""
Комплексный тест всех функций админ-панели
Проверяет основные сценарии использования бота администратором
"""
import asyncio
import sys
from datetime import datetime, timedelta
from database.repositories import (
    GameRepository, TournamentRepository, TeamRepository, 
    UserRepository, MatchRepository
)
from database.models import TournamentStatus, TeamStatus
from config.settings import settings

# Цвета для вывода
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

test_results = {
    'passed': 0,
    'failed': 0,
    'warnings': 0
}


def print_header(text):
    print(f"\n{BLUE}{'=' * 60}")
    print(f"{text}")
    print(f"{'=' * 60}{RESET}\n")


def print_test(name, status, message=""):
    if status == "PASS":
        print(f"{GREEN}✓{RESET} {name}")
        test_results['passed'] += 1
    elif status == "FAIL":
        print(f"{RED}✗{RESET} {name}")
        if message:
            print(f"  {RED}└─ {message}{RESET}")
        test_results['failed'] += 1
    elif status == "WARN":
        print(f"{YELLOW}⚠{RESET} {name}")
        if message:
            print(f"  {YELLOW}└─ {message}{RESET}")
        test_results['warnings'] += 1


async def test_games():
    """Тест управления играми"""
    print_header("ТЕСТ 1: Управление играми")
    
    try:
        # Получение списка игр
        games = await GameRepository.get_all_games()
        print_test(f"Получение списка игр ({len(games)} шт.)", "PASS")
        
        if not games:
            print_test("В БД должна быть хотя бы одна игра", "WARN", "Создайте игру через /admin")
            return
        
        # Проверка полей игры
        game = games[0]
        required_fields = ['id', 'name', 'short_name', 'max_players']
        missing_fields = [f for f in required_fields if not hasattr(game, f)]
        
        if missing_fields:
            print_test("Проверка полей модели Game", "FAIL", f"Отсутствуют: {missing_fields}")
        else:
            print_test("Проверка полей модели Game", "PASS")
        
        # Проверка иконки
        if game.icon_file_id:
            print_test("Иконка игры установлена", "PASS")
        else:
            print_test("Иконка игры", "WARN", "Иконка не загружена (функционал не реализован)")
        
    except Exception as e:
        print_test("Тест управления играми", "FAIL", str(e))


async def test_formats():
    """Тест управления форматами"""
    print_header("ТЕСТ 2: Управление форматами турниров")
    
    try:
        # Форматы хранятся в enum TournamentFormat, а не в отдельной таблице
        from database.models import TournamentFormat
        
        formats = [f for f in TournamentFormat]
        print_test(f"Доступные форматы турниров ({len(formats)} шт.)", "PASS")
        
        for fmt in formats:
            print(f"    • {fmt.name}: {fmt.value}")
        
        # Проверка использования форматов в турнирах
        tournaments = await TournamentRepository.get_all_tournaments()
        if tournaments:
            valid_formats = [f.value for f in TournamentFormat]
            invalid_formats = []
            
            for t in tournaments:
                if t.format not in valid_formats:
                    invalid_formats.append((t.id, t.format))
            
            if invalid_formats:
                print_test("Валидность форматов турниров", "FAIL", 
                          f"Турниры с недопустимым форматом: {invalid_formats}")
            else:
                print_test("Валидность форматов турниров", "PASS")
        
    except Exception as e:
        print_test("Тест управления форматами", "FAIL", str(e))


async def test_tournaments():
    """Тест управления турнирами"""
    print_header("ТЕСТ 3: Управление турнирами")
    
    try:
        # Получение списка турниров
        tournaments = await TournamentRepository.get_all_tournaments()
        print_test(f"Получение списка турниров ({len(tournaments)} шт.)", "PASS")
        
        if not tournaments:
            print_test("В БД должен быть хотя бы один турнир", "WARN", "Создайте через create_test_tournament.py")
            return
        
        tournament = tournaments[0]
        
        # Проверка обязательных полей
        required_fields = ['id', 'name', 'game_id', 'format', 'status', 'registration_start', 'registration_end']
        missing_fields = [f for f in required_fields if not hasattr(tournament, f)]
        
        if missing_fields:
            print_test("Проверка полей модели Tournament", "FAIL", f"Отсутствуют: {missing_fields}")
        else:
            print_test("Проверка полей модели Tournament", "PASS")
        
        # Проверка статусов
        valid_statuses = [s.value for s in TournamentStatus]
        if tournament.status in valid_statuses:
            print_test(f"Статус турнира ({tournament.status})", "PASS")
        else:
            print_test("Статус турнира", "FAIL", f"Недопустимый статус: {tournament.status}")
        
        # Проверка дат
        if tournament.registration_end and tournament.registration_start:
            if tournament.registration_end > tournament.registration_start:
                print_test("Валидность дат регистрации", "PASS")
            else:
                print_test("Валидность дат регистрации", "FAIL", "Дата окончания раньше начала")
        
        # Проверка связи с игрой
        if tournament.game:
            print_test(f"Связь с игрой ({tournament.game.name})", "PASS")
        else:
            print_test("Связь турнира с игрой", "FAIL", "Game не загружен")
        
        # Проверка Challonge
        if tournament.challonge_id:
            print_test(f"Challonge ID ({tournament.challonge_id})", "PASS")
        else:
            print_test("Challonge интеграция", "WARN", "Турнир не создан в Challonge")
        
    except Exception as e:
        print_test("Тест управления турнирами", "FAIL", str(e))


async def test_teams():
    """Тест управления командами"""
    print_header("ТЕСТ 4: Управление командами")
    
    try:
        tournaments = await TournamentRepository.get_all_tournaments()
        if not tournaments:
            print_test("Тест команд", "WARN", "Нет турниров для проверки")
            return
        
        tournament = tournaments[0]
        teams = await TeamRepository.get_teams_by_tournament(tournament.id)
        print_test(f"Получение команд турнира ({len(teams)} шт.)", "PASS")
        
        if not teams:
            print_test("Наличие команд", "WARN", "Создайте команды через create_test_tournament.py")
            return
        
        team = teams[0]
        
        # Проверка полей
        required_fields = ['id', 'name', 'tournament_id', 'captain_id', 'status']
        missing_fields = [f for f in required_fields if not hasattr(team, f)]
        
        if missing_fields:
            print_test("Проверка полей модели Team", "FAIL", f"Отсутствуют: {missing_fields}")
        else:
            print_test("Проверка полей модели Team", "PASS")
        
        # Проверка статуса
        valid_statuses = [s.value for s in TeamStatus]
        if team.status in valid_statuses:
            print_test(f"Статус команды ({team.status})", "PASS")
        else:
            print_test("Статус команды", "FAIL", f"Недопустимый статус: {team.status}")
        
        # Проверка игроков
        if team.players:
            print_test(f"Игроки в команде ({len(team.players)} чел.)", "PASS")
            
            # Проверка основного состава и запасных
            main_players = [p for p in team.players if not p.is_substitute]
            subs = [p for p in team.players if p.is_substitute]
            
            print_test(f"  Основной состав: {len(main_players)}, Запасные: {len(subs)}", "PASS")
        else:
            print_test("Игроки в команде", "WARN", "Нет игроков")
        
        # Проверка капитана
        if team.captain:
            print_test(f"Капитан команды ({team.captain.username or team.captain.telegram_id})", "PASS")
        else:
            print_test("Капитан команды", "FAIL", "Captain не загружен")
        
    except Exception as e:
        print_test("Тест управления командами", "FAIL", str(e))


async def test_matches():
    """Тест управления матчами"""
    print_header("ТЕСТ 5: Управление матчами")
    
    try:
        tournaments = await TournamentRepository.get_all_tournaments()
        tournament = None
        for t in tournaments:
            if t.challonge_id:
                tournament = t
                break
        
        if not tournament:
            print_test("Тест матчей", "WARN", "Нет турниров с Challonge ID")
            return
        
        matches = await MatchRepository.get_tournament_matches(tournament.id)
        print_test(f"Получение матчей турнира ({len(matches)} шт.)", "PASS")
        
        if not matches:
            print_test("Наличие матчей", "WARN", "Запустите турнир и синхронизируйте матчи")
            return
        
        match = matches[0]
        
        # Проверка полей
        required_fields = ['id', 'tournament_id', 'round_number', 'match_number', 'status']
        missing_fields = [f for f in required_fields if not hasattr(match, f)]
        
        if missing_fields:
            print_test("Проверка полей модели Match", "FAIL", f"Отсутствуют: {missing_fields}")
        else:
            print_test("Проверка полей модели Match", "PASS")
        
        # Проверка команд
        if match.team1_id and match.team2_id:
            if match.team1 and match.team2:
                print_test(f"Команды в матче ({match.team1.name} vs {match.team2.name})", "PASS")
            else:
                print_test("Связь с командами", "FAIL", "Team1/Team2 не загружены")
        else:
            print_test("Команды в матче", "WARN", "TBD - матч без команд")
        
        # Проверка Challonge ID
        if match.challonge_match_id:
            print_test(f"Challonge Match ID ({match.challonge_match_id})", "PASS")
        else:
            print_test("Challonge Match ID", "WARN", "Не синхронизирован")
        
    except Exception as e:
        print_test("Тест управления матчами", "FAIL", str(e))


async def test_users():
    """Тест управления пользователями"""
    print_header("ТЕСТ 6: Управление пользователями")
    
    try:
        # Получение пользователей
        users = await UserRepository.get_all_users()
        print_test(f"Получение списка пользователей ({len(users)} чел.)", "PASS")
        
        if not users:
            print_test("Наличие пользователей", "WARN", "Нет пользователей в БД")
            return
        
        user = users[0]
        
        # Проверка полей
        required_fields = ['id', 'telegram_id', 'role']
        missing_fields = [f for f in required_fields if not hasattr(user, f)]
        
        if missing_fields:
            print_test("Проверка полей модели User", "FAIL", f"Отсутствуют: {missing_fields}")
        else:
            print_test("Проверка полей модели User", "PASS")
        
        # Проверка timezone
        if hasattr(user, 'timezone') and user.timezone:
            print_test(f"Timezone пользователя ({user.timezone})", "PASS")
        else:
            print_test("Timezone пользователя", "WARN", "Не установлен (по умолчанию UTC)")
        
        # Проверка админов
        admins = [u for u in users if u.role == 'admin']
        print_test(f"Администраторы в системе: {len(admins)}", "PASS")
        
    except Exception as e:
        print_test("Тест управления пользователями", "FAIL", str(e))


async def test_challonge_integration():
    """Тест интеграции с Challonge"""
    print_header("ТЕСТ 7: Интеграция с Challonge API")
    
    try:
        if not settings.challonge_api_key or not settings.challonge_username:
            print_test("Challonge API настройки", "FAIL", "Не установлены CHALLONGE_API_KEY или CHALLONGE_USERNAME")
            return
        
        print_test("Challonge API настройки", "PASS")
        
        from integrations.challonge_api import ChallongeAPI
        
        api = ChallongeAPI(settings.challonge_api_key, settings.challonge_username)
        
        # Поиск турнира в Challonge
        tournaments = await TournamentRepository.get_all_tournaments()
        challonge_tournament = None
        
        for t in tournaments:
            if t.challonge_id:
                challonge_tournament = t
                break
        
        if not challonge_tournament:
            print_test("Турнир в Challonge", "WARN", "Нет турниров с Challonge ID")
            return
        
        # Получение информации о турнире
        info = await api.get_tournament(challonge_tournament.challonge_id)
        if info:
            print_test(f"Получение турнира из Challonge (ID: {challonge_tournament.challonge_id})", "PASS")
        else:
            print_test("Получение турнира из Challonge", "FAIL", "Турнир не найден")
            return
        
        # Получение участников
        participants = await api.get_participants(challonge_tournament.challonge_id)
        print_test(f"Получение участников из Challonge ({len(participants)} чел.)", "PASS")
        
        # Получение матчей
        matches = await api.get_matches(challonge_tournament.challonge_id)
        print_test(f"Получение матчей из Challonge ({len(matches)} шт.)", "PASS")
        
    except Exception as e:
        print_test("Тест интеграции с Challonge", "FAIL", str(e))


async def test_markdown_issues():
    """Тест на наличие Markdown в parse_mode"""
    print_header("ТЕСТ 8: Проверка Markdown форматирования")
    
    import os
    import re
    
    try:
        handlers_dir = "handlers/admin"
        markdown_files = []
        
        for root, dirs, files in os.walk(handlers_dir):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'parse_mode="Markdown"' in content:
                            count = content.count('parse_mode="Markdown"')
                            markdown_files.append((filepath, count))
        
        if markdown_files:
            print_test("Проверка parse_mode='Markdown'", "WARN", 
                      f"Найдено {len(markdown_files)} файлов с Markdown")
            for filepath, count in markdown_files[:5]:  # Показываем первые 5
                print(f"    {filepath}: {count} вхождений")
            if len(markdown_files) > 5:
                print(f"    ... и еще {len(markdown_files) - 5} файлов")
        else:
            print_test("Проверка parse_mode='Markdown'", "PASS", "Везде используется HTML")
        
    except Exception as e:
        print_test("Проверка Markdown форматирования", "FAIL", str(e))


async def test_database_integrity():
    """Тест целостности БД"""
    print_header("ТЕСТ 9: Целостность базы данных")
    
    try:
        # Проверка Foreign Keys
        tournaments = await TournamentRepository.get_all_tournaments()
        
        if tournaments:
            orphaned_tournaments = []
            for t in tournaments:
                if not t.game:
                    orphaned_tournaments.append(t.id)
            
            if orphaned_tournaments:
                print_test("FK: Tournament -> Game", "FAIL", 
                          f"Турниры без игры: {orphaned_tournaments}")
            else:
                print_test("FK: Tournament -> Game", "PASS")
        
        # Проверка команд
        all_teams = []
        for t in tournaments:
            teams = await TeamRepository.get_teams_by_tournament(t.id)
            all_teams.extend(teams)
        
        if all_teams:
            orphaned_teams = []
            for team in all_teams:
                if not team.captain:
                    orphaned_teams.append(team.id)
            
            if orphaned_teams:
                print_test("FK: Team -> User (captain)", "FAIL",
                          f"Команды без капитана: {orphaned_teams}")
            else:
                print_test("FK: Team -> User (captain)", "PASS")
        
    except Exception as e:
        print_test("Тест целостности БД", "FAIL", str(e))


async def main():
    """Запуск всех тестов"""
    print(f"\n{BLUE}{'=' * 60}")
    print("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ АДМИН-ПАНЕЛИ")
    print(f"{'=' * 60}{RESET}")
    print(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"База данных: {settings.database_path}")
    
    # Запуск тестов
    await test_games()
    await test_formats()
    await test_tournaments()
    await test_teams()
    await test_matches()
    await test_users()
    await test_challonge_integration()
    await test_markdown_issues()
    await test_database_integrity()
    
    # Итоги
    print_header("ИТОГИ ТЕСТИРОВАНИЯ")
    total = test_results['passed'] + test_results['failed'] + test_results['warnings']
    
    print(f"{GREEN}✓ Пройдено:{RESET} {test_results['passed']}/{total}")
    print(f"{RED}✗ Провалено:{RESET} {test_results['failed']}/{total}")
    print(f"{YELLOW}⚠ Предупреждений:{RESET} {test_results['warnings']}/{total}")
    
    if test_results['failed'] == 0:
        print(f"\n{GREEN}{'=' * 60}")
        print("ВСЕ КРИТИЧЕСКИЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print(f"{'=' * 60}{RESET}\n")
    else:
        print(f"\n{RED}{'=' * 60}")
        print("ОБНАРУЖЕНЫ КРИТИЧЕСКИЕ ОШИБКИ!")
        print(f"{'=' * 60}{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
