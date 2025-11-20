"""
Интеграция с Challonge API v2.1 для турнирных сеток
Документация: https://challonge.apidog.io/
Использует OAuth2 Client Credentials Flow
"""
import asyncio
import aiohttp
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ChallongeAPI:
    """Клиент для работы с Challonge API v2.1 через OAuth2"""
    
    def __init__(self, client_id: str, client_secret: str, username: str = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.base_url = "https://api.challonge.com/v2.1"
        self.oauth_url = "https://api.challonge.com/oauth/token"
        
        # Токен кешируется
        self.access_token = None
        self.token_expires_at = None
        
    async def _get_access_token(self) -> str:
        """Получение access token через OAuth2 Client Credentials Flow"""
        # Проверяем кеш
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token
        
        # Запрашиваем новый токен
        logger.info("Запрашиваем новый OAuth2 access token от Challonge...")
        
        async with aiohttp.ClientSession() as session:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
                "scope": "tournaments:write tournaments:read matches:write matches:read participants:write participants:read"
            }
            
            try:
                async with session.post(
                    self.oauth_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"OAuth token error {response.status}: {error_text}")
                        raise Exception(f"Failed to get OAuth token: {error_text}")
                    
                    token_data = await response.json()
                    self.access_token = token_data["access_token"]
                    expires_in = token_data.get("expires_in", 604800)  # По умолчанию 7 дней
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # -5 минут запас
                    
                    logger.info(f"✅ Получен OAuth2 токен, истекает через {expires_in} секунд")
                    return self.access_token
                    
            except Exception as e:
                logger.error(f"Ошибка получения OAuth токена: {e}")
                raise
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Выполнение HTTP запроса к Challonge API v2.1 с OAuth2"""
        url = f"{self.base_url}/{endpoint}.json"
        
        # Получаем access token
        access_token = await self._get_access_token()
        
        # Согласно документации Challonge API v2.1:
        # Для OAuth нужны заголовки Authorization-Type: v2 и Authorization: Bearer token
        headers = {
            "Authorization-Type": "v2",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                if method.upper() == 'GET':
                    async with session.get(url, params=params, headers=headers) as response:
                        if response.status >= 400:
                            error_text = await response.text()
                            logger.error(f"Challonge API error {response.status}: {error_text}")
                            raise Exception(f"API error {response.status}: {error_text}")
                        return await response.json()
                        
                elif method.upper() == 'POST':
                    async with session.post(url, json=data, params=params, headers=headers) as response:
                        if response.status >= 400:
                            error_text = await response.text()
                            logger.error(f"Challonge API error {response.status}: {error_text}")
                            raise Exception(f"API error {response.status}: {error_text}")
                        return await response.json()
                        
                elif method.upper() == 'PUT':
                    async with session.put(url, json=data, params=params, headers=headers) as response:
                        if response.status >= 400:
                            error_text = await response.text()
                            logger.error(f"Challonge API error {response.status}: {error_text}")
                            raise Exception(f"API error {response.status}: {error_text}")
                        return await response.json()
                        
                elif method.upper() == 'DELETE':
                    async with session.delete(url, params=params, headers=headers) as response:
                        if response.status >= 400:
                            error_text = await response.text()
                            logger.error(f"Challonge API error {response.status}: {error_text}")
                            raise Exception(f"API error {response.status}: {error_text}")
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
        """Создание турнира в Challonge API v2"""
        
        # Создаем уникальный URL для турнира
        # Challonge требует: только буквы, цифры и подчёркивания
        import re
        url_slug = name.lower()
        # Заменяем пробелы и дефисы на подчёркивания
        url_slug = url_slug.replace(" ", "_").replace("-", "_")
        # Удаляем все символы кроме букв, цифр и подчёркиваний
        url_slug = re.sub(r'[^a-z0-9_]', '', url_slug)
        # Добавляем timestamp для уникальности
        url_slug = f"{url_slug}_{int(datetime.now().timestamp())}"
        
        # V2 использует JSON API spec формат
        data = {
            "data": {
                "type": "tournaments",
                "attributes": {
                    "name": name,
                    "url": url_slug,
                    "tournament_type": tournament_type,
                    "description": description,
                    "private": private,
                    "show_rounds": True,
                    "open_signup": False,
                    "accept_attachments": False,
                    "hide_forum": True,
                    "show_standings": True,
                }
            }
        }
        
        try:
            response = await self._make_request("POST", "tournaments", data)
            logger.info(f"Создан турнир в Challonge v2: {name}")
            
            # API v2.1 возвращает структуру:
            # {
            #   "data": {
            #     "id": "12345",
            #     "type": "tournaments",
            #     "attributes": { "name": "...", "url": "...", ... }
            #   }
            # }
            data_obj = response.get("data", {})
            attributes = data_obj.get("attributes", {})
            
            # Добавляем ID из data в attributes для совместимости
            if "id" in data_obj:
                attributes["id"] = data_obj["id"]
            
            return attributes
        except Exception as e:
            logger.error(f"Ошибка создания турнира в Challonge: {e}")
            return None
    
    async def add_participant(
        self, 
        tournament_id: str, 
        participant_name: str
    ) -> Optional[Dict[str, Any]]:
        """Добавление участника в турнир (API v2)"""
        
        data = {
            "data": {
                "type": "participants",
                "attributes": {
                    "name": participant_name,
                }
            }
        }
        
        try:
            endpoint = f"tournaments/{tournament_id}/participants"
            response = await self._make_request("POST", endpoint, data)
            
            # Парсим ответ API v2.1 с ID
            data_obj = response.get("data", {})
            attributes = data_obj.get("attributes", {})
            if "id" in data_obj:
                attributes["id"] = data_obj["id"]
            
            return attributes
        except Exception as e:
            logger.error(f"Ошибка добавления участника: {e}")
            return None
    
    async def start_tournament(self, tournament_id: str) -> bool:
        """
        Запуск турнира (создание сетки) - API v2.1
        
        ВНИМАНИЕ: API v2.1 не поддерживает программный запуск турниров.
        Турнир необходимо запустить вручную через веб-интерфейс Challonge.
        
        Этот метод остаётся для совместимости и логирует предупреждение.
        Для запуска откройте турнир на challonge.com и нажмите "Start Tournament".
        """
        logger.warning(
            f"⚠️ API v2.1 не поддерживает автоматический запуск турниров. "
            f"Откройте турнир на https://challonge.com и запустите вручную: tournament_id={tournament_id}"
        )
        
        # Проверяем текущий статус турнира
        try:
            info = await self.get_tournament_info(tournament_id)
            if info:
                current_state = info.get("state", "unknown")
                logger.info(f"Текущий статус турнира {tournament_id}: {current_state}")
                
                # Если турнир уже запущен, возвращаем True
                if current_state in ["underway", "complete"]:
                    logger.info(f"Турнир {tournament_id} уже запущен (статус: {current_state})")
                    return True
                else:
                    logger.warning(
                        f"Турнир {tournament_id} не запущен (статус: {current_state}). "
                        f"Требуется ручной запуск через веб-интерфейс."
                    )
                    return False
            return False
        except Exception as e:
            logger.error(f"Ошибка проверки статуса турнира: {e}")
            return False
    
    async def get_tournament_info(self, tournament_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о турнире (API v2)"""
        try:
            endpoint = f"tournaments/{tournament_id}"
            params = {"include": "participants,matches"}
            response = await self._make_request("GET", endpoint, params=params)
            
            # Parse API v2.1 response - ID is separate from attributes
            data_obj = response.get("data", {})
            attributes = data_obj.get("attributes", {})
            
            # Merge ID into attributes if present
            if "id" in data_obj:
                attributes["id"] = data_obj["id"]
            
            return attributes
        except Exception as e:
            logger.error(f"Ошибка получения турнира: {e}")
            return None
    
    async def update_match_score(
        self,
        tournament_id: str,
        match_id: str,
        winner_id: str,
        scores_csv: str,
        loser_id: str = None
    ) -> bool:
        """Обновление результата матча (API v2.1)
        
        Args:
            tournament_id: ID турнира в Challonge
            match_id: ID матча в Challonge
            winner_id: ID участника-победителя
            scores_csv: Счёт в формате "2-0" или "3-1" и т.д.
            loser_id: ID участника-проигравшего (опционально)
        
        Формат согласно документации:
        https://challonge.apidog.io/update-match-23619747e0
        """
        
        # Парсим счёт
        scores = scores_csv.split('-')
        winner_score = scores[0].strip() if len(scores) > 0 else "0"
        loser_score = scores[1].strip() if len(scores) > 1 else "0"
        
        # Формируем данные согласно документации API v2.1
        match_data = [
            {
                "participant_id": str(winner_id),
                "score_set": winner_score,
                "rank": 1,
                "advancing": True
            }
        ]
        
        # Добавляем проигравшего если известен
        if loser_id:
            match_data.append({
                "participant_id": str(loser_id),
                "score_set": loser_score,
                "rank": 2,
                "advancing": False
            })
        
        data = {
            "data": {
                "type": "Match",
                "attributes": {
                    "match": match_data
                }
            }
        }
        
        try:
            endpoint = f"tournaments/{tournament_id}/matches/{match_id}"
            response = await self._make_request("PUT", endpoint, data)
            
            # Проверяем, обновился ли матч
            updated_match = await self.get_match(tournament_id, match_id)
            if updated_match and updated_match.get("winner_id"):
                logger.info(f"✅ Результат матча {match_id} успешно обновлен: {scores_csv}")
                return True
            else:
                logger.warning(
                    f"⚠️ API вернул ответ, но результат не обновился для матча {match_id}. "
                    f"Проверьте формат данных или обновите вручную на challonge.com"
                )
                return False
        except Exception as e:
            logger.error(f"Ошибка обновления матча {match_id}: {e}")
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
    
    async def get_participants(self, tournament_id: str) -> List[Dict[str, Any]]:
        """Получение списка участников турнира (API v2)"""
        try:
            endpoint = f"tournaments/{tournament_id}/participants"
            response = await self._make_request("GET", endpoint)
            
            # API v2.1 возвращает список участников напрямую
            # Если есть обёртка data, извлекаем, иначе используем весь ответ
            if isinstance(response, dict) and "data" in response:
                data_list = response.get("data", [])
                # Extract attributes and merge ID for each participant
                participants = []
                for item in data_list:
                    attributes = item.get("attributes", {})
                    if "id" in item:
                        attributes["id"] = item["id"]
                    participants.append(attributes)
                return participants
            elif isinstance(response, list):
                # Ответ уже список участников без обёртки
                return response
            else:
                return []
        except Exception as e:
            logger.error(f"Ошибка получения участников: {e}")
            return []
    
    async def get_tournament(self, tournament_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о турнире"""
        try:
            endpoint = f"tournaments/{tournament_id}"
            response = await self._make_request("GET", endpoint)
            
            # API v2.1 может вернуть данные напрямую или через data->attributes
            if isinstance(response, dict):
                if "data" in response:
                    data_obj = response.get("data", {})
                    attributes = data_obj.get("attributes", {})
                    if "id" in data_obj:
                        attributes["id"] = data_obj["id"]
                    return attributes
                else:
                    # Данные возвращаются напрямую
                    return response
            return None
        except Exception as e:
            logger.error(f"Ошибка получения турнира: {e}")
            return None
    
    async def get_matches(self, tournament_id: str) -> List[Dict[str, Any]]:
        """Получение списка всех матчей турнира (API v2)"""
        try:
            endpoint = f"tournaments/{tournament_id}/matches"
            response = await self._make_request("GET", endpoint)
            
            # API v2.1 возвращает список матчей напрямую
            # Если есть обёртка data, извлекаем, иначе используем весь ответ
            if isinstance(response, dict) and "data" in response:
                data_list = response.get("data", [])
                # Extract attributes and merge ID for each match
                matches = []
                for item in data_list:
                    attributes = item.get("attributes", {})
                    if "id" in item:
                        attributes["id"] = item["id"]
                    matches.append(attributes)
                return matches
            elif isinstance(response, list):
                # Ответ уже список матчей без обёртки
                return response
            else:
                return []
        except Exception as e:
            logger.error(f"Ошибка получения матчей: {e}")
            return []
    
    async def get_match(self, tournament_id: str, match_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации об одном матче (API v2)"""
        try:
            endpoint = f"tournaments/{tournament_id}/matches/{match_id}"
            response = await self._make_request("GET", endpoint)
            
            # Parse API v2.1 response - ID is separate from attributes
            data_obj = response.get("data", {})
            attributes = data_obj.get("attributes", {})
            
            # Merge ID into attributes if present
            if "id" in data_obj:
                attributes["id"] = data_obj["id"]
            
            return attributes
        except Exception as e:
            logger.error(f"Ошибка получения матча: {e}")
            return None
    
    async def update_participant_seed(
        self, 
        tournament_id: str, 
        participant_id: int, 
        new_seed: int
    ) -> bool:
        """Обновление seed (позиции) участника (API v2)"""
        try:
            endpoint = f"tournaments/{tournament_id}/participants/{participant_id}"
            data = {
                "data": {
                    "type": "participants",
                    "attributes": {
                        "seed": new_seed
                    }
                }
            }
            await self._make_request("PUT", endpoint, data)
            logger.info(f"Обновлен seed участника {participant_id} на {new_seed}")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления seed: {e}")
            return False
    
    async def swap_participants(
        self, 
        tournament_id: str, 
        participant1_id: int, 
        participant2_id: int
    ) -> bool:
        """Обмен позициями двух участников"""
        try:
            # Получаем текущие seed'ы
            participants = await self.get_participants(tournament_id)
            
            p1_seed = None
            p2_seed = None
            
            # API v2.1 возвращает данные напрямую
            for p in participants:
                if p.get("id") == participant1_id:
                    p1_seed = p.get("seed")
                elif p.get("id") == participant2_id:
                    p2_seed = p.get("seed")
            
            if p1_seed is None or p2_seed is None:
                logger.error("Не удалось найти seed'ы участников")
                return False
            
            # Меняем местами
            success1 = await self.update_participant_seed(tournament_id, participant1_id, p2_seed)
            success2 = await self.update_participant_seed(tournament_id, participant2_id, p1_seed)
            
            return success1 and success2
            
        except Exception as e:
            logger.error(f"Ошибка обмена участников: {e}")
            return False


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
            # В API v2.1 нужно получить участников отдельным запросом
            participants = await self.get_participants(str(tournament_info.get("id", "")))
            for participant in participants:
                if str(participant.get("id")) == str(tournament_info["winner_id"]):
                    winner_name = participant.get("name", "Неизвестно")
                    break
            text += f"\n🏆 **Победитель: {winner_name}**"
        
        return text