"""
Репозиторий для работы с логами действий администраторов
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import joinedload

from database.db_manager import get_session
from database.models import ActionLog, User

logger = logging.getLogger(__name__)


class ActionLogRepository:
    """Репозиторий для работы с логами"""
    
    @staticmethod
    async def create_log(
        user_id: int,
        action: str,
        details: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Optional[ActionLog]:
        """Создать новую запись в логах"""
        try:
            async with get_session() as session:
                log = ActionLog(
                    user_id=user_id,
                    action=action,
                    details=details,
                    ip_address=ip_address
                )
                session.add(log)
                await session.commit()
                await session.refresh(log)
                return log
        except Exception as e:
            logger.error(f"Ошибка создания лога: {e}")
            return None
    
    @staticmethod
    async def get_logs(
        limit: int = 10,
        offset: int = 0,
        action_filter: Optional[str] = None,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ActionLog]:
        """Получить список логов с фильтрами"""
        try:
            async with get_session() as session:
                query = select(ActionLog).options(
                    joinedload(ActionLog.user)
                )
                
                # Применяем фильтры
                conditions = []
                
                if action_filter:
                    conditions.append(ActionLog.action.contains(action_filter))
                
                if user_id:
                    conditions.append(ActionLog.user_id == user_id)
                
                if start_date:
                    conditions.append(ActionLog.created_at >= start_date)
                
                if end_date:
                    conditions.append(ActionLog.created_at <= end_date)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                # Сортировка и пагинация
                query = query.order_by(desc(ActionLog.created_at))
                query = query.limit(limit).offset(offset)
                
                result = await session.execute(query)
                return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Ошибка получения логов: {e}")
            return []
    
    @staticmethod
    async def count_logs(
        action_filter: Optional[str] = None,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """Подсчитать количество логов с учетом фильтров"""
        try:
            async with get_session() as session:
                query = select(func.count(ActionLog.id))
                
                conditions = []
                
                if action_filter:
                    conditions.append(ActionLog.action.contains(action_filter))
                
                if user_id:
                    conditions.append(ActionLog.user_id == user_id)
                
                if start_date:
                    conditions.append(ActionLog.created_at >= start_date)
                
                if end_date:
                    conditions.append(ActionLog.created_at <= end_date)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                result = await session.execute(query)
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Ошибка подсчета логов: {e}")
            return 0
    
    @staticmethod
    async def get_statistics() -> Dict[str, Any]:
        """Получить статистику по логам"""
        try:
            async with get_session() as session:
                # Общее количество
                total_query = select(func.count(ActionLog.id))
                total_result = await session.execute(total_query)
                total = total_result.scalar() or 0
                
                # Уникальные пользователи
                unique_users_query = select(func.count(func.distinct(ActionLog.user_id)))
                unique_users_result = await session.execute(unique_users_query)
                unique_users = unique_users_result.scalar() or 0
                
                # Последнее действие
                last_action_query = select(ActionLog).order_by(desc(ActionLog.created_at)).limit(1)
                last_action_result = await session.execute(last_action_query)
                last_action = last_action_result.scalar_one_or_none()
                last_action_str = last_action.created_at.strftime("%d.%m.%Y %H:%M") if last_action else "Нет данных"
                
                # Топ действий
                top_actions_query = (
                    select(ActionLog.action, func.count(ActionLog.id).label('count'))
                    .group_by(ActionLog.action)
                    .order_by(desc('count'))
                    .limit(5)
                )
                top_actions_result = await session.execute(top_actions_query)
                top_actions = [(row[0], row[1]) for row in top_actions_result.all()]
                
                return {
                    "total": total,
                    "unique_users": unique_users,
                    "last_action": last_action_str,
                    "top_actions": top_actions
                }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    @staticmethod
    async def get_by_user(user_id: int, limit: int = 50) -> List[ActionLog]:
        """Получить логи конкретного пользователя"""
        try:
            async with get_session() as session:
                query = (
                    select(ActionLog)
                    .where(ActionLog.user_id == user_id)
                    .order_by(desc(ActionLog.created_at))
                    .limit(limit)
                )
                result = await session.execute(query)
                return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Ошибка получения логов пользователя: {e}")
            return []
    
    @staticmethod
    async def get_recent(limit: int = 20) -> List[ActionLog]:
        """Получить последние логи"""
        try:
            async with get_session() as session:
                query = (
                    select(ActionLog)
                    .options(joinedload(ActionLog.user))
                    .order_by(desc(ActionLog.created_at))
                    .limit(limit)
                )
                result = await session.execute(query)
                return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Ошибка получения последних логов: {e}")
            return []
    
    @staticmethod
    async def delete_old_logs(days: int = 90) -> int:
        """Удалить логи старше указанного количества дней"""
        try:
            async with get_session() as session:
                cutoff_date = datetime.now() - timedelta(days=days)
                query = select(ActionLog).where(ActionLog.created_at < cutoff_date)
                result = await session.execute(query)
                old_logs = result.scalars().all()
                
                count = len(old_logs)
                for log in old_logs:
                    await session.delete(log)
                
                await session.commit()
                return count
        except Exception as e:
            logger.error(f"Ошибка удаления старых логов: {e}")
            return 0
    
    @staticmethod
    async def search_logs(
        search_term: str,
        limit: int = 50
    ) -> List[ActionLog]:
        """Поиск в логах по тексту"""
        try:
            async with get_session() as session:
                query = (
                    select(ActionLog)
                    .options(joinedload(ActionLog.user))
                    .where(
                        (ActionLog.action.contains(search_term)) |
                        (ActionLog.details.contains(search_term))
                    )
                    .order_by(desc(ActionLog.created_at))
                    .limit(limit)
                )
                result = await session.execute(query)
                return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Ошибка поиска в логах: {e}")
            return []

