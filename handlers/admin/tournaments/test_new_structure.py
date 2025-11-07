"""
Тестовый скрипт для проверки новой структуры модулей турниров
"""
import sys
import os

# Добавляем корневую папку проекта в путь
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

def test_new_structure():
    """Тестируем новую структуру импортов"""
    try:
        print("🔍 Тестирование новой структуры модулей турниров...")
        
        # Тестируем основной модуль
        from handlers.admin import tournaments
        print("✅ Основной модуль tournaments импортирован")
        
        # Тестируем подмодули из папки tournaments
        from handlers.admin.tournaments import tournament_management
        print("✅ Модуль tournament_management импортирован")
        
        from handlers.admin.tournaments import tournament_creation
        print("✅ Модуль tournament_creation импортирован")
        
        from handlers.admin.tournaments import tournament_editing
        print("✅ Модуль tournament_editing импортирован")
        
        from handlers.admin.tournaments import tournament_statistics
        print("✅ Модуль tournament_statistics импортирован")
        
        # Проверяем наличие роутеров
        print("\n🔧 Проверяем роутеры...")
        
        if hasattr(tournaments, 'router'):
            print("✅ Основной router найден")
        else:
            print("❌ Основной router не найден")
            
        if hasattr(tournament_management, 'router'):
            print("✅ Router tournament_management найден")
        else:
            print("❌ Router tournament_management не найден")
            
        if hasattr(tournament_creation, 'router'):
            print("✅ Router tournament_creation найден")
        else:
            print("❌ Router tournament_creation не найден")
            
        if hasattr(tournament_editing, 'router'):
            print("✅ Router tournament_editing найден")
        else:
            print("❌ Router tournament_editing не найден")
            
        if hasattr(tournament_statistics, 'router'):
            print("✅ Router tournament_statistics найден")
        else:
            print("❌ Router tournament_statistics не найден")
        
        print("\n✅ Все проверки пройдены! Новая структура работает корректно.")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def show_new_structure():
    """Показывает новую структуру"""
    print("\n📁 Новая структура:")
    print("📂 handlers/admin/")
    print("├── tournaments.py (главный модуль-прокси)")
    print("└── 📂 tournaments/")
    print("    ├── __init__.py (координатор)")
    print("    ├── tournament_management.py (управление)")
    print("    ├── tournament_creation.py (создание)")
    print("    ├── tournament_editing.py (редактирование)")
    print("    ├── tournament_statistics.py (статистика)")
    print("    ├── tournaments_backup.py (резервная копия)")
    print("    └── tournaments_old.py (старый файл)")

if __name__ == "__main__":
    print("🏆 Тест новой структуры модулей турниров")
    print("=" * 60)
    
    show_new_structure()
    print()
    
    success = test_new_structure()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Тестирование завершено успешно!")
        print("📋 Новая структура готова к использованию.")
    else:
        print("⚠️ Обнаружены проблемы с новой структурой.")
        print("📋 Требуется дополнительная настройка.")