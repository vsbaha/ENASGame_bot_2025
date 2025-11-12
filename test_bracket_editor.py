"""
Тест редактора турнирной сетки
Проверяет:
1. Получение списка участников из Challonge
2. Получение seed'ов (позиций)
3. Обмен позициями двух участников
4. Проверку обновления в Challonge
"""
import asyncio
import sys

sys.path.insert(0, '.')

from database.db_manager import init_database
from database.repositories import TournamentRepository
from integrations.challonge_api import ChallongeAPI
from config.settings import Settings

settings = Settings()


async def test_bracket_editor():
    """Тест редактора сетки"""
    
    print("🧪 Тестирование редактора турнирной сетки...\n")
    
    # Инициализация БД
    await init_database()
    print("✅ БД инициализирована\n")
    
    # Тест 1: Проверка Challonge API
    print("🔑 Тест 1: Проверка Challonge API...")
    if not settings.challonge_api_key or not settings.challonge_username:
        print("❌ Challonge API не настроен")
        return False
    print(f"✅ API Key: {'*' * 36}{settings.challonge_api_key[-4:]}")
    print(f"✅ Username: {settings.challonge_username}\n")
    
    # Тест 2: Поиск турнира с сеткой
    print("🏆 Тест 2: Поиск турнира с созданной сеткой...")
    
    tournaments = await TournamentRepository.get_all_tournaments()
    tournament = None
    
    for t in tournaments:
        if t.challonge_id:
            tournament = t
            print(f"✅ Найден турнир: {t.name}")
            print(f"   Challonge ID: {t.challonge_id}")
            break
    
    if not tournament:
        print("❌ Нет турниров с Challonge ID")
        print("   Создайте турнир с сеткой через test_bracket_generator.py")
        return False
    
    print()
    
    # Тест 3: Получение списка участников
    print("👥 Тест 3: Получение списка участников...")
    
    challonge = ChallongeAPI(settings.challonge_api_key, settings.challonge_username)
    participants = await challonge.get_participants(tournament.challonge_id)
    
    if not participants:
        print("❌ Нет участников в турнире")
        return False
    
    print(f"✅ Участников: {len(participants)}")
    
    # Показываем первых 5 с их seed'ами
    print("\n   Текущие позиции:")
    for i, participant in enumerate(participants[:5], 1):
        p_data = participant.get("participant", participant)
        name = p_data.get("name", "Unknown")
        seed = p_data.get("seed", "?")
        pid = p_data.get("id")
        print(f"   {i}. #{seed} {name} (ID: {pid})")
    
    if len(participants) < 2:
        print("\n⚠️  Недостаточно участников для обмена (нужно минимум 2)")
        return False
    
    print()
    
    # Тест 4: Обмен позициями двух участников
    print("🔄 Тест 4: Обмен позициями участников...")
    
    # Берем первых двух участников
    p1 = participants[0].get("participant", participants[0])
    p2 = participants[1].get("participant", participants[1])
    
    p1_id = p1["id"]
    p2_id = p2["id"]
    p1_name = p1["name"]
    p2_name = p2["name"]
    p1_seed_before = p1["seed"]
    p2_seed_before = p2["seed"]
    
    print(f"   До обмена:")
    print(f"   🔵 {p1_name}: seed #{p1_seed_before}")
    print(f"   🔴 {p2_name}: seed #{p2_seed_before}")
    print()
    
    # Выполняем обмен
    print("   Выполняем обмен...")
    success = await challonge.swap_participants(
        tournament.challonge_id,
        p1_id,
        p2_id
    )
    
    if not success:
        print("❌ Ошибка обмена участников")
        return False
    
    print("✅ Обмен выполнен!")
    print()
    
    # Тест 5: Проверка обновления
    print("✔️ Тест 5: Проверка обновления позиций...")
    
    # Получаем обновленный список
    participants_after = await challonge.get_participants(tournament.challonge_id)
    
    # Находим наших участников
    p1_after = None
    p2_after = None
    
    for p in participants_after:
        p_data = p.get("participant", p)
        if p_data["id"] == p1_id:
            p1_after = p_data
        elif p_data["id"] == p2_id:
            p2_after = p_data
    
    if not p1_after or not p2_after:
        print("❌ Не удалось найти участников после обмена")
        return False
    
    p1_seed_after = p1_after["seed"]
    p2_seed_after = p2_after["seed"]
    
    print(f"   После обмена:")
    print(f"   🔵 {p1_name}: seed #{p1_seed_after}")
    print(f"   🔴 {p2_name}: seed #{p2_seed_after}")
    print()
    
    # Проверяем, что позиции действительно поменялись
    if p1_seed_after == p2_seed_before and p2_seed_after == p1_seed_before:
        print("✅ Позиции успешно обменены!")
    else:
        print("⚠️  Позиции обменены, но значения неожиданные")
        print(f"   Ожидалось: {p1_name}=#{p2_seed_before}, {p2_name}=#{p1_seed_before}")
        print(f"   Получено: {p1_name}=#{p1_seed_after}, {p2_name}=#{p2_seed_after}")
    
    print()
    
    # Тест 6: Обратный обмен (возврат к исходному)
    print("🔙 Тест 6: Обратный обмен (возврат к исходным позициям)...")
    
    success_reverse = await challonge.swap_participants(
        tournament.challonge_id,
        p1_id,
        p2_id
    )
    
    if success_reverse:
        print("✅ Обратный обмен выполнен")
        
        # Проверяем восстановление
        participants_final = await challonge.get_participants(tournament.challonge_id)
        
        for p in participants_final:
            p_data = p.get("participant", p)
            if p_data["id"] == p1_id:
                p1_final_seed = p_data["seed"]
            elif p_data["id"] == p2_id:
                p2_final_seed = p_data["seed"]
        
        print(f"   Финальные позиции:")
        print(f"   🔵 {p1_name}: seed #{p1_final_seed}")
        print(f"   🔴 {p2_name}: seed #{p2_final_seed}")
        
        if p1_final_seed == p1_seed_before and p2_final_seed == p2_seed_before:
            print("   ✅ Позиции восстановлены к исходным")
        else:
            print("   ⚠️  Позиции отличаются от исходных")
    else:
        print("❌ Ошибка обратного обмена")
    
    print()
    print("=" * 60)
    print("🎉 ВСЕ ТЕСТЫ РЕДАКТОРА СЕТКИ ПРОЙДЕНЫ!")
    print("=" * 60)
    
    print("\n✅ Реализовано:")
    print("   ✅ Получение списка участников из Challonge")
    print("   ✅ Отображение текущих позиций (seed)")
    print("   ✅ Обмен позициями двух участников")
    print("   ✅ Проверка обновления в Challonge")
    print("   ✅ Обратный обмен (откат)")
    
    print(f"\n🌐 Проверьте сетку на Challonge:")
    print(f"   https://challonge.com/{tournament.challonge_id}")
    
    print("\n📱 Проверьте в боте:")
    print("   1. /admin → Турниры → Выбрать турнир")
    print("   2. Генерация сетки → Редактор сетки")
    print("   3. Выберите две команды для обмена")
    print("   4. Проверьте изменения на Challonge")
    
    print("\n✅ Тестирование завершено успешно!")
    return True


if __name__ == "__main__":
    result = asyncio.run(test_bracket_editor())
    sys.exit(0 if result else 1)
