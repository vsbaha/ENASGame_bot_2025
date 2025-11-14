

import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.models import Game, Tournament, Team, Player, User, TournamentStatus, TournamentFormat, TeamStatus
from sqlalchemy import select, text


async def main():
    print("🚀 Запуск скрипта добавления тестовых данных...\n")
    
    # Используем правильный путь к базе данных (как в main.py)
    database_url = "sqlite+aiosqlite:///./tournament_bot.db"
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("✅ Подключились к базе данных tournament_bot.db\n")
    
    async with async_session_maker() as session:
        try:
            # 1. Ищем или создаем тестовую игру
            print("📝 Ищем тестовую игру...")
            result = await session.execute(
                select(Game).where(Game.short_name == "TEST")
            )
            test_game = result.scalar_one_or_none()
            
            if not test_game:
                print("📝 Создаём тестовую игру...")
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
                print(f"ℹ️  Игра уже существует: {test_game.name} (ID: {test_game.id})")
            
            # 2. Ищем любого администратора
            print("\n📝 Ищем администратора...")
            result = await session.execute(
                select(User).where(User.role == "admin").limit(1)
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                print("❌ Администратор не найден!")
                print("💡 Запустите бота и войдите в него как администратор, затем повторите этот скрипт.")
                return
            
            print(f"✅ Найден администратор: {admin.full_name} (Telegram ID: {admin.telegram_id})")
            
            # 3. Создаем тестовый турнир
            print("\n📝 Создаем тестовый турнир...")
            
            now = datetime.utcnow()
            test_tournament = Tournament(
                game_id=test_game.id,
                name="Тестовый турнир 8 команд",
                description="Турнир для тестирования управления сеткой и матчами",
                format=TournamentFormat.SINGLE_ELIMINATION.value,
                max_teams=8,
                region=admin.region,
                status=TournamentStatus.REGISTRATION.value,  # Статус "регистрация" чтобы показать кнопку генерации сетки
                registration_start=now - timedelta(days=7),
                registration_end=now + timedelta(days=7),  # Регистрация еще открыта
                tournament_start=now + timedelta(days=10),  # Турнир начнется через 10 дней
                edit_deadline=now + timedelta(days=14),
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
                
                # Добавляем основных игроков
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
            print(f"   • Турнир: {test_tournament.name} (ID: {test_tournament.id})")
            print(f"   • Команд: {len(teams)}")
            print(f"   • Игроков в каждой команде: {test_game.max_players}")
            print(f"   • Запасных в каждой команде: {test_game.max_substitutes}")
            print("\n💡 Теперь вы можете:")
            print("   1. Запустить бота")
            print("   2. Перейти в Админ панель → Управление турнирами")
            print(f"   3. Выбрать турнир '{test_tournament.name}'")
            print("   4. Нажать '🎯 Генерация сетки' (турнир в статусе 'Регистрация')")
            print("   5. После генерации нажать '🏁 Запустить турнир'")
            print("   6. Управлять матчами через '🎮 Управление матчами'")
            
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
