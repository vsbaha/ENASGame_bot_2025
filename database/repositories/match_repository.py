"""
Репозиторий для работы с матчами
"""
from typing import List, Optional
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload

from database.models import Match, MatchStatus, Team
from database.db_manager import DatabaseSession


class MatchRepository:
    """Репозиторий для работы с матчами"""
    
    @staticmethod
    async def create_match(
        tournament_id: int,
        round_number: int,
        match_number: int,
        team1_id: Optional[int] = None,
        team2_id: Optional[int] = None,
        challonge_match_id: Optional[str] = None,
        bracket_type: str = "winner"
    ) -> Match:
        """Создание нового матча"""
        async with DatabaseSession() as session:
            match = Match(
                tournament_id=tournament_id,
                round_number=round_number,
                match_number=match_number,
                team1_id=team1_id,
                team2_id=team2_id,
                challonge_match_id=challonge_match_id,
                bracket_type=bracket_type,
                status=MatchStatus.PENDING.value
            )
            session.add(match)
            await session.commit()
            await session.refresh(match)
            return match
    
    @staticmethod
    async def get_by_id(match_id: int) -> Optional[Match]:
        """Получение матча по ID с загрузкой команд"""
        async with DatabaseSession() as session:
            result = await session.execute(
                select(Match)
                .options(
                    selectinload(Match.team1),
                    selectinload(Match.team2),
                    selectinload(Match.winner)
                )
                .where(Match.id == match_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_challonge_id(
        tournament_id: int, 
        challonge_match_id: str
    ) -> Optional[Match]:
        """Получение матча по Challonge ID"""
        async with DatabaseSession() as session:
            result = await session.execute(
                select(Match)
                .options(
                    selectinload(Match.team1),
                    selectinload(Match.team2),
                    selectinload(Match.winner)
                )
                .where(
                    and_(
                        Match.tournament_id == tournament_id,
                        Match.challonge_match_id == challonge_match_id
                    )
                )
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_tournament_matches(
        tournament_id: int,
        status: Optional[str] = None
    ) -> List[Match]:
        """Получение всех матчей турнира с фильтром по статусу"""
        async with DatabaseSession() as session:
            query = (
                select(Match)
                .options(
                    selectinload(Match.team1),
                    selectinload(Match.team2),
                    selectinload(Match.winner)
                )
                .where(Match.tournament_id == tournament_id)
                .order_by(Match.round_number, Match.match_number)
            )
            
            if status:
                query = query.where(Match.status == status)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_pending_matches(tournament_id: int) -> List[Match]:
        """Получение незавершенных матчей турнира"""
        return await MatchRepository.get_tournament_matches(
            tournament_id, 
            status=MatchStatus.PENDING.value
        )
    
    @staticmethod
    async def get_completed_matches(tournament_id: int) -> List[Match]:
        """Получение завершенных матчей турнира"""
        return await MatchRepository.get_tournament_matches(
            tournament_id, 
            status=MatchStatus.COMPLETED.value
        )
    
    @staticmethod
    async def get_matches_by_round(
        tournament_id: int, 
        round_number: int
    ) -> List[Match]:
        """Получение матчей конкретного раунда"""
        async with DatabaseSession() as session:
            result = await session.execute(
                select(Match)
                .options(
                    selectinload(Match.team1),
                    selectinload(Match.team2),
                    selectinload(Match.winner)
                )
                .where(
                    and_(
                        Match.tournament_id == tournament_id,
                        Match.round_number == round_number
                    )
                )
                .order_by(Match.match_number)
            )
            return list(result.scalars().all())
    
    @staticmethod
    async def update_match_score(
        match_id: int,
        team1_score: int,
        team2_score: int,
        winner_id: Optional[int] = None
    ) -> Optional[Match]:
        """Обновление счета матча"""
        async with DatabaseSession() as session:
            await session.execute(
                update(Match)
                .where(Match.id == match_id)
                .values(
                    team1_score=team1_score,
                    team2_score=team2_score,
                    winner_id=winner_id,
                    status=MatchStatus.COMPLETED.value if winner_id else MatchStatus.PENDING.value
                )
            )
            await session.commit()
            
            return await MatchRepository.get_by_id(match_id)
    
    @staticmethod
    async def set_match_winner(match_id: int, winner_id: int) -> Optional[Match]:
        """Установка победителя матча"""
        async with DatabaseSession() as session:
            await session.execute(
                update(Match)
                .where(Match.id == match_id)
                .values(
                    winner_id=winner_id,
                    status=MatchStatus.COMPLETED.value
                )
            )
            await session.commit()
            
            return await MatchRepository.get_by_id(match_id)
    
    @staticmethod
    async def cancel_match(match_id: int) -> Optional[Match]:
        """Отмена матча"""
        async with DatabaseSession() as session:
            await session.execute(
                update(Match)
                .where(Match.id == match_id)
                .values(status=MatchStatus.CANCELLED.value)
            )
            await session.commit()
            
            return await MatchRepository.get_by_id(match_id)
    
    @staticmethod
    async def sync_matches_from_challonge(
        tournament_id: int,
        challonge_matches: List[dict]
    ) -> List[Match]:
        """Синхронизация матчей из Challonge в БД"""
        synced_matches = []
        
        for challonge_match in challonge_matches:
            match_data = challonge_match.get("match", challonge_match)
            
            challonge_match_id = str(match_data["id"])
            round_number = match_data.get("round", 1)
            
            # Проверяем, существует ли матч
            existing_match = await MatchRepository.get_by_challonge_id(
                tournament_id, 
                challonge_match_id
            )
            
            if not existing_match:
                # Создаем новый матч
                match = await MatchRepository.create_match(
                    tournament_id=tournament_id,
                    round_number=abs(round_number),  # Challonge использует отрицательные для loser bracket
                    match_number=match_data.get("suggested_play_order", 0),
                    challonge_match_id=challonge_match_id,
                    bracket_type="loser" if round_number < 0 else "winner"
                )
                synced_matches.append(match)
            else:
                synced_matches.append(existing_match)
        
        return synced_matches
    
    @staticmethod
    async def get_team_matches(
        team_id: int,
        status: Optional[str] = None
    ) -> List[Match]:
        """Получение всех матчей команды"""
        async with DatabaseSession() as session:
            query = (
                select(Match)
                .options(
                    selectinload(Match.team1),
                    selectinload(Match.team2),
                    selectinload(Match.winner),
                    selectinload(Match.tournament)
                )
                .where(
                    (Match.team1_id == team_id) | (Match.team2_id == team_id)
                )
                .order_by(Match.created_at.desc())
            )
            
            if status:
                query = query.where(Match.status == status)
            
            result = await session.execute(query)
            return list(result.scalars().all())
