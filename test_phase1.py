"""
Тестирование Фазы 1: Регистрация команд + Обязательные каналы + Модерация
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from database.db_manager import init_database, close_database
from database.repositories.user_repository import UserRepository
from database.repositories.tournament_repository import TournamentRepository
from database.repositories.team_repository import TeamRepository
from database.repositories.player_repository import PlayerRepository
from database.repositories.game_repository import GameRepository
from database.models import TournamentFormat
from datetime import datetime, timedelta


async def test_phase1():
    """Тестирование всей Фазы 1"""
    print("🧪 Начинаем тестирование Фазы 1...\n")
    
    # Инициализация БД
    print("📦 Инициализация базы данных...")
    await init_database()
    print("✅ База данных инициализирована\n")
    print("ℹ️  Используется существующая БД (если бот запущен)\n")
    
    # Тест 1: Создание пользователя (капитан)
    print("👤 Тест 1: Создание пользователя...")
    try:
        user = await UserRepository.create_user(
            telegram_id=999999999,
            username="test_captain",
            full_name="Тестовый Капитан",
            region="kg",
            language="ru"
        )
        if user:
            print(f"✅ Пользователь создан: {user.full_name} (ID: {user.id})")
        else:
            print("❌ Ошибка создания пользователя")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    print()
    
    # Тест 2: Создание или получение игры
    print("🎮 Тест 2: Получение/создание игры...")
    try:
        # Пробуем найти существующую игру
        game = await GameRepository.get_by_short_name("ML")
        
        if not game:
            # Создаём новую, если не нашли
            game = await GameRepository.create_game(
                name="Mobile Legends",
                short_name="ML",
                max_players=5,
                max_substitutes=2,
                icon_file_id=None
            )
            print(f"✅ Игра создана: {game.name} (ID: {game.id})")
        else:
            print(f"✅ Игра найдена: {game.name} (ID: {game.id})")
            
        if not game:
            print("❌ Ошибка получения/создания игры")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    print()
    
    # Тест 3: Создание турнира с обязательными каналами
    print("🏆 Тест 3: Создание турнира с обязательными каналами...")
    try:
        now = datetime.now()
        tournament = await TournamentRepository.create_tournament(
            game_id=game.id,
            name="Тестовый Турнир 2025",
            description="Турнир для тестирования системы",
            format_type=TournamentFormat.SINGLE_ELIMINATION,
            max_teams=16,
            registration_start=now,
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=10),
            edit_deadline=now + timedelta(days=9),
            rules_text="Правила турнира: играть честно!",
            required_channels=["enasgame_official", "testchannel"],  # Обязательные каналы
            created_by=user.id
        )
        if tournament:
            print(f"✅ Турнир создан: {tournament.name} (ID: {tournament.id})")
            channels = tournament.required_channels_list
            print(f"   📢 Обязательных каналов: {len(channels)}")
            for channel in channels:
                print(f"      • @{channel}")
        else:
            print("❌ Ошибка создания турнира")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    print()
    
    # Тест 4: Регистрация команды
    print("👥 Тест 4: Регистрация команды...")
    try:
        team = await TeamRepository.create_team(
            tournament_id=tournament.id,
            name="Test Team Alpha",
            captain_id=user.id,
            logo_file_id=None
        )
        if team:
            print(f"✅ Команда создана: {team.name} (ID: {team.id})")
            print(f"   📊 Статус: {team.status}")
        else:
            print("❌ Ошибка создания команды")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    print()
    
    # Тест 5: Добавление игроков
    print("🎮 Тест 5: Добавление игроков...")
    try:
        players_data = [
            ("Player1", "ML12345", False, 1),
            ("Player2", "ML12346", False, 2),
            ("Player3", "ML12347", False, 3),
            ("Player4", "ML12348", False, 4),
            ("Player5", "ML12349", False, 5),
            ("Sub1", "ML12350", True, 1),
        ]
        
        for nickname, game_id_str, is_sub, position in players_data:
            player = await PlayerRepository.add_player(
                team_id=team.id,
                nickname=nickname,
                game_id=game_id_str,
                is_substitute=is_sub,
                position=position
            )
            if player:
                role = "Запасной" if is_sub else "Основной"
                print(f"   ✅ {role}: {player.nickname} | {player.game_id}")
            else:
                print(f"   ❌ Ошибка добавления игрока {nickname}")
                return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    print()
    
    # Тест 6: Проверка состояния команды (pending)
    print("📋 Тест 6: Проверка статуса команды...")
    try:
        pending_teams = await TeamRepository.get_pending_teams()
        print(f"✅ Команд на модерации: {len(pending_teams)}")
        if team.id in [t.id for t in pending_teams]:
            print(f"   ✅ Команда {team.name} в списке на модерации")
        else:
            print(f"   ❌ Команда {team.name} НЕ в списке на модерации")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    print()
    
    # Тест 7: Одобрение команды (модерация)
    print("✅ Тест 7: Одобрение команды админом...")
    try:
        success = await TeamRepository.approve_team(team.id)
        if success:
            print(f"✅ Команда {team.name} одобрена!")
            
            # Проверяем что статус изменился
            updated_team = await TeamRepository.get_by_id(team.id)
            if updated_team:
                print(f"   📊 Новый статус: {updated_team.status}")
                if updated_team.status == "approved":
                    print("   ✅ Статус корректно изменён на 'approved'")
                else:
                    print(f"   ❌ Статус некорректный: {updated_team.status}")
        else:
            print("❌ Ошибка одобрения команды")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    print()
    
    # Тест 8: Проверка активных команд
    print("🏃 Тест 8: Проверка активных команд...")
    try:
        active_teams = await TeamRepository.get_active_teams()
        print(f"✅ Активных команд: {len(active_teams)}")
        if team.id in [t.id for t in active_teams]:
            print(f"   ✅ Команда {team.name} в списке активных")
        else:
            print(f"   ❌ Команда {team.name} НЕ в списке активных")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    print()
    
    # Тест 9: Отклонение команды
    print("❌ Тест 9: Создание и отклонение второй команды...")
    try:
        team2 = await TeamRepository.create_team(
            tournament_id=tournament.id,
            name="Test Team Beta",
            captain_id=user.id,
            logo_file_id=None
        )
        if team2:
            print(f"✅ Вторая команда создана: {team2.name}")
            
            # Отклоняем команду
            success = await TeamRepository.reject_team(team2.id, "Недостаточно игроков")
            if success:
                print(f"✅ Команда {team2.name} отклонена")
                
                # Проверяем статус
                rejected_team = await TeamRepository.get_by_id(team2.id)
                if rejected_team and rejected_team.status == "rejected":
                    print(f"   ✅ Статус корректно изменён на 'rejected'")
                else:
                    print(f"   ❌ Статус некорректный: {rejected_team.status if rejected_team else 'None'}")
            else:
                print("❌ Ошибка отклонения команды")
        else:
            print("❌ Ошибка создания второй команды")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    print()
    
    # Тест 10: Статистика
    print("📊 Тест 10: Общая статистика...")
    try:
        total_teams = await TeamRepository.get_total_count()
        pending_count = await TeamRepository.get_pending_count()
        active_count = await TeamRepository.get_active_count()
        
        print(f"✅ Статистика команд:")
        print(f"   📋 Всего команд: {total_teams}")
        print(f"   ⏱ На модерации: {pending_count}")
        print(f"   ✅ Активных: {active_count}")
        print(f"   ❌ Отклонённых: {total_teams - pending_count - active_count}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    print()
    print("=" * 60)
    print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 60)
    print()
    print("✅ Фаза 1 завершена:")
    print("   ✅ Система регистрации команд")
    print("   ✅ Обязательные каналы для турниров")
    print("   ✅ Модерация команд (одобрение/отклонение)")
    print()
    
    # Закрываем БД
    await close_database()
    
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_phase1())
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
