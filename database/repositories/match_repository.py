"""
Репозиторий для работы с матчами
"""
from typing import List, Optional
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload

from database.models import Match, MatchStatus, Team, TeamStatus
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
    async def update_teams(
        match_id: int,
        team1_id: Optional[int] = None,
        team2_id: Optional[int] = None
    ) -> Optional[Match]:
        """Обновление команд в матче"""
        async with DatabaseSession() as session:
            update_values = {}
            if team1_id is not None:
                update_values['team1_id'] = team1_id
            if team2_id is not None:
                update_values['team2_id'] = team2_id
            
            if update_values:
                await session.execute(
                    update(Match)
                    .where(Match.id == match_id)
                    .values(**update_values)
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
        challonge_matches: List[dict],
        participants_map: dict = None
    ) -> List[Match]:
        """Синхронизация матчей из Challonge в БД
        
        Args:
            tournament_id: ID турнира
            challonge_matches: Список матчей из Challonge API
            participants_map: Словарь {challonge_participant_id: team_id} для связи участников с командами
        """
        from database.repositories import TeamRepository
        
        synced_matches = []
        
        # Если маппинг не передан, создаем его на основе имен команд
        if participants_map is None:
            participants_map = {}
            teams = await TeamRepository.get_teams_by_tournament(tournament_id, status=TeamStatus.APPROVED)
            for team in teams:
                # Предполагаем, что имена команд совпадают с именами участников в Challonge
                participants_map[team.name] = team.id
        
        for challonge_match in challonge_matches:
            # API v2.1 возвращает данные напрямую, без обёртки "match"
            match_data = challonge_match
            
            challonge_match_id = str(match_data["id"])
            round_number = match_data.get("round", 1)
            
            # В API v2.1 participant_id могут быть в points_by_participant или напрямую
            player1_id = match_data.get("player1_id")
            player2_id = match_data.get("player2_id")
            
            # Если player_id нет, проверяем points_by_participant
            if not player1_id and not player2_id:
                points_data = match_data.get("points_by_participant", [])
                if len(points_data) >= 2:
                    player1_id = points_data[0].get("participant_id")
                    player2_id = points_data[1].get("participant_id")
                elif len(points_data) == 1:
                    player1_id = points_data[0].get("participant_id")
            
            # Проверяем, существует ли матч
            existing_match = await MatchRepository.get_by_challonge_id(
                tournament_id, 
                challonge_match_id
            )
            
            # Получаем team_id для участников
            # Преобразуем ID в строку для сравнения (API v2.1 возвращает строки)
            team1_id = participants_map.get(str(player1_id)) if player1_id and participants_map else None
            team2_id = participants_map.get(str(player2_id)) if player2_id and participants_map else None
            
            if not existing_match:
                # Создаем новый матч
                match = await MatchRepository.create_match(
                    tournament_id=tournament_id,
                    round_number=abs(round_number),  # Challonge использует отрицательные для loser bracket
                    match_number=match_data.get("suggested_play_order", 0),
                    team1_id=team1_id,
                    team2_id=team2_id,
                    challonge_match_id=challonge_match_id,
                    bracket_type="loser" if round_number < 0 else "winner"
                )
                synced_matches.append(match)
            else:
                # Обновляем команды если они изменились
                if team1_id or team2_id:
                    await MatchRepository.update_teams(
                        existing_match.id,
                        team1_id=team1_id,
                        team2_id=team2_id
                    )
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
