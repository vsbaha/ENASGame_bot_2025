"""
Управление базой данных
"""

from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from settings import config
from database.models import Base


class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self):
        # Создаем папку для базы данных если её нет
        db_path = Path("tournament_bot.db")
        db_path.parent.mkdir(exist_ok=True)
        
        # Создаем движок для async SQLite
        self.engine = create_async_engine(
            config.DB_URL,
            echo=False,  # Установить True для отладки SQL запросов
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
            }
        )
        
        # Создаем фабрику сессий
        self.async_session = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def init_database(self):
        """Инициализация базы данных"""
        async with self.engine.begin() as conn:
            # Создаем все таблицы
            await conn.run_sync(Base.metadata.create_all)
    
    async def close(self):
        """Закрытие соединения с базой данных"""
        await self.engine.dispose()


# Глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()


async def init_database():
    """Инициализация базы данных"""
    await db_manager.init_database()


class DatabaseSession:
    """Контекстный менеджер для работы с сессией базы данных"""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = db_manager.async_session()
        return await self.session.__aenter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            result = await self.session.__aexit__(exc_type, exc_val, exc_tb)
            return result


def get_session():
    """Получение сессии базы данных"""
    return DatabaseSession()


async def close_database():
    """Закрытие базы данных"""
    await db_manager.close()