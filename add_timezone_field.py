"""
Скрипт для добавления поля timezone в таблицу users
"""
import asyncio
import sqlite3
from pathlib import Path


async def add_timezone_field():
    """Добавляет поле timezone в таблицу users"""
    db_path = Path("tournament_bot.db")
    
    if not db_path.exists():
        print("❌ База данных не найдена!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже поле timezone
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'timezone' in columns:
            print("✅ Поле timezone уже существует в таблице users")
        else:
            # Добавляем поле timezone
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Bishkek'
            """)
            conn.commit()
            print("✅ Поле timezone успешно добавлено в таблицу users")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении поля: {e}")


if __name__ == "__main__":
    asyncio.run(add_timezone_field())
