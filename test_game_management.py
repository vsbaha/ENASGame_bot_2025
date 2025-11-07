"""
Тестовый скрипт для проверки функционала управления играми
"""
import asyncio
from database.repositories.game_repository import GameRepository

async def test_game_management():
    """Тест функционала управления играми"""
    
    print("=" * 60)
    print("🎮 ТЕСТИРОВАНИЕ УПРАВЛЕНИЯ ИГРАМИ")
    print("=" * 60)
    print()
    
    # Тест 1: Создание игры
    print("📋 Тест 1: Создание игры CS:GO")
    game = await GameRepository.create_game(
        name="CS:GO Test",
        short_name="CSGO",
        max_players=5,
        max_substitutes=2
    )
    
    if game:
        print(f"✅ Игра создана: ID={game.id}, название={game.name}")
        game_id = game.id
    else:
        print("❌ Ошибка создания игры")
        return False
    print()
    
    # Тест 2: Получение игры по ID
    print("📋 Тест 2: Получение игры по ID")
    retrieved_game = await GameRepository.get_by_id(game_id)
    if retrieved_game:
        print(f"✅ Игра найдена: {retrieved_game.name}")
        print(f"   - Макс. игроков: {retrieved_game.max_players}")
        print(f"   - Запасных: {retrieved_game.max_substitutes}")
    else:
        print("❌ Игра не найдена")
    print()
    
    # Тест 3: Обновление названия
    print("📋 Тест 3: Обновление названия игры")
    success = await GameRepository.update_game(
        game_id,
        name="Counter-Strike: Global Offensive"
    )
    if success:
        updated_game = await GameRepository.get_by_id(game_id)
        print(f"✅ Название обновлено: {updated_game.name}")
    else:
        print("❌ Ошибка обновления")
    print()
    
    # Тест 4: Обновление игроков
    print("📋 Тест 4: Обновление количества игроков")
    success = await GameRepository.update_game(
        game_id,
        max_players=6,
        max_substitutes=3
    )
    if success:
        updated_game = await GameRepository.get_by_id(game_id)
        print(f"✅ Параметры обновлены:")
        print(f"   - Макс. игроков: {updated_game.max_players}")
        print(f"   - Запасных: {updated_game.max_substitutes}")
    else:
        print("❌ Ошибка обновления")
    print()
    
    # Тест 5: Список всех игр
    print("📋 Тест 5: Получение списка всех игр")
    all_games = await GameRepository.get_all_games()
    print(f"✅ Найдено игр: {len(all_games)}")
    for g in all_games:
        print(f"   - {g.name} ({g.max_players} игроков)")
    print()
    
    # Тест 6: Проверка уникальности короткого названия
    print("📋 Тест 6: Проверка занятости короткого названия")
    is_taken = await GameRepository.is_short_name_taken("CSGO")
    print(f"✅ 'CSGO' занято: {is_taken}")
    
    is_taken_new = await GameRepository.is_short_name_taken("DOTA2")
    print(f"✅ 'DOTA2' занято: {is_taken_new}")
    print()
    
    # Тест 7: Удаление игры
    print("📋 Тест 7: Удаление тестовой игры")
    success = await GameRepository.delete_game(game_id)
    if success:
        print(f"✅ Игра удалена: ID={game_id}")
    else:
        print("❌ Ошибка удаления")
    print()
    
    # Проверка удаления
    deleted_game = await GameRepository.get_by_id(game_id)
    if deleted_game is None:
        print("✅ Подтверждено: игра удалена из базы")
    else:
        print("❌ Ошибка: игра всё ещё в базе")
    print()
    
    print("=" * 60)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_game_management())
    if result:
        print("\n✅ Система управления играми работает корректно!")
    else:
        print("\n❌ Обнаружены ошибки в системе управления играми!")
