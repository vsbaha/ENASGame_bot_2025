from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from config.settings import settings
from database.models import Base, Game


class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self):
        # Создаем папку для базы данных если её нет
        db_path = Path(settings.database_path)
        db_path.parent.mkdir(exist_ok=True)
        
        # Создаем движок для async SQLite
        database_url = f"sqlite+aiosqlite:///{settings.database_path}"
        self.engine = create_async_engine(
            database_url,
            echo=False,  # Установить True для отладки SQL запросов
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
            },
        )
        
        # Создаем фабрику сессий
        self.async_session = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def init_db(self):
        """Инициализация базы данных"""
        async with self.engine.begin() as conn:
            # Создаем все таблицы
            await conn.run_sync(Base.metadata.create_all)
        
        # Добавляем базовые данные
        await self._insert_default_data()
    
    async def _insert_default_data(self):
        """Вставка базовых данных"""
        async with self.get_session() as session:
            # Проверяем, есть ли уже игры
            result = await session.execute("SELECT COUNT(*) FROM games")
            count = result.scalar()
            
            if count == 0:
                # Добавляем популярные игры
                games = [
                    Game(name="Counter-Strike 2", short_name="CS2", max_players=5, max_substitutes=1),
                    Game(name="Dota 2", short_name="DOTA2", max_players=5, max_substitutes=1),
                    Game(name="Valorant", short_name="VALORANT", max_players=5, max_substitutes=1),
                    Game(name="League of Legends", short_name="LOL", max_players=5, max_substitutes=1),
                    Game(name="Overwatch 2", short_name="OW2", max_players=6, max_substitutes=2),
                    Game(name="Rainbow Six Siege", short_name="R6", max_players=5, max_substitutes=1),
                    Game(name="Rocket League", short_name="RL", max_players=3, max_substitutes=1),
                    Game(name="Apex Legends", short_name="APEX", max_players=3, max_substitutes=0),
                ]
                
                session.add_all(games)
                await session.commit()
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Получение сессии базы данных"""
        async with self.async_session() as session:
            yield session
    
    async def close(self):
        """Закрытие соединения с базой данных"""
        await self.engine.dispose()


# Глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()


async def init_db():
    """Инициализация базы данных"""
    await db_manager.init_db()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Получение сессии базы данных"""
    async with db_manager.async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()