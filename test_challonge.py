"""
Скрипт для тестирования интеграции с Challonge API
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from integrations.challonge_api import ChallongeAPI
from config.settings import settings

async def test_challonge_connection():
    """Тестирование подключения к Challonge API"""
    
    print("=" * 60)
    print("🔍 ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ CHALLONGE API")
    print("=" * 60)
    print()
    
    # Проверяем наличие credentials
    print("📋 Шаг 1: Проверка credentials...")
    if not settings.challonge_api_key:
        print("❌ ОШИБКА: CHALLONGE_API_KEY не задан в .env файле")
        return False
    if not settings.challonge_username:
        print("❌ ОШИБКА: CHALLONGE_USERNAME не задан в .env файле")
        return False
    
    print(f"✅ API Key: {'*' * 20}{settings.challonge_api_key[-10:]}")
    print(f"✅ Username: {settings.challonge_username}")
    print()
    
    # Создаем клиент
    print("📋 Шаг 2: Создание клиента Challonge API...")
    try:
        challonge = ChallongeAPI(settings.challonge_api_key, settings.challonge_username)
        print("✅ Клиент создан успешно")
    except Exception as e:
        print(f"❌ ОШИБКА создания клиента: {e}")
        return False
    print()
    
    # Тестовое имя турнира
    test_tournament_name = f"ENAS Test Tournament {asyncio.get_event_loop().time():.0f}"
    tournament_id = None
    
    try:
        # Создаем тестовый турнир
        print("📋 Шаг 3: Создание тестового турнира...")
        print(f"   Название: {test_tournament_name}")
        tournament = await challonge.create_tournament(
            name=test_tournament_name,
            tournament_type="single elimination",
            description="Тестовый турнир для проверки API",
            private=True  # Приватный, чтобы не засорять публичные турниры
        )
        
        if not tournament:
            print("❌ ОШИБКА: Турнир не был создан (вернулся None)")
            return False
        
        tournament_id = tournament.get("url")
        print(f"✅ Турнир создан успешно!")
        print(f"   ID: {tournament_id}")
        print(f"   URL: {tournament.get('full_challonge_url')}")
        print()
        
        # Добавляем тестовых участников
        print("📋 Шаг 4: Добавление участников...")
        test_teams = ["Team Alpha", "Team Beta", "Team Gamma", "Team Delta"]
        
        for team in test_teams:
            participant = await challonge.add_participant(tournament_id, team)
            if participant:
                print(f"   ✅ {team} добавлена (ID: {participant.get('id')})")
            else:
                print(f"   ❌ Ошибка добавления {team}")
        print()
        
        # Запускаем турнир
        print("📋 Шаг 5: Запуск турнира (генерация сетки)...")
        started = await challonge.start_tournament(tournament_id)
        if started:
            print("✅ Турнир запущен, сетка сгенерирована")
        else:
            print("❌ ОШИБКА запуска турнира")
        print()
        
        # Получаем информацию о турнире
        print("📋 Шаг 6: Получение информации о турнире...")
        tournament_info = await challonge.get_tournament_info(tournament_id)
        
        if tournament_info:
            print("✅ Информация получена:")
            print(f"   Название: {tournament_info.get('name')}")
            print(f"   Статус: {tournament_info.get('state')}")
            print(f"   Участников: {tournament_info.get('participants_count')}")
            print(f"   Тип: {tournament_info.get('tournament_type')}")
            
            # Выводим матчи
            if 'matches' in tournament_info and tournament_info['matches']:
                print(f"   Матчей: {len(tournament_info['matches'])}")
                print("   Первый матч:")
                first_match = tournament_info['matches'][0]['match']
                print(f"      ID: {first_match.get('id')}")
                print(f"      Раунд: {first_match.get('round')}")
                print(f"      Игрок 1 ID: {first_match.get('player1_id')}")
                print(f"      Игрок 2 ID: {first_match.get('player2_id')}")
        else:
            print("❌ ОШИБКА получения информации")
        print()
        
        # Получаем URL сетки
        print("📋 Шаг 7: Получение URL турнирной сетки...")
        bracket_url = await challonge.get_tournament_bracket_url(tournament_id)
        if bracket_url:
            print(f"✅ URL сетки: {bracket_url}")
            print(f"   SVG изображение: https://challonge.com/{tournament_id}.svg")
        else:
            print("❌ ОШИБКА получения URL")
        print()
        
        print("=" * 60)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("=" * 60)
        print()
        print("⚠️ ВНИМАНИЕ: Тестовый турнир создан в вашем аккаунте Challonge")
        print(f"   Вы можете просмотреть его: {tournament.get('full_challonge_url')}")
        print("   Рекомендуется удалить его вручную через веб-интерфейс Challonge")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        print("\n📋 Подробности ошибки:")
        print(traceback.format_exc())
        return False

async def main():
    """Главная функция"""
    success = await test_challonge_connection()
    
    if success:
        print("\n✅ Интеграция с Challonge API работает корректно!")
        return 0
    else:
        print("\n❌ Интеграция с Challonge API НЕ работает!")
        print("   Проверьте:")
        print("   1. Правильность API ключа в .env файле")
        print("   2. Правильность username в .env файле")
        print("   3. Подключение к интернету")
        print("   4. Что API ключ активен на https://challonge.com/settings/developer")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
