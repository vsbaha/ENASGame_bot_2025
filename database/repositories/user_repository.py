from typing import Optional, List, Dict
from datetime import datetime, timedelta
from sqlalchemy import select, update, func, and_, or_, desc, cast, DATE
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from database.db_manager import get_session
from database.models import User, UserRole


class UserRepository:
    """Репозиторий для работы с пользователями"""
    
    @staticmethod
    async def create_user(
        telegram_id: int, 
        username: Optional[str], 
        full_name: str, 
        region: str = "kg", 
        language: str = "ru"
    ) -> Optional[User]:
        """Создание нового пользователя"""
        async with get_session() as session:
            session: AsyncSession
            
            # Проверяем, существует ли пользователь
            existing_user = await UserRepository.get_by_telegram_id(telegram_id)
            if existing_user:
                return existing_user
            
            # Создаем нового пользователя
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                region=region,
                language=language,
                role=UserRole.USER.value
            )
            
            session.add(user)
            try:
                await session.commit()
                await session.refresh(user)
                return user
            except IntegrityError:
                await session.rollback()
                # Пользователь уже существует, возвращаем существующую запись
                return await UserRepository.get_by_telegram_id(telegram_id)
    
    @staticmethod
    async def get_by_telegram_id(telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_id(user_id: int) -> Optional[User]:
        """Получение пользователя по ID"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def update_user_info(telegram_id: int, username: Optional[str], full_name: str) -> bool:
        """Обновление информации о пользователе"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(username=username, full_name=full_name)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    @staticmethod
    async def update_language(telegram_id: int, language: str) -> bool:
        """Обновление языка пользователя"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(language=language)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    @staticmethod
    async def update_region(telegram_id: int, region: str) -> bool:
        """Обновление региона пользователя"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(region=region)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    @staticmethod
    async def block_user(telegram_id: int) -> bool:
        """Блокировка пользователя"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(is_blocked=True)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    @staticmethod
    async def unblock_user(telegram_id: int) -> bool:
        """Разблокировка пользователя"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(is_blocked=False)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    @staticmethod
    async def get_all_users(limit: int = 100, offset: int = 0) -> List[User]:
        """Получение списка всех пользователей"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = (
                select(User)
                .order_by(User.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_user_count() -> int:
        """Получение общего количества пользователей"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(User.id))
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_admins() -> List[User]:
        """Получение списка администраторов"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(User.role == UserRole.ADMIN.value)
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_all_admins() -> List[User]:
        """Алиас для get_admins - получение списка администраторов"""
        return await UserRepository.get_admins()
    
    @staticmethod
    async def set_admin_role(telegram_id: int, is_admin: bool = True) -> bool:
        """Установка/снятие роли администратора"""
        async with get_session() as session:
            session: AsyncSession
            
            role = UserRole.ADMIN.value if is_admin else UserRole.USER.value
            
            stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(role=role)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    @staticmethod
    async def get_total_count() -> int:
        """Получение общего количества пользователей"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(User.id))
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_active_users_count() -> int:
        """Получение количества активных пользователей"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(User.id)).where(User.is_blocked == False)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_blocked_users_count() -> int:
        """Получение количества заблокированных пользователей"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(User.id)).where(User.is_blocked == True)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_admins_count() -> int:
        """Получение количества администраторов"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(User.id)).where(User.role == UserRole.ADMIN.value)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_blocked_users() -> List[User]:
        """Получение списка заблокированных пользователей"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(User.is_blocked == True).order_by(User.created_at.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_all_users(limit: int = 50, offset: int = 0) -> List[User]:
        """Получение списка всех пользователей с пагинацией"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def make_admin(user_id: int) -> bool:
        """Назначение пользователя администратором"""
        return await UserRepository.set_admin_role(user_id, True)
    
    @staticmethod
    async def remove_admin(user_id: int) -> bool:
        """Снятие роли администратора"""
        return await UserRepository.set_admin_role(user_id, False)
    
    @staticmethod
    async def search_by_username(username: str) -> List[User]:
        """Поиск пользователей по username"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(User.username.ilike(f"%{username}%"))
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod 
    async def search_by_name(name: str) -> List[User]:
        """Поиск пользователей по имени"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(User.full_name.ilike(f"%{name}%"))
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_active_count() -> int:
        """Получение количества активных пользователей (псевдоним для get_active_users_count)"""
        return await UserRepository.get_active_users_count()
    
    @staticmethod
    async def get_all_active_users() -> List[User]:
        """Получение списка всех активных (не заблокированных) пользователей"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(User.is_blocked == False).order_by(User.created_at.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_users_by_ids(user_ids: List[int]) -> List[User]:
        """Получение пользователей по списку Telegram ID"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(User.telegram_id.in_(user_ids))
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_users_by_language(language: str) -> List[User]:
        """Получение пользователей по языку"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(
                and_(User.language == language, User.is_blocked == False)
            ).order_by(User.created_at.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_users_by_region(region: str) -> List[User]:
        """Получение пользователей по региону"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(
                and_(User.region == region, User.is_blocked == False)
            ).order_by(User.created_at.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_users_by_ids(telegram_ids: List[int]) -> List[User]:
        """Получение пользователей по списку Telegram ID"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(User.telegram_id.in_(telegram_ids)).where(User.is_blocked == False)
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_users_by_language(language: str) -> List[User]:
        """Получение пользователей по языку"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(User.language == language).where(User.is_blocked == False)
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_users_by_region(region: str) -> List[User]:
        """Получение пользователей по региону"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(User.region == region).where(User.is_blocked == False)
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    # МЕТОДЫ СТАТИСТИКИ
    
    @staticmethod
    async def get_total_count() -> int:
        """Получение общего количества пользователей"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(User.id))
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_count_since(date: datetime) -> int:
        """Получение количества пользователей зарегистрированных с определенной даты"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(User.id)).where(User.created_at >= date)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_language_statistics() -> Dict[str, int]:
        """Получение статистики по языкам пользователей"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User.language, func.count(User.id)).where(
                User.is_blocked == False
            ).group_by(User.language)
            result = await session.execute(stmt)
            return dict(result.all())
    
    @staticmethod
    async def get_region_statistics() -> Dict[str, int]:
        """Получение статистики по регионам пользователей"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User.region, func.count(User.id)).where(
                and_(User.region.is_not(None), User.is_blocked == False)
            ).group_by(User.region)
            result = await session.execute(stmt)
            return dict(result.all())
    
    @staticmethod
    async def get_blocked_users() -> List[User]:
        """Получение списка заблокированных пользователей"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(User.is_blocked == True).order_by(User.created_at.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_active_since(date: datetime) -> int:
        """Получение количества активных пользователей с определенной даты"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(func.count(User.id)).where(
                and_(User.updated_at >= date, User.is_blocked == False)
            )
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_daily_registrations(days: int) -> Dict[str, int]:
        """Получение статистики регистраций по дням за последние N дней"""
        async with get_session() as session:
            session: AsyncSession
            
            start_date = datetime.now() - timedelta(days=days)
            stmt = select(
                func.date(User.created_at).label('date'),
                func.count(User.id).label('count')
            ).where(
                User.created_at >= start_date
            ).group_by(
                func.date(User.created_at)
            ).order_by(
                func.date(User.created_at).desc()
            )
            result = await session.execute(stmt)
            return {str(row.date): row.count for row in result.all()}
    
    @staticmethod
    async def get_most_active_users(limit: int = 5) -> Dict[str, str]:
        """Получение самых активных пользователей (по updated_at)"""
        async with get_session() as session:
            session: AsyncSession
            
            stmt = select(User).where(
                User.is_blocked == False
            ).order_by(
                User.updated_at.desc()
            ).limit(limit)
            result = await session.execute(stmt)
            users = result.scalars().all()
            
            return {
                user.full_name or f"@{user.username}" or f"ID:{user.telegram_id}": 
                user.updated_at.strftime("%d.%m.%Y %H:%M") if user.updated_at else "Никогда"
                for user in users
            }
    
    @staticmethod
    async def get_user_teams_count(user_id: int) -> int:
        """Получение количества команд пользователя (где он капитан)"""
        from database.models import Team
        
        async with get_session() as session:
            session: AsyncSession
            
            # Считаем команды где пользователь капитан
            stmt = select(func.count(Team.id)).where(Team.captain_id == user_id)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @staticmethod
    async def get_user_tournaments_count(user_id: int) -> int:
        """Получение количества турниров пользователя (где он капитан команды)"""
        from database.models import Team, Tournament
        
        async with get_session() as session:
            session: AsyncSession
            
            # Получаем турниры через команды где пользователь капитан
            stmt = select(func.count(func.distinct(Tournament.id))).select_from(
                Tournament
            ).join(
                Team, Tournament.id == Team.tournament_id
            ).where(
                Team.captain_id == user_id
            )
            
            result = await session.execute(stmt)
            return result.scalar() or 0