"""
Проверка проблемы с каналами
"""
import asyncio
import json
from database.database import init_db, get_session
from database.repositories.tournament_repository import TournamentRepository


async def test_channels():
    """Тестирование проблемы с каналами"""
    
    print("=" * 60)
    print("🔍 ПРОВЕРКА ОБЯЗАТЕЛЬНЫХ КАНАЛОВ")
    print("=" * 60)
    
    # Инициализация БД
    await init_db()
    
    # Получаем все турниры
    tournaments = await TournamentRepository.get_all()
    
    for tournament in tournaments:
        print(f"\n📋 Турнир: {tournament.name} (ID: {tournament.id})")
        print(f"   Статус: {tournament.status}")
        
        # Проверяем RAW значение из БД
        raw_channels = tournament.required_channels
        print(f"   RAW из БД: {repr(raw_channels)}")
        print(f"   Тип: {type(raw_channels)}")
        
        # Проверяем property
        channels_list = tournament.required_channels_list
        print(f"   Property list: {channels_list}")
        print(f"   Тип: {type(channels_list)}")
        
        if channels_list:
            print(f"   Количество каналов: {len(channels_list)}")
            for i, channel in enumerate(channels_list, 1):
                print(f"     {i}. {repr(channel)} (тип: {type(channel)})")
        
        # Попробуем распарсить вручную
        try:
            parsed = json.loads(raw_channels or "[]")
            print(f"   JSON.loads: {parsed}")
            print(f"   Тип после парсинга: {type(parsed)}")
        except Exception as e:
            print(f"   ❌ Ошибка парсинга: {e}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_channels())
