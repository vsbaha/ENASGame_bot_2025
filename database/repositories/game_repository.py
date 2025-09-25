from typing import Optional, List
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_manager import get_session
from database.models import Game


class GameRepository:
    """Репозиторий для работы с играми"""
    
    @staticmethod
    async def create_game(
        name: str,
        short_name: str,
        max_players: int,
        max_substitutes: int = 0,
        icon_file_id: Optional[str] = None
    ) -> Optional[Game]:
        """Создание новой игры"""
        async with get_session() as session:
            session: AsyncSession
            
            game = Game(
                name=name,
                short_name=short_name,
                max_players=max_players,
                max_substitutes=max_substitutes,
                icon_file_id=icon_file_id
            )
            
            session.add(game)
            await session.commit()
            await session.refresh(game)
            
            return game
    
    @staticmethod
    async def get_by_id(game_id: int) -> Optional[Game]:
        """Получение игры по ID"""
        async with get_session() as session:
            session: AsyncSession
            
            return await session.get(Game, game_id)
    
    @staticmethod
    async def get_by_short_name(short_name: str) -> Optional[Game]:
        """Получение игры по короткому названию"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(Game).where(Game.short_name == short_name)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_games() -> List[Game]:
        """Получение всех игр"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(Game).order_by(Game.name.asc())
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def update_game(
        game_id: int,
        name: Optional[str] = None,
        short_name: Optional[str] = None,
        max_players: Optional[int] = None,
        max_substitutes: Optional[int] = None,
        icon_file_id: Optional[str] = None
    ) -> bool:
        """Обновление игры"""
        async with get_session() as session:
            session: AsyncSession
            
            game = await session.get(Game, game_id)
            if not game:
                return False
            
            if name is not None:
                game.name = name
            if short_name is not None:
                game.short_name = short_name
            if max_players is not None:
                game.max_players = max_players
            if max_substitutes is not None:
                game.max_substitutes = max_substitutes
            if icon_file_id is not None:
                game.icon_file_id = icon_file_id
            
            await session.commit()
            return True
    
    @staticmethod
    async def delete_game(game_id: int) -> bool:
        """Удаление игры"""
        async with get_session() as session:
            session: AsyncSession
            
            game = await session.get(Game, game_id)
            if game:
                await session.delete(game)
                await session.commit()
                return True
            
            return False
    
    @staticmethod
    async def is_short_name_taken(short_name: str, exclude_game_id: Optional[int] = None) -> bool:
        """Проверка занятости короткого названия"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(Game).where(Game.short_name == short_name)
            
            if exclude_game_id:
                stmt = stmt.where(Game.id != exclude_game_id)
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def get_games_count() -> int:
        """Получение количества игр"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Game.id))
            result = await session.execute(stmt)
            return result.scalar() or 0