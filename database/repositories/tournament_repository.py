from typing import Optional, List, Tuple, Dict
from datetime import datetime
from sqlalchemy import select, update, and_, func, desc, cast, DATE
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.db_manager import get_session
from database.models import Tournament, TournamentStatus, TournamentFormat, Game


class TournamentRepository:
    """Репозиторий для работы с турнирами"""
    
    @staticmethod
    async def create_tournament(
        game_id: int,
        name: str,
        description: str,
        format_type: TournamentFormat,
        max_teams: int,
        registration_start: datetime,
        registration_end: datetime,
        tournament_start: datetime,
        edit_deadline: datetime,
        rules_text: str,
        required_channels: List[str],
        created_by: int,
        logo_file_id: Optional[str] = None
    ) -> Optional[Tournament]:
        """Создание нового турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = Tournament(
                game_id=game_id,
                name=name,
                description=description,
                format=format_type.value,
                max_teams=max_teams,
                registration_start=registration_start,
                registration_end=registration_end,
                tournament_start=tournament_start,
                edit_deadline=edit_deadline,
                logo_file_id=logo_file_id,
                rules_text=rules_text,
                created_by=created_by
            )
            
            # Устанавливаем обязательные каналы
            tournament.required_channels_list = required_channels
            
            session.add(tournament)
            await session.commit()
            await session.refresh(tournament)
            
            return tournament
    
    @staticmethod
    async def get_by_id(tournament_id: int) -> Optional[Tournament]:
        """Получение турнира по ID"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Tournament)
                .options(
                    selectinload(Tournament.game),
                    selectinload(Tournament.creator)
                )
                .where(Tournament.id == tournament_id)
            )
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_active_tournaments(region: str = None) -> List[Tournament]:
        """Получение активных турниров (регистрация открыта)"""
        async with get_session() as session:
            session: AsyncSession
            
            now = datetime.utcnow()
            
            conditions = [
                Tournament.status == TournamentStatus.REGISTRATION.value,
                Tournament.registration_start <= now,
                Tournament.registration_end > now
            ]
            
            # Добавляем фильтр по региону, если указан
            if region:
                conditions.append(Tournament.region == region)
            
            stmt = (
                select(Tournament)
                .options(selectinload(Tournament.game))
                .where(and_(*conditions))
                .order_by(Tournament.registration_end.asc())
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_all_tournaments(limit: int = 50, offset: int = 0) -> List[Tournament]:
        """Получение всех турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Tournament)
                .options(selectinload(Tournament.game))
                .order_by(Tournament.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_tournaments_by_status(status: TournamentStatus) -> List[Tournament]:
        """Получение турниров по статусу"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Tournament)
                .options(selectinload(Tournament.game))
                .where(Tournament.status == status.value)
                .order_by(Tournament.created_at.desc())
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def update_status(tournament_id: int, status: TournamentStatus) -> bool:
        """Обновление статуса турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                update(Tournament)
                .where(Tournament.id == tournament_id)
                .values(status=status.value)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    @staticmethod
    async def update_tournament(
        tournament_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        max_teams: Optional[int] = None,
        registration_start: Optional[datetime] = None,
        registration_end: Optional[datetime] = None,
        tournament_start: Optional[datetime] = None,
        edit_deadline: Optional[datetime] = None,
        rules_text: Optional[str] = None,
        required_channels: Optional[List[str]] = None,
        logo_file_id: Optional[str] = None
    ) -> bool:
        """Обновление турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if not tournament:
                return False
            
            if name is not None:
                tournament.name = name
            if description is not None:
                tournament.description = description
            if max_teams is not None:
                tournament.max_teams = max_teams
            if registration_start is not None:
                tournament.registration_start = registration_start
            if registration_end is not None:
                tournament.registration_end = registration_end
            if tournament_start is not None:
                tournament.tournament_start = tournament_start
            if edit_deadline is not None:
                tournament.edit_deadline = edit_deadline
            if rules_text is not None:
                tournament.rules_text = rules_text
            if required_channels is not None:
                tournament.required_channels_list = required_channels
            if logo_file_id is not None:
                tournament.logo_file_id = logo_file_id
            
            await session.commit()
            return True
    
    @staticmethod
    async def delete_tournament(tournament_id: int) -> bool:
        """Удаление турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                await session.delete(tournament)
                await session.commit()
                return True
            
            return False
    
    @staticmethod
    async def get_tournament_with_game(tournament_id: int) -> Optional[Tuple[Tournament, Game]]:
        """Получение турнира с информацией об игре"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Tournament)
                .options(selectinload(Tournament.game))
                .where(Tournament.id == tournament_id)
            )
            
            result = await session.execute(stmt)
            tournament = result.scalar_one_or_none()
            
            if tournament and tournament.game:
                return tournament, tournament.game
            
            return None
    
    @staticmethod
    async def get_tournaments_count() -> int:
        """Получение общего количества турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Tournament.id))
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_upcoming_tournaments(limit: int = 10) -> List[Tournament]:
        """Получение предстоящих турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            now = datetime.utcnow()
            
            stmt = (
                select(Tournament)
                .options(selectinload(Tournament.game))
                .where(Tournament.tournament_start > now)
                .order_by(Tournament.tournament_start.asc())
                .limit(limit)
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def is_registration_open(tournament_id: int) -> bool:
        """Проверка открыта ли регистрация на турнир"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if not tournament:
                return False
            
            now = datetime.utcnow()
            return (
                tournament.status == TournamentStatus.REGISTRATION.value and
                tournament.registration_start <= now <= tournament.registration_end
            )
    
    @staticmethod
    async def is_edit_allowed(tournament_id: int) -> bool:
        """Проверка разрешено ли редактирование команд"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if not tournament:
                return False
            
            now = datetime.utcnow()
            return now <= tournament.edit_deadline
    
    # МЕТОДЫ СТАТИСТИКИ
    
    @staticmethod
    async def get_total_count() -> int:
        """Получение общего количества турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Tournament.id))
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_count_since(date: datetime) -> int:
        """Получение количества турниров созданных с определенной даты"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Tournament.id)).where(Tournament.created_at >= date)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_active_count() -> int:
        """Получение количества активных турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            now = datetime.utcnow()
            stmt = select(func.count(Tournament.id)).where(
                and_(
                    Tournament.status == TournamentStatus.ACTIVE.value,
                    Tournament.start_date <= now,
                    Tournament.end_date >= now
                )
            )
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_completed_count() -> int:
        """Получение количества завершенных турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Tournament.id)).where(
                Tournament.status == TournamentStatus.COMPLETED.value
            )
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_upcoming_count() -> int:
        """Получение количества предстоящих турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            now = datetime.utcnow()
            stmt = select(func.count(Tournament.id)).where(
                and_(
                    Tournament.status == TournamentStatus.REGISTRATION.value,
                    Tournament.start_date > now
                )
            )
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_game_statistics() -> Dict[str, int]:
        """Получение статистики по играм"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(
                Game.name, func.count(Tournament.id)
            ).select_from(
                Tournament
            ).join(
                Game, Tournament.game_id == Game.id
            ).group_by(
                Game.name
            ).order_by(
                func.count(Tournament.id).desc()
            )
            result = await session.execute(stmt)
            return dict(result.all())
    
    @staticmethod
    async def get_top_by_teams(limit: int = 5) -> List[Tournament]:
        """Получение топ турниров по количеству команд"""
        async with get_session() as session:
            session: AsyncSession
            
            # Подсчитываем количество команд для каждого турнира через JOIN
            from database.models import Team
            
            stmt = select(
                Tournament,
                func.count(Team.id).label('team_count')
            ).outerjoin(
                Team, Tournament.id == Team.tournament_id
            ).options(
                selectinload(Tournament.teams)
            ).group_by(
                Tournament.id
            ).order_by(
                func.count(Team.id).desc()
            ).limit(limit)
            
            result = await session.execute(stmt)
            tournaments = [row.Tournament for row in result.all()]
            return tournaments
    
    @staticmethod
    async def get_total_tournaments() -> int:
        """Получить общее количество турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Tournament.id))
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_active_tournaments_count() -> int:
        """Получить количество активных турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Tournament.id)).where(
                Tournament.status.in_(['registration', 'in_progress'])
            )
            result = await session.execute(stmt)
            return result.scalar() or 0