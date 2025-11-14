"""Отладка структуры данных матчей из Challonge"""
import asyncio
import json
from integrations.challonge_api import ChallongeAPI
from config.settings import settings


async def main():
    api = ChallongeAPI(settings.challonge_api_key, settings.challonge_username)
    
    print("Получаем матчи турнира 17095947...")
    matches = await api.get_matches('17095947')
    
    if matches:
        print(f"\n=== ВСЕГО МАТЧЕЙ: {len(matches)} ===\n")
        print("=== ПЕРВЫЙ МАТЧ ===")
        print(json.dumps(matches[0], indent=2, ensure_ascii=False))
    else:
        print("Нет матчей")
    
    print("\n\n=== УЧАСТНИКИ ТУРНИРА ===")
    participants = await api.get_participants('17095947')
    if participants:
        print(f"Всего участников: {len(participants)}")
        print("\nПервый участник:")
        print(json.dumps(participants[0], indent=2, ensure_ascii=False))
    else:
        print("Нет участников")


if __name__ == "__main__":
    asyncio.run(main())
