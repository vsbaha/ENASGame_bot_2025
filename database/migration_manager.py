"""
Менеджер миграций базы данных
"""
import os
import importlib.util
import logging
from pathlib import Path
from typing import List, Dict
from sqlalchemy import text
from database.db_manager import get_session

logger = logging.getLogger(__name__)

class MigrationManager:
    """Менеджер для управления миграциями базы данных"""
    
    def __init__(self):
        self.migrations_dir = Path(__file__).parent / "migrations"
        
    async def init_migration_table(self):
        """Инициализация таблицы миграций"""
        async with get_session() as session:
            try:
                create_table_sql = text("""
                    CREATE TABLE IF NOT EXISTS migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await session.execute(create_table_sql)
                await session.commit()
                logger.info("✅ Таблица миграций инициализирована")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации таблицы миграций: {e}")
                raise
    
    async def get_applied_migrations(self) -> List[str]:
        """Получение списка применённых миграций"""
        async with get_session() as session:
            try:
                sql = text("SELECT name FROM migrations ORDER BY name")
                result = await session.execute(sql)
                return [row[0] for row in result.fetchall()]
            except Exception:
                # Если таблица не существует, возвращаем пустой список
                return []
    
    def get_available_migrations(self) -> List[str]:
        """Получение списка доступных миграций"""
        if not self.migrations_dir.exists():
            return []
        
        migrations = []
        for file in self.migrations_dir.glob("*.py"):
            if file.name != "__init__.py":
                migrations.append(file.stem)
        
        return sorted(migrations)
    
    async def apply_migration(self, migration_name: str):
        """Применение конкретной миграции"""
        migration_file = self.migrations_dir / f"{migration_name}.py"
        
        if not migration_file.exists():
            raise FileNotFoundError(f"Миграция {migration_name} не найдена")
        
        # Загружаем модуль миграции
        spec = importlib.util.spec_from_file_location(migration_name, migration_file)
        migration_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_module)
        
        # Применяем миграцию
        logger.info(f"🔄 Применение миграции {migration_name}...")
        await migration_module.upgrade()
        
        # Отмечаем миграцию как применённую
        async with get_session() as session:
            try:
                sql = text("INSERT INTO migrations (name) VALUES (:name)")
                await session.execute(sql, {"name": migration_name})
                await session.commit()
                logger.info(f"✅ Миграция {migration_name} успешно применена")
            except Exception as e:
                logger.error(f"❌ Ошибка записи миграции: {e}")
                raise
    
    async def rollback_migration(self, migration_name: str):
        """Откат конкретной миграции"""
        migration_file = self.migrations_dir / f"{migration_name}.py"
        
        if not migration_file.exists():
            raise FileNotFoundError(f"Миграция {migration_name} не найдена")
        
        # Загружаем модуль миграции
        spec = importlib.util.spec_from_file_location(migration_name, migration_file)
        migration_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_module)
        
        # Откатываем миграцию
        logger.info(f"🔄 Откат миграции {migration_name}...")
        await migration_module.downgrade()
        
        # Удаляем запись о миграции
        async with get_session() as session:
            try:
                sql = text("DELETE FROM migrations WHERE name = :name")
                await session.execute(sql, {"name": migration_name})
                await session.commit()
                logger.info(f"✅ Миграция {migration_name} успешно откачена")
            except Exception as e:
                logger.error(f"❌ Ошибка удаления записи миграции: {e}")
                raise
    
    async def migrate(self):
        """Применение всех неприменённых миграций"""
        await self.init_migration_table()
        
        applied = await self.get_applied_migrations()
        available = self.get_available_migrations()
        
        pending = [m for m in available if m not in applied]
        
        if not pending:
            logger.info("✅ Все миграции уже применены")
            return
        
        logger.info(f"🔄 Найдено {len(pending)} неприменённых миграций")
        
        for migration in pending:
            await self.apply_migration(migration)
        
        logger.info("✅ Все миграции успешно применены")
    
    async def status(self) -> Dict[str, List[str]]:
        """Получение статуса миграций"""
        await self.init_migration_table()
        
        applied = await self.get_applied_migrations()
        available = self.get_available_migrations()
        pending = [m for m in available if m not in applied]
        
        return {
            "applied": applied,
            "pending": pending,
            "available": available
        }

# Глобальный экземпляр менеджера
migration_manager = MigrationManager()

if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("🔄 Применение миграций...")
        try:
            await migration_manager.migrate()
            
            # Показываем статус
            status = await migration_manager.status()
            print(f"\n📊 Статус миграций:")
            print(f"✅ Применено: {len(status['applied'])}")
            print(f"⏳ Ожидает: {len(status['pending'])}")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    asyncio.run(main())