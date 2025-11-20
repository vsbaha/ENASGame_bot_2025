"""
Миграция: добавление полей для блокировки команд
Дата: 2025-11-20
"""
import asyncio
from sqlalchemy import text
from database.db_manager import get_session


async def migrate():
    """Добавляет поля для системы блокировки команд"""
    async with get_session() as session:
        try:
            # Проверяем существование колонок и добавляем их по одной
            # SQLite не поддерживает IF NOT EXISTS в ALTER TABLE
            columns_to_add = [
                ("block_reason", "TEXT"),
                ("block_scope", "VARCHAR(20)"),
                ("blocked_by", "INTEGER"),
                ("blocked_at", "TIMESTAMP")
            ]
            
            for column_name, column_type in columns_to_add:
                try:
                    await session.execute(text(f"""
                        ALTER TABLE teams ADD COLUMN {column_name} {column_type}
                    """))
                    print(f"✅ Добавлена колонка {column_name}")
                except Exception as col_error:
                    if "duplicate column name" in str(col_error).lower():
                        print(f"⚠️ Колонка {column_name} уже существует")
                    else:
                        raise
            
            await session.commit()
            print("✅ Миграция успешно применена: добавлены поля блокировки команд")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка миграции: {e}")
            raise


async def rollback():
    """Откатывает миграцию"""
    async with get_session() as session:
        try:
            await session.execute(text("""
                ALTER TABLE teams 
                DROP COLUMN IF EXISTS block_reason,
                DROP COLUMN IF EXISTS block_scope,
                DROP COLUMN IF EXISTS blocked_by,
                DROP COLUMN IF EXISTS blocked_at
            """))
            
            await session.commit()
            print("✅ Откат миграции выполнен успешно")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка отката миграции: {e}")
            raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(rollback())
    else:
        asyncio.run(migrate())
