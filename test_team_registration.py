"""
Тест системы регистрации команд
"""
import asyncio
import logging
from database.database import init_db
from database.repositories.tournament_repository import TournamentRepository
from database.repositories.team_repository import TeamRepository
from database.repositories.user_repository import UserRepository
from database.models import TournamentStatus, TeamStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_team_registration():
    """Тестирование регистрации команд"""
    
    print("=" * 60)
    print("🧪 ТЕСТ СИСТЕМЫ РЕГИСТРАЦИИ КОМАНД")
    print("=" * 60)
    
    await init_db()
    
    try:
        # Тест 1: Получаем активные турниры
        print("\n" + "━" * 60)
        print("ТЕСТ 1: Получение активных турниров")
        print("━" * 60)
        
        tournaments = await TournamentRepository.get_active_tournaments()
        print(f"✅ Найдено активных турниров: {len(tournaments)}")
        
        for tournament in tournaments:
            print(f"\n🏆 {tournament.name}")
            print(f"   📋 Формат: {tournament.format}")
            print(f"   🎮 Игра: {tournament.game.name}")
            print(f"   👥 Макс команд: {tournament.max_teams}")
            print(f"   📢 Обязательных каналов: {len(tournament.required_channels_list)}")
            
            if tournament.required_channels_list:
                for channel in tournament.required_channels_list:
                    print(f"      • {channel}")
        
        # Тест 2: Проверяем пользователя
        print("\n" + "━" * 60)
        print("ТЕСТ 2: Проверка тестового пользователя")
        print("━" * 60)
        
        test_telegram_id = 1189473577
        user = await UserRepository.get_by_telegram_id(test_telegram_id)
        
        if user:
            print(f"✅ Пользователь найден: {user.full_name}")
            print(f"   ID в БД: {user.id}")
            print(f"   Telegram ID: {user.telegram_id}")
        else:
            print("❌ Пользователь не найден")
            return
        
        # Тест 3: Проверяем команды пользователя
        print("\n" + "━" * 60)
        print("ТЕСТ 3: Команды пользователя")
        print("━" * 60)
        
        teams = await TeamRepository.get_teams_by_captain(user.id)
        print(f"✅ Команд у пользователя: {len(teams)}")
        
        for team in teams:
            status_emoji = {
                TeamStatus.PENDING.value: "⏳",
                TeamStatus.APPROVED.value: "✅",
                TeamStatus.REJECTED.value: "❌"
            }.get(team.status, "❓")
            
            print(f"\n{status_emoji} {team.name}")
            print(f"   🏆 Турнир: {team.tournament.name}")
            print(f"   🎮 Игра: {team.tournament.game.name}")
            print(f"   📊 Статус: {team.status}")
        
        # Тест 4: Проверяем возможность регистрации
        print("\n" + "━" * 60)
        print("ТЕСТ 4: Проверка возможности регистрации")
        print("━" * 60)
        
        if tournaments:
            tournament = tournaments[0]
            
            # Проверяем, зарегистрирован ли уже
            is_registered = await TeamRepository.is_captain_registered(user.id, tournament.id)
            print(f"\nТурнир: {tournament.name}")
            print(f"Уже зарегистрирован: {'Да' if is_registered else 'Нет'}")
            
            # Проверяем заполненность
            teams_count = await TeamRepository.get_approved_teams_count(tournament.id)
            print(f"Заполнено мест: {teams_count}/{tournament.max_teams}")
            
            # Проверяем статус турнира
            print(f"Статус турнира: {tournament.status}")
            print(f"Регистрация открыта: {'Да' if tournament.status == TournamentStatus.REGISTRATION.value else 'Нет'}")
            
            # Проверяем обязательные каналы
            if tournament.required_channels_list:
                print(f"\n⚠️ Требуется подписка на каналы:")
                for channel in tournament.required_channels_list:
                    print(f"   • {channel}")
            else:
                print("\n✅ Подписка на каналы не требуется")
        
        print("\n" + "=" * 60)
        print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
        print("=" * 60)
        
        # Итоговая информация
        print("\n📊 ИТОГОВАЯ СТАТИСТИКА:")
        print(f"   • Активных турниров: {len(tournaments)}")
        print(f"   • Команд пользователя: {len(teams)}")
        
        if tournaments:
            can_register = []
            for t in tournaments:
                is_reg = await TeamRepository.is_captain_registered(user.id, t.id)
                count = await TeamRepository.get_approved_teams_count(t.id)
                if not is_reg and count < t.max_teams and t.status == TournamentStatus.REGISTRATION.value:
                    can_register.append(t.name)
            
            print(f"   • Доступно для регистрации: {len(can_register)}")
            if can_register:
                print(f"\n   Можно зарегистрироваться на:")
                for name in can_register:
                    print(f"      ✓ {name}")
        
    except Exception as e:
        logger.error(f"Ошибка теста: {e}", exc_info=True)
        print(f"\n❌ Ошибка выполнения теста: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(test_team_registration())
    except KeyboardInterrupt:
        print("\n\n⏹️ Тест прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
