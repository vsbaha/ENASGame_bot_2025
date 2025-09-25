from typing import Optional, List
from sqlalchemy import select, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_manager import get_session
from database.models import Player, Team


class PlayerRepository:
    """Репозиторий для работы с игроками"""
    
    @staticmethod
    async def add_player(
        team_id: int,
        nickname: str,
        game_id: str,
        is_substitute: bool = False,
        position: Optional[int] = None
    ) -> Optional[Player]:
        """Добавление игрока в команду"""
        async with get_session() as session:
            session: AsyncSession
            
            # Определяем позицию если не указана
            if position is None:
                stmt = select(func.max(Player.position)).where(Player.team_id == team_id)
                result = await session.execute(stmt)
                max_position = result.scalar() or 0
                position = max_position + 1
            
            player = Player(
                team_id=team_id,
                nickname=nickname,
                game_id=game_id,
                is_substitute=is_substitute,
                position=position
            )
            
            session.add(player)
            await session.commit()
            await session.refresh(player)
            
            return player
    
    @staticmethod
    async def get_team_players(team_id: int) -> List[Player]:
        """Получение всех игроков команды"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Player)
                .where(Player.team_id == team_id)
                .order_by(Player.is_substitute.asc(), Player.position.asc())
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_main_players(team_id: int) -> List[Player]:
        """Получение основных игроков команды"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Player)
                .where(and_(Player.team_id == team_id, Player.is_substitute == False))
                .order_by(Player.position.asc())
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_substitute_players(team_id: int) -> List[Player]:
        """Получение запасных игроков команды"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Player)
                .where(and_(Player.team_id == team_id, Player.is_substitute == True))
                .order_by(Player.position.asc())
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def remove_player(player_id: int) -> bool:
        """Удаление игрока"""
        async with get_session() as session:
            session: AsyncSession
            
            player = await session.get(Player, player_id)
            if player:
                await session.delete(player)
                await session.commit()
                return True
            
            return False
    
    @staticmethod
    async def clear_team_players(team_id: int) -> bool:
        """Очистка всех игроков команды"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = delete(Player).where(Player.team_id == team_id)
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    @staticmethod
    async def is_nickname_taken_in_tournament(tournament_id: int, nickname: str, exclude_team_id: Optional[int] = None) -> bool:
        """Проверка занятости никнейма в турнире"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Player)
                .join(Team)
                .where(
                    and_(
                        Team.tournament_id == tournament_id,
                        Player.nickname == nickname
                    )
                )
            )
            
            if exclude_team_id:
                stmt = stmt.where(Team.id != exclude_team_id)
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def is_game_id_taken_in_tournament(tournament_id: int, game_id: str, exclude_team_id: Optional[int] = None) -> bool:
        """Проверка занятости игрового ID в турнире"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Player)
                .join(Team)
                .where(
                    and_(
                        Team.tournament_id == tournament_id,
                        Player.game_id == game_id
                    )
                )
            )
            
            if exclude_team_id:
                stmt = stmt.where(Team.id != exclude_team_id)
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def update_player(
        player_id: int,
        nickname: Optional[str] = None,
        game_id: Optional[str] = None,
        is_substitute: Optional[bool] = None,
        position: Optional[int] = None
    ) -> bool:
        """Обновление информации об игроке"""
        async with get_session() as session:
            session: AsyncSession
            
            player = await session.get(Player, player_id)
            if not player:
                return False
            
            if nickname is not None:
                player.nickname = nickname
            if game_id is not None:
                player.game_id = game_id
            if is_substitute is not None:
                player.is_substitute = is_substitute
            if position is not None:
                player.position = position
            
            await session.commit()
            return True
    
    @staticmethod
    async def get_team_players_count(team_id: int) -> dict:
        """Получение количества игроков в команде"""
        async with get_session() as session:
            session: AsyncSession
            
            # Основные игроки
            main_stmt = select(func.count(Player.id)).where(
                and_(Player.team_id == team_id, Player.is_substitute == False)
            )
            main_result = await session.execute(main_stmt)
            main_count = main_result.scalar() or 0
            
            # Запасные игроки
            sub_stmt = select(func.count(Player.id)).where(
                and_(Player.team_id == team_id, Player.is_substitute == True)
            )
            sub_result = await session.execute(sub_stmt)
            sub_count = sub_result.scalar() or 0
            
            return {
                "main": main_count,
                "substitutes": sub_count,
                "total": main_count + sub_count
            }