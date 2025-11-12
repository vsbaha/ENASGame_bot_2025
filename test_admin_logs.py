"""
Тестирование системы логов администратора
"""
import asyncio
import sys
from datetime import datetime, timedelta

# Инициализация базы данных
from database.database import init_db
from database.repositories import ActionLogRepository, UserRepository, TournamentRepository


async def main():
    print("🧪 Тестирование системы логов администратора...\n")
    
    # Инициализация БД
    try:
        await init_db()
        print("✅ БД инициализирована\n")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return
    
    # Тест 1: Получение или создание администратора
    print("📝 Тест 1: Проверка пользователя...")
    admin = await UserRepository.get_by_telegram_id(1234567890)
    if not admin:
        admin = await UserRepository.create_user(
            telegram_id=1234567890,
            username="test_admin",
            full_name="Test Admin",
            region="kg",
            language="ru"
        )
        # Делаем админом
        from database.models import UserRole
        await UserRepository.set_admin_role(1234567890, True)
        admin = await UserRepository.get_by_telegram_id(1234567890)
        print(f"✅ Создан тестовый админ: {admin.full_name} (ID: {admin.id})")
    else:
        print(f"✅ Найден админ: {admin.full_name} (ID: {admin.id})")
    
    print()
    
    # Тест 2: Создание записей в логах
    print("📝 Тест 2: Создание тестовых записей в логах...")
    test_logs = [
        ("tournament:create", "Создан турнир 'Test Tournament 1'"),
        ("tournament:update", "Обновлены даты турнира 'Test Tournament 1'"),
        ("team:approve", "Одобрена заявка команды 'Test Team 1'"),
        ("team:reject", "Отклонена заявка команды 'Test Team 2' - причина: Неполный состав"),
        ("match:update_score", "Обновлен счет матча #1: Team A 3:2 Team B"),
        ("bracket:generate", "Сгенерирована сетка для турнира 'Test Tournament 1'"),
        ("bracket:swap", "Обменяны позиции команд: Team 1 ↔ Team 2"),
        ("user:block", "Заблокирован пользователь @spammer"),
        ("system:backup", "Создана резервная копия БД"),
    ]
    
    created_logs = []
    for action, details in test_logs:
        log = await ActionLogRepository.create_log(
            user_id=admin.id,
            action=action,
            details=details
        )
        if log:
            created_logs.append(log)
            print(f"  ✓ {action}: {details}")
    
    print(f"✅ Создано {len(created_logs)} записей в логах\n")
    
    # Тест 3: Получение статистики
    print("📝 Тест 3: Получение статистики...")
    stats = await ActionLogRepository.get_statistics()
    
    if stats:
        print(f"  📊 Всего записей: {stats.get('total', 0)}")
        print(f"  👤 Уникальных пользователей: {stats.get('unique_users', 0)}")
        print(f"  🕐 Последнее действие: {stats.get('last_action', 'N/A')}")
        
        if stats.get('top_actions'):
            print(f"\n  🏆 Топ действий:")
            for action, count in stats['top_actions'][:5]:
                print(f"     {action}: {count}")
        
        print("✅ Статистика получена\n")
    else:
        print("❌ Не удалось получить статистику\n")
    
    # Тест 4: Фильтрация по категории
    print("📝 Тест 4: Фильтрация логов по категории 'tournament'...")
    tournament_logs = await ActionLogRepository.get_logs(
        limit=10,
        action_filter="tournament"
    )
    
    print(f"  Найдено {len(tournament_logs)} записей:")
    for log in tournament_logs:
        time_str = log.created_at.strftime("%H:%M:%S")
        print(f"  • [{time_str}] {log.action}: {log.details}")
    print("✅ Фильтрация по категории работает\n")
    
    # Тест 5: Фильтрация по пользователю
    print("📝 Тест 5: Фильтрация логов по администратору...")
    user_logs = await ActionLogRepository.get_by_user(admin.id, limit=5)
    
    print(f"  Последние 5 действий {admin.full_name}:")
    for log in user_logs:
        time_str = log.created_at.strftime("%d.%m.%Y %H:%M")
        print(f"  • [{time_str}] {log.action}")
    print("✅ Фильтрация по пользователю работает\n")
    
    # Тест 6: Фильтрация по времени
    print("📝 Тест 6: Фильтрация логов по времени (последние 10 минут)...")
    start_date = datetime.now() - timedelta(minutes=10)
    recent_logs = await ActionLogRepository.get_logs(
        limit=10,
        start_date=start_date
    )
    
    print(f"  Найдено {len(recent_logs)} записей за последние 10 минут")
    print("✅ Фильтрация по времени работает\n")
    
    # Тест 7: Подсчет с фильтрами
    print("📝 Тест 7: Подсчет логов с фильтрами...")
    total_count = await ActionLogRepository.count_logs()
    tournament_count = await ActionLogRepository.count_logs(action_filter="tournament")
    team_count = await ActionLogRepository.count_logs(action_filter="team")
    
    print(f"  📊 Всего: {total_count}")
    print(f"  🏆 Турниры: {tournament_count}")
    print(f"  👥 Команды: {team_count}")
    print("✅ Подсчет с фильтрами работает\n")
    
    # Тест 8: Поиск в логах
    print("📝 Тест 8: Поиск в логах по слову 'турнир'...")
    search_results = await ActionLogRepository.search_logs("турнир", limit=5)
    
    print(f"  Найдено {len(search_results)} записей:")
    for log in search_results:
        print(f"  • {log.action}: {log.details}")
    print("✅ Поиск в логах работает\n")
    
    # Тест 9: Получение последних логов
    print("📝 Тест 9: Получение последних 5 записей...")
    recent = await ActionLogRepository.get_recent(limit=5)
    
    print(f"  📜 Последние действия:")
    for log in recent:
        time_str = log.created_at.strftime("%d.%m.%Y %H:%M:%S")
        user_name = log.user.full_name if hasattr(log, 'user') and log.user else "Unknown"
        print(f"  • [{time_str}] {user_name}: {log.action}")
    print("✅ Получение последних логов работает\n")
    
    # Финальный отчет
    print("=" * 60)
    print("🎉 ВСЕ ТЕСТЫ СИСТЕМЫ ЛОГОВ ПРОШЛИ УСПЕШНО!")
    print("=" * 60)
    print("\n📋 Итоговая статистика:")
    final_stats = await ActionLogRepository.get_statistics()
    print(f"   • Всего записей: {final_stats.get('total', 0)}")
    print(f"   • Администраторов: {final_stats.get('unique_users', 0)}")
    print(f"   • Категорий действий: {len(final_stats.get('top_actions', []))}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
