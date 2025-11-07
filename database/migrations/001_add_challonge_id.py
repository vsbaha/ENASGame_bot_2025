"""
Миграция: Добавление поля challonge_id в таблицу tournaments
Дата: 2025-09-30
"""
import logging
from sqlalchemy import text
from database.db_manager import get_session

logger = logging.getLogger(__name__)

async def upgrade():
    """Применение миграции"""
    async with get_session() as session:
        try:
            # Проверяем, существует ли уже колонка
            check_sql = text("""
                SELECT COUNT(*) 
                FROM pragma_table_info('tournaments') 
                WHERE name = 'challonge_id'
            """)
            result = await session.execute(check_sql)
            exists = result.scalar() > 0
            
            if not exists:
                # Добавляем колонку challonge_id
                alter_sql = text("""
                    ALTER TABLE tournaments 
                    ADD COLUMN challonge_id VARCHAR(100) NULL
                """)
                await session.execute(alter_sql)
                await session.commit()
                logger.info("✅ Добавлена колонка challonge_id в таблицу tournaments")
            else:
                logger.info("ℹ️ Колонка challonge_id уже существует в таблице tournaments")
                
        except Exception as e:
            logger.error(f"❌ Ошибка миграции: {e}")
            await session.rollback()
            raise

async def downgrade():
    """Откат миграции"""
    async with get_session() as session:
        try:
            # Создаем временную таблицу без challonge_id
            create_temp_sql = text("""
                CREATE TABLE tournaments_temp AS 
                SELECT 
                    id, game_id, name, description, format, max_teams, 
                    region, status, registration_start, registration_end, 
                    tournament_start, edit_deadline, logo_file_id, 
                    rules_text, required_channels, created_by, 
                    created_at, updated_at
                FROM tournaments
            """)
            await session.execute(create_temp_sql)
            
            # Удаляем старую таблицу
            drop_sql = text("DROP TABLE tournaments")
            await session.execute(drop_sql)
            
            # Переименовываем временную таблицу
            rename_sql = text("ALTER TABLE tournaments_temp RENAME TO tournaments")
            await session.execute(rename_sql)
            
            await session.commit()
            logger.info("✅ Откат миграции выполнен - колонка challonge_id удалена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отката миграции: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("🔄 Применение миграции...")
        try:
            await upgrade()
            print("✅ Миграция успешно применена!")
        except Exception as e:
            print(f"❌ Ошибка миграции: {e}")
    
    asyncio.run(main())