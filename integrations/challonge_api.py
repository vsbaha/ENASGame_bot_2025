"""
Интеграция с Challonge API для турнирных сеток
"""
import asyncio
import aiohttp
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ChallongeAPI:
    """Клиент для работы с Challonge API"""
    
    def __init__(self, api_key: str, username: str):
        self.api_key = api_key
        self.username = username
        self.base_url = "https://api.challonge.com/v1"
        
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Выполнение HTTP запроса к Challonge API"""
        url = f"{self.base_url}/{endpoint}.json"
        
        # Добавляем API ключ к данным
        if data is None:
            data = {}
        data['api_key'] = self.api_key
        
        async with aiohttp.ClientSession() as session:
            try:
                if method.upper() == 'GET':
                    async with session.get(url, params=data) as response:
                        return await response.json()
                elif method.upper() == 'POST':
                    async with session.post(url, data=data) as response:
                        return await response.json()
                elif method.upper() == 'PUT':
                    async with session.put(url, data=data) as response:
                        return await response.json()
                elif method.upper() == 'DELETE':
                    async with session.delete(url, params=data) as response:
                        return await response.json()
                        
            except Exception as e:
                logger.error(f"Ошибка запроса к Challonge: {e}")
                raise
    
    async def create_tournament(
        self,
        name: str,
        tournament_type: str = "single elimination",
        description: str = "",
        private: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Создание турнира в Challonge"""
        
        # Создаем уникальный URL для турнира
        url_slug = name.lower().replace(" ", "_").replace("-", "_")
        url_slug = f"{self.username}_{url_slug}_{int(datetime.now().timestamp())}"
        
        data = {
            "tournament[name]": name,
            "tournament[url]": url_slug,
            "tournament[tournament_type]": tournament_type,
            "tournament[description]": description,
            "tournament[private]": private,
            "tournament[show_rounds]": True,
            "tournament[open_signup]": False,  # Регистрация только через админа
            "tournament[accept_attachments]": False,
            "tournament[hide_forum]": True,
            "tournament[show_standings]": True,
        }
        
        try:
            response = await self._make_request("POST", "tournaments", data)
            logger.info(f"Создан турнир в Challonge: {name}")
            return response.get("tournament")
        except Exception as e:
            logger.error(f"Ошибка создания турнира в Challonge: {e}")
            return None
    
    async def add_participant(
        self, 
        tournament_id: str, 
        participant_name: str
    ) -> Optional[Dict[str, Any]]:
        """Добавление участника в турнир"""
        
        data = {
            "participant[name]": participant_name,
            "participant[seed]": "",  # Рандомный сид
        }
        
        try:
            endpoint = f"tournaments/{tournament_id}/participants"
            response = await self._make_request("POST", endpoint, data)
            return response.get("participant")
        except Exception as e:
            logger.error(f"Ошибка добавления участника: {e}")
            return None
    
    async def start_tournament(self, tournament_id: str) -> bool:
        """Запуск турнира (создание сетки)"""
        try:
            endpoint = f"tournaments/{tournament_id}/start"
            await self._make_request("POST", endpoint)
            logger.info(f"Турнир {tournament_id} запущен")
            return True
        except Exception as e:
            logger.error(f"Ошибка запуска турнира: {e}")
            return False
    
    async def get_tournament_info(self, tournament_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о турнире"""
        try:
            endpoint = f"tournaments/{tournament_id}"
            data = {"include_participants": 1, "include_matches": 1}
            response = await self._make_request("GET", endpoint, data)
            return response.get("tournament")
        except Exception as e:
            logger.error(f"Ошибка получения турнира: {e}")
            return None
    
    async def update_match_score(
        self,
        tournament_id: str,
        match_id: str,
        winner_id: str,
        scores_csv: str
    ) -> bool:
        """Обновление результата матча"""
        
        data = {
            "match[winner_id]": winner_id,
            "match[scores_csv]": scores_csv,  # Например: "2-1" или "16-14,14-16,16-10"
        }
        
        try:
            endpoint = f"tournaments/{tournament_id}/matches/{match_id}"
            await self._make_request("PUT", endpoint, data)
            logger.info(f"Обновлен результат матча {match_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления матча: {e}")
            return False
    
    async def finalize_tournament(self, tournament_id: str) -> bool:
        """Завершение турнира"""
        try:
            endpoint = f"tournaments/{tournament_id}/finalize"
            await self._make_request("POST", endpoint)
            logger.info(f"Турнир {tournament_id} завершен")
            return True
        except Exception as e:
            logger.error(f"Ошибка завершения турнира: {e}")
            return False
    
    async def get_tournament_bracket_url(self, tournament_id: str) -> Optional[str]:
        """Получение URL турнирной сетки для просмотра"""
        try:
            tournament_info = await self.get_tournament_info(tournament_id)
            if tournament_info:
                return tournament_info.get("full_challonge_url")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения URL сетки: {e}")
            return None


class ChallongeIntegration:
    """Интеграция Challonge с нашей системой турниров"""
    
    def __init__(self, api_key: str, username: str):
        self.api = ChallongeAPI(api_key, username)
    
    async def create_tournament_with_teams(
        self,
        tournament_name: str,
        teams: List[str],
        tournament_type: str = "single elimination"
    ) -> Optional[str]:
        """Создание турнира со всеми командами"""
        
        # 1. Создаем турнир
        tournament = await self.api.create_tournament(
            name=tournament_name,
            tournament_type=tournament_type,
            description=f"Турнир создан через ENAS Game Bot"
        )
        
        if not tournament:
            return None
            
        tournament_id = tournament["url"]
        
        # 2. Добавляем все команды
        for team_name in teams:
            participant = await self.api.add_participant(tournament_id, team_name)
            if not participant:
                logger.warning(f"Не удалось добавить команду: {team_name}")
        
        # 3. Запускаем турнир (создаем сетку)
        started = await self.api.start_tournament(tournament_id)
        if not started:
            logger.error(f"Не удалось запустить турнир {tournament_id}")
            return None
        
        return tournament_id
    
    async def get_bracket_image_url(self, tournament_id: str) -> Optional[str]:
        """Получение URL изображения турнирной сетки"""
        # Challonge предоставляет embed изображения
        return f"https://challonge.com/{tournament_id}.svg"
    
    async def get_tournament_status_text(self, tournament_id: str) -> str:
        """Получение текстового статуса турнира"""
        tournament_info = await self.api.get_tournament_info(tournament_id)
        
        if not tournament_info:
            return "❌ Турнир не найден"
        
        status_map = {
            "pending": "🕐 Ожидание начала",
            "underway": "🏃 В процессе", 
            "awaiting_review": "⏳ Ожидание проверки",
            "complete": "✅ Завершен"
        }
        
        status = status_map.get(tournament_info["state"], "❓ Неизвестно")
        
        text = f"""🏆 **{tournament_info['name']}**
        
📊 Статус: {status}
👥 Участников: {tournament_info['participants_count']}
🎯 Тип: {tournament_info['tournament_type'].replace('_', ' ').title()}
📅 Создан: {tournament_info['created_at'][:10]}
"""
        
        if tournament_info.get("winner_id"):
            # Находим победителя среди участников
            winner_name = "Неизвестно"
            if "participants" in tournament_info:
                for participant in tournament_info["participants"]:
                    if participant["participant"]["id"] == tournament_info["winner_id"]:
                        winner_name = participant["participant"]["name"]
                        break
            text += f"\n🏆 **Победитель: {winner_name}**"
        
        return text