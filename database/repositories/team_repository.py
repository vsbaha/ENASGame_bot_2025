from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy import select, update, func, and_, desc, cast, DATE
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.db_manager import get_session
from database.models import Team, TeamStatus, Player, Tournament, User


class TeamRepository:
    """Репозиторий для работы с командами"""
    
    @staticmethod
    async def create_team(
        tournament_id: int,
        name: str,
        captain_id: int,
        logo_file_id: Optional[str] = None
    ) -> Optional[Team]:
        """Создание новой команды"""
        async with get_session() as session:
            session: AsyncSession
            
            team = Team(
                tournament_id=tournament_id,
                name=name,
                captain_id=captain_id,
                logo_file_id=logo_file_id,
                status=TeamStatus.PENDING.value
            )
            
            session.add(team)
            await session.commit()
            await session.refresh(team)
            
            return team
    
    @staticmethod
    async def get_by_id(team_id: int) -> Optional[Team]:
        """Получение команды по ID"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Team)
                .options(
                    selectinload(Team.players),
                    selectinload(Team.captain),
                    selectinload(Team.tournament).selectinload(Tournament.game)
                )
                .where(Team.id == team_id)
            )
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_teams_by_tournament(tournament_id: int, status: Optional[TeamStatus] = None) -> List[Team]:
        """Получение команд турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Team)
                .options(
                    selectinload(Team.players),
                    selectinload(Team.captain)
                )
                .where(Team.tournament_id == tournament_id)
            )
            
            if status:
                stmt = stmt.where(Team.status == status.value)
            
            stmt = stmt.order_by(Team.created_at.desc())
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_teams_by_captain(captain_id: int) -> List[Team]:
        """Получение команд капитана"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Team)
                .options(
                    selectinload(Team.players),
                    selectinload(Team.tournament).selectinload(Tournament.game)
                )
                .where(Team.captain_id == captain_id)
                .order_by(Team.created_at.desc())
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def update_team_status(team_id: int, status: TeamStatus, rejection_reason: Optional[str] = None) -> bool:
        """Обновление статуса команды"""
        async with get_session() as session:
            session: AsyncSession
            
            values = {"status": status.value}
            if rejection_reason is not None:
                values["rejection_reason"] = rejection_reason
            
            stmt = (
                update(Team)
                .where(Team.id == team_id)
                .values(**values)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    @staticmethod
    async def update_team_info(team_id: int, name: Optional[str] = None, logo_file_id: Optional[str] = None) -> bool:
        """Обновление информации о команде"""
        async with get_session() as session:
            session: AsyncSession
            
            values = {}
            if name is not None:
                values["name"] = name
            if logo_file_id is not None:
                values["logo_file_id"] = logo_file_id
            
            if not values:
                return False
            
            stmt = (
                update(Team)
                .where(Team.id == team_id)
                .values(**values)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    @staticmethod
    async def delete_team(team_id: int) -> bool:
        """Удаление команды"""
        async with get_session() as session:
            session: AsyncSession
            
            team = await session.get(Team, team_id)
            if team:
                await session.delete(team)
                await session.commit()
                return True
            
            return False
    
    @staticmethod
    async def is_team_name_taken(tournament_id: int, name: str, exclude_team_id: Optional[int] = None) -> bool:
        """Проверка занятости названия команды в турнире"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(Team).where(
                and_(
                    Team.tournament_id == tournament_id,
                    Team.name == name
                )
            )
            
            if exclude_team_id:
                stmt = stmt.where(Team.id != exclude_team_id)
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def is_captain_registered(captain_id: int, tournament_id: int) -> bool:
        """Проверка регистрации капитана на турнир (только активные статусы)"""
        async with get_session() as session:
            session: AsyncSession
            
            # Проверяем только pending и approved команды (rejected и blocked не считаются)
            stmt = select(Team).where(
                and_(
                    Team.captain_id == captain_id,
                    Team.tournament_id == tournament_id,
                    Team.status.in_([TeamStatus.PENDING.value, TeamStatus.APPROVED.value])
                )
            )
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def is_captain_globally_blocked(captain_id: int) -> bool:
        """Проверка глобальной блокировки капитана"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(Team).where(
                and_(
                    Team.captain_id == captain_id,
                    Team.status == TeamStatus.BLOCKED.value,
                    Team.block_scope == "global"
                )
            )
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def is_captain_blocked_on_tournament(captain_id: int, tournament_id: int) -> bool:
        """Проверка блокировки капитана на конкретном турнире"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(Team).where(
                and_(
                    Team.captain_id == captain_id,
                    Team.tournament_id == tournament_id,
                    Team.status == TeamStatus.BLOCKED.value,
                    Team.block_scope == "tournament"
                )
            )
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def get_by_name_and_tournament(tournament_id: int, name: str) -> Optional[Team]:
        """Получение команды по названию и турниру"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Team)
                .options(
                    selectinload(Team.players),
                    selectinload(Team.captain),
                    selectinload(Team.tournament).selectinload(Tournament.game)
                )
                .where(
                    and_(
                        Team.tournament_id == tournament_id,
                        Team.name == name
                    )
                )
            )
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_tournament_teams_count(tournament_id: int) -> int:
        """Получение количества команд в турнире"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Team.id)).where(Team.tournament_id == tournament_id)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_approved_teams_count(tournament_id: int) -> int:
        """Получение количества одобренных команд в турнире"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Team.id)).where(
                and_(
                    Team.tournament_id == tournament_id,
                    Team.status == TeamStatus.APPROVED.value
                )
            )
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_approved_teams_by_tournament(tournament_id: int) -> List[Team]:
        """Получение одобренных команд турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Team)
                .options(
                    selectinload(Team.players),
                    selectinload(Team.captain),
                    selectinload(Team.tournament)
                )
                .where(
                    and_(
                        Team.tournament_id == tournament_id,
                        Team.status == TeamStatus.APPROVED.value
                    )
                )
                .order_by(Team.created_at.asc())
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_pending_teams() -> List[Team]:
        """Получение команд ожидающих модерации"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Team)
                .options(
                    selectinload(Team.players),
                    selectinload(Team.captain),
                    selectinload(Team.tournament)
                )
                .where(Team.status == TeamStatus.PENDING.value)
                .order_by(Team.created_at.asc())
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_active_teams() -> List[Team]:
        """Получение активных команд"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Team)
                .options(
                    selectinload(Team.players),
                    selectinload(Team.captain),
                    selectinload(Team.tournament)
                )
                .where(Team.status == TeamStatus.APPROVED.value)
                .order_by(Team.created_at.desc())
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_blocked_teams() -> List[Team]:
        """Получение заблокированных команд"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Team)
                .options(
                    selectinload(Team.players),
                    selectinload(Team.captain),
                    selectinload(Team.tournament)
                )
                .where(Team.status == TeamStatus.BLOCKED.value)
                .order_by(Team.blocked_at.desc())
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def approve_team(team_id: int) -> bool:
        """Одобрение команды"""
        return await TeamRepository.update_team_status(team_id, TeamStatus.APPROVED)
    
    @staticmethod
    async def reject_team(team_id: int, reason: str = None) -> bool:
        """Отклонение команды"""
        return await TeamRepository.update_team_status(team_id, TeamStatus.REJECTED, reason)
    
    @staticmethod
    async def block_team(team_id: int, reason: str, scope: str = "tournament", blocked_by: int = None) -> bool:
        """Блокировка команды"""
        from datetime import datetime
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                update(Team)
                .where(Team.id == team_id)
                .values(
                    status=TeamStatus.BLOCKED.value,
                    block_reason=reason,
                    block_scope=scope,
                    blocked_by=blocked_by,
                    blocked_at=datetime.utcnow()
                )
            )
            
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    
    @staticmethod
    async def unblock_team(team_id: int) -> bool:
        """Разблокировка команды"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                update(Team)
                .where(Team.id == team_id)
                .values(
                    status=TeamStatus.APPROVED.value,
                    block_reason=None,
                    block_scope=None,
                    blocked_by=None,
                    blocked_at=None
                )
            )
            
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    
    @staticmethod
    async def get_total_count() -> int:
        """Получение общего количества команд"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Team.id))
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_tournament_participants_count() -> int:
        """Получение количества участников турниров (капитаны одобренных команд)"""
        async with get_session() as session:
            session: AsyncSession
            
            # Подсчитываем количество капитанов одобренных команд
            stmt = select(func.count(func.distinct(Team.captain_id))).where(Team.status == TeamStatus.APPROVED.value)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_captains_count() -> int:
        """Получение количества капитанов команд"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(func.distinct(Team.captain_id))).where(Team.status == TeamStatus.APPROVED.value)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_tournament_participants() -> List[User]:
        """Получение участников турниров (капитаны одобренных команд)"""
        async with get_session() as session:
            session: AsyncSession
            
            # Получаем всех капитанов одобренных команд
            stmt = (
                select(User)
                .join(Team, User.id == Team.captain_id)
                .where(Team.status == TeamStatus.APPROVED.value)
                .distinct()
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def update_status(team_id: int, status: str) -> bool:
        """Обновление статуса команды"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = update(Team).where(Team.id == team_id).values(status=status)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    
    @staticmethod
    async def set_rejection_reason(team_id: int, reason: str) -> bool:
        """Установка причины отклонения команды"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = update(Team).where(Team.id == team_id).values(rejection_reason=reason)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    
    @staticmethod
    async def search_by_name(name: str) -> List[Team]:
        """Поиск команд по названию"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Team)
                .options(
                    selectinload(Team.players),
                    selectinload(Team.captain),
                    selectinload(Team.tournament)
                )
                .where(Team.name.ilike(f"%{name}%"))
                .order_by(Team.created_at.desc())
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())

    @staticmethod
    async def get_all_captains() -> List[User]:
        """Получение всех капитанов команд"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(User)
                .join(Team, User.id == Team.captain_id)
                .where(Team.status == TeamStatus.APPROVED.value)
                .distinct()
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    # МЕТОДЫ СТАТИСТИКИ
    
    @staticmethod
    async def get_total_count() -> int:
        """Получение общего количества команд"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Team.id))
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_count_since(date: datetime) -> int:
        """Получение количества команд созданных с определенной даты"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Team.id)).where(Team.created_at >= date)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_active_count() -> int:
        """Получение количества активных (одобренных) команд"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Team.id)).where(Team.status == TeamStatus.APPROVED.value)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_pending_count() -> int:
        """Получение количества команд на рассмотрении"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Team.id)).where(Team.status == TeamStatus.PENDING.value)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_blocked_count() -> int:
        """Получение количества заблокированных команд (отклоненные команды)"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Team.id)).where(Team.status == TeamStatus.REJECTED.value)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_average_team_size() -> float:
        """Получение среднего размера команды"""
        async with get_session() as session:
            session: AsyncSession
            
            # Подсчитываем количество игроков для каждой команды через JOIN
            stmt = select(
                func.avg(
                    select(func.count(Player.id))
                    .where(Player.team_id == Team.id)
                    .scalar_subquery()
                )
            ).where(
                Team.status == TeamStatus.APPROVED.value
            )
            result = await session.execute(stmt)
            return result.scalar() or 0.0
    
    @staticmethod
    async def get_tournament_participation_stats() -> Dict[str, int]:
        """Получение статистики участия команд в турнирах"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(
                Tournament.name, func.count(Team.id)
            ).select_from(
                Team
            ).join(
                Tournament, Team.tournament_id == Tournament.id
            ).where(
                Team.status == TeamStatus.APPROVED.value
            ).group_by(
                Tournament.name
            ).order_by(
                func.count(Team.id).desc()
            )
            result = await session.execute(stmt)
            return dict(result.all())
    
    @staticmethod
    async def get_top_captains(limit: int = 5) -> Dict[str, int]:
        """Получение топ капитанов по количеству команд"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(
                User.full_name, func.count(Team.id)
            ).select_from(
                Team
            ).join(
                User, Team.captain_id == User.id
            ).where(
                Team.status == TeamStatus.APPROVED.value
            ).group_by(
                User.id, User.full_name
            ).order_by(
                func.count(Team.id).desc()
            ).limit(limit)
            result = await session.execute(stmt)
            return dict(result.all())
    
    @staticmethod
    async def get_all_teams(limit: int = None, offset: int = 0) -> List[Team]:
        """Получить все команды с полной информацией"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(Team).options(
                selectinload(Team.players),
                selectinload(Team.captain),
                selectinload(Team.tournament)
            ).offset(offset)
            
            if limit:
                stmt = stmt.limit(limit)
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    @staticmethod
    async def get_total_teams() -> int:
        """Получить общее количество команд"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(Team.id))
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def update_team(team_id: int, **kwargs) -> bool:
        """Обновление данных команды"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = update(Team).where(Team.id == team_id).values(**kwargs)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    
    @staticmethod
    async def update_team_name(team_id: int, name: str) -> bool:
        """Обновление названия команды"""
        return await TeamRepository.update_team(team_id, name=name)
    
    @staticmethod
    async def update_team_description(team_id: int, description: str) -> bool:
        """Обновление описания команды"""
        return await TeamRepository.update_team(team_id, description=description)
    
    @staticmethod
    async def delete_by_id(team_id: int) -> bool:
        """Удаление команды по ID"""
        async with get_session() as session:
            session: AsyncSession
            
            # Сначала получаем команду
            team = await session.get(Team, team_id)
            if not team:
                return False
            
            # Удаляем команду
            await session.delete(team)
            await session.commit()
            return True
    
    @staticmethod
    async def create_team_full(
        tournament_id: int,
        name: str,
        captain_id: int,
        description: Optional[str] = None,
        logo_file_id: Optional[str] = None,
        status: str = TeamStatus.PENDING.value
    ) -> Optional[Team]:
        """Создание команды с полными параметрами"""
        async with get_session() as session:
            session: AsyncSession
            
            new_team = Team(
                tournament_id=tournament_id,
                name=name,
                captain_id=captain_id,
                description=description,
                logo_file_id=logo_file_id,
                status=status
            )
            
            session.add(new_team)
            await session.commit()
            await session.refresh(new_team)
            
            return new_team