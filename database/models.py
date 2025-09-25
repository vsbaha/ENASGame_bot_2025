from datetime import datetime
from typing import List, Optional
from enum import Enum as PyEnum
import json

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, 
    ForeignKey, UniqueConstraint, Index, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func


Base = declarative_base()


class UserRole(PyEnum):
    USER = "user"
    ADMIN = "admin"


class TeamStatus(PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TournamentStatus(PyEnum):
    REGISTRATION = "registration"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TournamentFormat(PyEnum):
    SINGLE_ELIMINATION = "single_elimination"
    DOUBLE_ELIMINATION = "double_elimination"
    ROUND_ROBIN = "round_robin"
    GROUP_STAGE_PLAYOFFS = "group_stage_playoffs"


class MatchStatus(PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.USER.value)
    region: Mapped[str] = mapped_column(String(20), nullable=False, default="kg")
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="ru")
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    created_tournaments: Mapped[List["Tournament"]] = relationship("Tournament", back_populates="creator")
    teams: Mapped[List["Team"]] = relationship("Team", back_populates="captain")
    action_logs: Mapped[List["ActionLog"]] = relationship("ActionLog", back_populates="user")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user")
    
    # Properties
    @property
    def is_admin(self) -> bool:
        """Проверка является ли пользователь администратором"""
        return self.role == UserRole.ADMIN.value
    
    @property
    def first_name(self) -> str:
        """Получить имя из full_name (для совместимости)"""
        return self.full_name.split()[0] if self.full_name else ""
    
    @property
    def last_seen(self) -> Optional[datetime]:
        """Последнее время активности (для совместимости)"""
        return self.updated_at


class Game(Base):
    __tablename__ = "games"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    short_name: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    max_players: Mapped[int] = mapped_column(Integer, nullable=False)
    max_substitutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    icon_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tournaments: Mapped[List["Tournament"]] = relationship("Tournament", back_populates="game")


class Tournament(Base):
    __tablename__ = "tournaments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    format: Mapped[str] = mapped_column(String(30), nullable=False)
    max_teams: Mapped[int] = mapped_column(Integer, nullable=False)
    region: Mapped[str] = mapped_column(String(10), nullable=False, default="kg")  # Регион турнира
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TournamentStatus.REGISTRATION.value)
    registration_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registration_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tournament_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    edit_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    logo_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rules_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_channels: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON array
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="tournaments")
    creator: Mapped["User"] = relationship("User", back_populates="created_tournaments")
    teams: Mapped[List["Team"]] = relationship("Team", back_populates="tournament")
    matches: Mapped[List["Match"]] = relationship("Match", back_populates="tournament")
    bracket: Mapped[Optional["TournamentBracket"]] = relationship("TournamentBracket", back_populates="tournament", uselist=False)
    
    @property
    def required_channels_list(self) -> List[str]:
        """Получить список обязательных каналов"""
        return json.loads(self.required_channels or "[]")
    
    @required_channels_list.setter
    def required_channels_list(self, channels: List[str]):
        """Установить список обязательных каналов"""
        self.required_channels = json.dumps(channels)


class Team(Base):
    __tablename__ = "teams"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey("tournaments.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    captain_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    logo_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TeamStatus.PENDING.value)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="teams")
    captain: Mapped["User"] = relationship("User", back_populates="teams")
    players: Mapped[List["Player"]] = relationship("Player", back_populates="team", cascade="all, delete-orphan")
    team1_matches: Mapped[List["Match"]] = relationship("Match", foreign_keys="Match.team1_id", back_populates="team1")
    team2_matches: Mapped[List["Match"]] = relationship("Match", foreign_keys="Match.team2_id", back_populates="team2")
    won_matches: Mapped[List["Match"]] = relationship("Match", foreign_keys="Match.winner_id", back_populates="winner")
    
    __table_args__ = (
        UniqueConstraint('tournament_id', 'name', name='uq_tournament_team_name'),
        Index('ix_teams_tournament_id', 'tournament_id'),
        Index('ix_teams_captain_id', 'captain_id'),
    )


class Player(Base):
    __tablename__ = "players"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    game_id: Mapped[str] = mapped_column(String(100), nullable=False)
    is_substitute: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="players")
    
    __table_args__ = (
        Index('ix_players_team_id', 'team_id'),
    )


class Match(Base):
    __tablename__ = "matches"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey("tournaments.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    match_number: Mapped[int] = mapped_column(Integer, nullable=False)
    team1_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    team2_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    winner_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=MatchStatus.PENDING.value)
    bracket_type: Mapped[str] = mapped_column(String(20), nullable=False, default="winner")
    next_match_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("matches.id"), nullable=True)
    scheduled_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="matches")
    team1: Mapped[Optional["Team"]] = relationship("Team", foreign_keys=[team1_id], back_populates="team1_matches")
    team2: Mapped[Optional["Team"]] = relationship("Team", foreign_keys=[team2_id], back_populates="team2_matches")
    winner: Mapped[Optional["Team"]] = relationship("Team", foreign_keys=[winner_id], back_populates="won_matches")
    next_match: Mapped[Optional["Match"]] = relationship("Match", remote_side=[id])
    
    __table_args__ = (
        Index('ix_matches_tournament_id', 'tournament_id'),
    )


class TournamentBracket(Base):
    __tablename__ = "tournament_brackets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey("tournaments.id"), nullable=False, unique=True)
    format_type: Mapped[str] = mapped_column(String(30), nullable=False)
    current_round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_rounds: Mapped[int] = mapped_column(Integer, nullable=False)
    bracket_data: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="bracket")
    
    @property
    def bracket_data_dict(self) -> dict:
        """Получить данные сетки как словарь"""
        return json.loads(self.bracket_data or "{}")
    
    @bracket_data_dict.setter
    def bracket_data_dict(self, data: dict):
        """Установить данные сетки"""
        self.bracket_data = json.dumps(data)


class ActionLog(Base):
    __tablename__ = "action_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="action_logs")
    
    __table_args__ = (
        Index('ix_action_logs_user_id', 'user_id'),
        Index('ix_action_logs_created_at', 'created_at'),
    )


class Notification(Base):
    __tablename__ = "notifications"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    
    __table_args__ = (
        Index('ix_notifications_user_id', 'user_id'),
        Index('ix_notifications_is_read', 'is_read'),
    )