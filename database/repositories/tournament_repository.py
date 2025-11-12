from typing import Optional, List, Tuple, Dict
from datetime import datetime, timezone, timedelta, date
from sqlalchemy import select, update, and_, func, desc, cast, DATE
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging

from database.db_manager import get_session
from database.models import Tournament, TournamentStatus, TournamentFormat, Game

logger = logging.getLogger(__name__)


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
        logo_file_id: Optional[str] = None,
        rules_file_id: Optional[str] = None,
        rules_file_name: Optional[str] = None
    ) -> Optional[Tournament]:
        """Создание нового турнира"""
        logger.info(f"Creating tournament with files: logo={logo_file_id}, rules={rules_file_id}, rules_name={rules_file_name}")
        
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
                rules_file_id=rules_file_id,
                rules_file_name=rules_file_name,
                created_by=created_by
            )
            
            # Устанавливаем обязательные каналы
            tournament.required_channels_list = required_channels
            
            logger.info(f"Tournament object before commit: logo={tournament.logo_file_id}, rules={tournament.rules_file_id}")
            
            session.add(tournament)
            await session.commit()
            await session.refresh(tournament)
            
            logger.info(f"Tournament after commit: logo={tournament.logo_file_id}, rules={tournament.rules_file_id}")
            
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
    async def get_all() -> List[Tournament]:
        """Получение всех турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Tournament)
                .options(
                    selectinload(Tournament.game),
                    selectinload(Tournament.creator)
                )
                .order_by(Tournament.created_at.desc())
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
                    Tournament.status == TournamentStatus.IN_PROGRESS.value,
                    Tournament.tournament_start <= now
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
    
    @staticmethod
    async def get_format_statistics() -> Dict[str, int]:
        """Получение статистики по форматам турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(
                Tournament.format, func.count(Tournament.id)
            ).group_by(
                Tournament.format
            ).order_by(
                func.count(Tournament.id).desc()
            )
            result = await session.execute(stmt)
            return dict(result.all())
    
    @staticmethod
    async def update_challonge_id(tournament_id: int, challonge_id: str) -> bool:
        """Обновление ID турнира в Challonge"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                tournament.challonge_id = challonge_id
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def update_status(tournament_id: int, new_status: str) -> bool:
        """Обновление статуса турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                tournament.status = new_status
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def update_name(tournament_id: int, new_name: str) -> bool:
        """Обновление названия турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                tournament.name = new_name
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def update_description(tournament_id: int, new_description: str) -> bool:
        """Обновление описания турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                tournament.description = new_description
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def update_game(tournament_id: int, new_game_id: int) -> bool:
        """Обновление игры турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                tournament.game_id = new_game_id
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def update_format(tournament_id: int, new_format: str) -> bool:
        """Обновление формата турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                tournament.format = new_format
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def update_max_teams(tournament_id: int, new_max_teams: int) -> bool:
        """Обновление максимального количества команд"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                tournament.max_teams = new_max_teams
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def update_dates(tournament_id: int, reg_start, reg_end, tournament_start) -> bool:
        """Обновление дат турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                tournament.registration_start = reg_start
                tournament.registration_end = reg_end
                tournament.tournament_start = tournament_start
                # Обновляем дедлайн редактирования (за 1 час до начала)
                from datetime import timedelta
                tournament.edit_deadline = tournament_start - timedelta(hours=1)
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def get_by_name(name: str, exclude_id: int = None) -> Optional[Tournament]:
        """Поиск турнира по названию (для проверки уникальности)"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(Tournament).where(Tournament.name == name)
            if exclude_id:
                stmt = stmt.where(Tournament.id != exclude_id)
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def update_field(tournament_id: int, field_name: str, value) -> bool:
        """Обновление конкретного поля турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament and hasattr(tournament, field_name):
                setattr(tournament, field_name, value)
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def get_by_name(name: str) -> Optional[Tournament]:
        """Получение турнира по названию"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Tournament)
                .options(
                    selectinload(Tournament.game),
                    selectinload(Tournament.creator)
                )
                .where(Tournament.name == name)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    @staticmethod
    async def get_tournaments_since(date: datetime) -> List[Tournament]:
        """Получение турниров с определенной даты"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Tournament)
                .where(Tournament.created_at >= date)
                .options(selectinload(Tournament.game))
                .order_by(Tournament.created_at.desc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    @staticmethod
    async def get_status_statistics() -> Dict[str, int]:
        """Получение статистики по статусам турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Tournament.status, func.count(Tournament.id))
                .group_by(Tournament.status)
            )
            result = await session.execute(stmt)
            return {status: count for status, count in result.all()}

    @staticmethod
    async def get_popular_games() -> List[Tuple[str, int]]:
        """Получение популярных игр по количеству турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            from database.models import Game
            stmt = (
                select(Game.name, func.count(Tournament.id))
                .join(Game, Tournament.game_id == Game.id)
                .group_by(Game.name)
                .order_by(func.count(Tournament.id).desc())
            )
            result = await session.execute(stmt)
            return result.all()

    @staticmethod
    async def get_format_statistics() -> Dict[str, int]:
        """Получение статистики по форматам турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(Tournament.format, func.count(Tournament.id))
                .group_by(Tournament.format)
            )
            result = await session.execute(stmt)
            return {format_type: count for format_type, count in result.all()}

    @staticmethod
    async def get_average_teams_per_tournament() -> float:
        """Получение среднего количества команд на турнир"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.avg(Tournament.max_teams))
            result = await session.execute(stmt)
            avg = result.scalar_one_or_none()
            return float(avg) if avg else 0.0

    @staticmethod
    async def get_tournaments_this_month() -> int:
        """Получение количества турниров в этом месяце"""
        async with get_session() as session:
            session: AsyncSession
            
            now = datetime.now(timezone.utc)
            start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            stmt = (
                select(func.count(Tournament.id))
                .where(Tournament.created_at >= start_month)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() or 0

    @staticmethod
    async def get_tournaments_this_week() -> int:
        """Получение количества турниров на этой неделе"""
        async with get_session() as session:
            session: AsyncSession
            
            now = datetime.now(timezone.utc)
            start_week = now - timedelta(days=now.weekday())
            start_week = start_week.replace(hour=0, minute=0, second=0, microsecond=0)
            
            stmt = (
                select(func.count(Tournament.id))
                .where(Tournament.created_at >= start_week)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() or 0

    @staticmethod
    async def get_tournaments_last_week() -> int:
        """Получение количества турниров на прошлой неделе"""
        async with get_session() as session:
            session: AsyncSession
            
            now = datetime.now(timezone.utc)
            end_last_week = now - timedelta(days=now.weekday())
            start_last_week = end_last_week - timedelta(days=7)
            start_last_week = start_last_week.replace(hour=0, minute=0, second=0, microsecond=0)
            end_last_week = end_last_week.replace(hour=0, minute=0, second=0, microsecond=0)
            
            stmt = (
                select(func.count(Tournament.id))
                .where(Tournament.created_at >= start_last_week)
                .where(Tournament.created_at < end_last_week)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() or 0

    @staticmethod
    async def get_tournaments_last_month() -> int:
        """Получение количества турниров в прошлом месяце"""
        async with get_session() as session:
            session: AsyncSession
            
            now = datetime.now(timezone.utc)
            start_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Находим начало прошлого месяца
            if start_this_month.month == 1:
                start_last_month = start_this_month.replace(year=start_this_month.year - 1, month=12)
            else:
                start_last_month = start_this_month.replace(month=start_this_month.month - 1)
            
            stmt = (
                select(func.count(Tournament.id))
                .where(Tournament.created_at >= start_last_month)
                .where(Tournament.created_at < start_this_month)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() or 0

    @staticmethod
    async def get_tournaments_count_for_date(date) -> int:
        """Получение количества турниров за определенную дату"""
        async with get_session() as session:
            session: AsyncSession
            
            from datetime import datetime as dt
            start_date = dt.combine(date, dt.min.time()).replace(tzinfo=timezone.utc)
            end_date = start_date + timedelta(days=1)
            
            stmt = (
                select(func.count(Tournament.id))
                .where(Tournament.created_at >= start_date)
                .where(Tournament.created_at < end_date)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() or 0

    @staticmethod
    async def get_paused_count() -> int:
        """Получение количества приостановленных турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(func.count(Tournament.id))
                .where(Tournament.status == 'paused')
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() or 0

    @staticmethod
    async def get_completion_rate() -> float:
        """Получение коэффициента завершения турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            total_stmt = select(func.count(Tournament.id))
            total_result = await session.execute(total_stmt)
            total = total_result.scalar_one_or_none() or 0
            
            if total == 0:
                return 0.0
            
            completed_stmt = (
                select(func.count(Tournament.id))
                .where(Tournament.status == 'completed')
            )
            completed_result = await session.execute(completed_stmt)
            completed = completed_result.scalar_one_or_none() or 0
            
            return (completed / total) * 100

    @staticmethod
    async def get_average_duration() -> int:
        """Получение средней длительности турниров в днях"""
        # Заглушка - в реальном приложении нужно рассчитывать на основе дат
        return 7

    @staticmethod  
    async def get_peak_creation_days(limit: int = 10) -> List[Tuple]:
        """Получение дней с пиковым количеством созданных турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(
                    func.date(Tournament.created_at).label('creation_date'),
                    func.count(Tournament.id).label('count')
                )
                .group_by(func.date(Tournament.created_at))
                .order_by(func.count(Tournament.id).desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [(row.creation_date, row.count) for row in result.all()]

    @staticmethod
    async def get_format_by_game_statistics() -> Dict[Tuple[str, str], int]:
        """Получение статистики форматов по играм"""
        async with get_session() as session:
            session: AsyncSession
            
            from database.models import Game
            stmt = (
                select(Game.name, Tournament.format, func.count(Tournament.id))
                .join(Game, Tournament.game_id == Game.id)
                .group_by(Game.name, Tournament.format)
                .order_by(func.count(Tournament.id).desc())
            )
            result = await session.execute(stmt)
            return {(game_name, format_type): count for game_name, format_type, count in result.all()}

    @staticmethod
    async def get_cancelled_count() -> int:
        """Получение количества отмененных турниров"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(func.count(Tournament.id))
                .where(Tournament.status == 'cancelled')
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() or 0

    @staticmethod
    async def update_rules_file(tournament_id: int, file_id: str, file_name: str) -> bool:
        """Обновление файла правил турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                tournament.rules_file_id = file_id
                tournament.rules_file_name = file_name
                await session.commit()
                return True
            return False

    @staticmethod
    async def remove_rules_file(tournament_id: int) -> bool:
        """Удаление файла правил турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                tournament.rules_file_id = None
                tournament.rules_file_name = None
                await session.commit()
                return True
            return False

    @staticmethod
    async def get_rules_file_info(tournament_id: int) -> Optional[Tuple[str, str]]:
        """Получение информации о файле правил турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament and tournament.rules_file_id:
                return (tournament.rules_file_id, tournament.rules_file_name)
            return None

    @staticmethod
    async def update_logo(tournament_id: int, file_id: str) -> bool:
        """Обновление логотипа турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                tournament.logo_file_id = file_id
                await session.commit()
                return True
            return False

    @staticmethod
    async def remove_logo(tournament_id: int) -> bool:
        """Удаление логотипа турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                tournament.logo_file_id = None
                await session.commit()
                return True
            return False

    @staticmethod
    async def get_logo_file_id(tournament_id: int) -> Optional[str]:
        """Получение file_id логотипа турнира"""
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament and tournament.logo_file_id:
                return tournament.logo_file_id
            return None

    @staticmethod
    async def update_required_channels(tournament_id: int, channels: List[str]) -> bool:
        """Обновление списка обязательных каналов"""
        import json
        async with get_session() as session:
            session: AsyncSession
            
            tournament = await session.get(Tournament, tournament_id)
            if tournament:
                tournament.required_channels = json.dumps(channels)
                await session.commit()
                return True
            return False