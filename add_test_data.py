"""
Скрипт для добавления тестовых данных в базу данных
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from database.models import (
    Base, Game, Tournament, Team, Player, User,
    TournamentStatus, TournamentFormat, TeamStatus
)
from config.settings import settings


async def add_test_data():
    """Добавление тестовых данных для проверки функционала"""
    
    # Создаем движок и сессию
    database_url = f"sqlite+aiosqlite:///{settings.database_path}"
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("📝 Подключаемся к базе данных...\n")
    
    async with async_session() as session:
        try:
            # 1. Проверяем/создаем тестовую игру
            print("📝 Создаем тестовую игру...")
            
            # Ищем существующую игру
            from sqlalchemy import select
            result = await session.execute(
                select(Game).where(Game.short_name == "TEST")
            )
            test_game = result.scalar_one_or_none()
            
            if not test_game:
                test_game = Game(
                    name="Тестовая игра",
                    short_name="TEST",
                    max_players=5,
                    max_substitutes=2
                )
                session.add(test_game)
                await session.flush()
                print(f"✅ Создана игра: {test_game.name} (ID: {test_game.id})")
            else:
                print(f"ℹ️ Игра уже существует: {test_game.name} (ID: {test_game.id})")
            
            # 2. Получаем или создаём тестового администратора
            print("\n📝 Ищем администратора...")
            result = await session.execute(
                select(User).where(User.telegram_id == 999999999)
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                print("📝 Создаём тестового администратора...")
                admin = User(
                    telegram_id=999999999,
                    username="test_admin",
                    full_name="Тестовый Администратор",
                    role="admin",
                    region="kg",
                    language="ru",
                    timezone="Asia/Bishkek",
                    is_blocked=False
                )
                session.add(admin)
                await session.flush()
                print(f"✅ Создан администратор: {admin.full_name} (ID: {admin.id})")
            else:
                print(f"✅ Найден администратор: {admin.full_name} (ID: {admin.id})")
            
            # 3. Создаем тестовый турнир
            print("\n📝 Создаем тестовый турнир...")
            
            now = datetime.utcnow()
            test_tournament = Tournament(
                game_id=test_game.id,
                name="Тестовый турнир 8 команд",
                description="Турнир для тестирования управления сеткой и матчами",
                format=TournamentFormat.SINGLE_ELIMINATION.value,
                max_teams=8,
                region="kg",
                status=TournamentStatus.IN_PROGRESS.value,
                registration_start=now - timedelta(days=7),
                registration_end=now - timedelta(days=1),
                tournament_start=now,
                edit_deadline=now + timedelta(days=7),
                created_by=admin.id
            )
            session.add(test_tournament)
            await session.flush()
            print(f"✅ Создан турнир: {test_tournament.name} (ID: {test_tournament.id})")
            
            # 4. Создаем 8 тестовых команд
            print("\n📝 Создаем тестовые команды...")
            
            team_names = [
                "Team Alpha", "Team Beta", "Team Gamma", "Team Delta",
                "Team Epsilon", "Team Zeta", "Team Eta", "Team Theta"
            ]
            
            teams = []
            for i, team_name in enumerate(team_names, 1):
                team = Team(
                    tournament_id=test_tournament.id,
                    name=team_name,
                    captain_id=admin.id,
                    status=TeamStatus.APPROVED.value
                )
                session.add(team)
                await session.flush()
                teams.append(team)
                print(f"  ✅ Создана команда {i}/8: {team.name} (ID: {team.id})")
                
                # Добавляем игроков в команду
                for j in range(1, test_game.max_players + 1):
                    player = Player(
                        team_id=team.id,
                        nickname=f"{team_name}_Player{j}",
                        game_id=f"test_player_{team.id}_{j}",
                        is_substitute=False,
                        position=j
                    )
                    session.add(player)
                
                # Добавляем запасных
                for j in range(1, test_game.max_substitutes + 1):
                    player = Player(
                        team_id=team.id,
                        nickname=f"{team_name}_Sub{j}",
                        game_id=f"test_sub_{team.id}_{j}",
                        is_substitute=True,
                        position=test_game.max_players + j
                    )
                    session.add(player)
            
            await session.commit()
            
            print("\n" + "="*60)
            print("✅ ТЕСТОВЫЕ ДАННЫЕ УСПЕШНО ДОБАВЛЕНЫ!")
            print("="*60)
            print(f"\n📊 Создано:")
            print(f"   • Игра: {test_game.name}")
            print(f"   • Турнир: {test_tournament.name}")
            print(f"   • Команд: {len(teams)}")
            print(f"   • Игроков в каждой команде: {test_game.max_players}")
            print(f"   • Запасных в каждой команде: {test_game.max_substitutes}")
            print("\n💡 Теперь вы можете:")
            print("   1. Сгенерировать сетку турнира через админ-панель")
            print("   2. Управлять матчами")
            print("   3. Вводить результаты матчей")
            print("\n🎮 Запустите бота и перейдите в:")
            print("   Админ панель → Управление турнирами → Выберите турнир → Сгенерировать сетку")
            
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("🚀 Запуск скрипта добавления тестовых данных...\n")
    asyncio.run(add_test_data())
