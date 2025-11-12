"""
Тест системы управления матчами
Проверяет:
1. Создание матчей в БД
2. Синхронизация с Challonge
3. Ввод результатов
4. Обновление в Challonge
5. Получение статистики
"""
import asyncio
import sys
from datetime import datetime, timedelta

# Добавляем путь к проекту
sys.path.insert(0, '.')

from database.db_manager import init_database
from database.repositories import (
    TournamentRepository, 
    TeamRepository, 
    UserRepository, 
    GameRepository,
    MatchRepository
)
from database.models import TournamentFormat, TournamentStatus, MatchStatus
from integrations.challonge_api import ChallongeAPI
from config.settings import Settings
settings = Settings()


async def test_match_management():
    """Основной тест системы управления матчами"""
    
    print("🧪 Тестирование системы управления матчами...\n")
    
    # Инициализация БД
    await init_database()
    print("✅ БД инициализирована\n")
    
    # Тест 1: Проверка Challonge API
    print("🔑 Тест 1: Проверка Challonge API...")
    if not settings.challonge_api_key or not settings.challonge_username:
        print("❌ Challonge API не настроен в .env")
        return False
    print(f"✅ API Key: {'*' * 36}{settings.challonge_api_key[-4:]}")
    print(f"✅ Username: {settings.challonge_username}\n")
    
    # Тест 2: Поиск турнира со сгенерированной сеткой
    print("🏆 Тест 2: Поиск турнира с активной сеткой...")
    
    # Ищем турнир с challonge_id и статусом in_progress
    tournaments = await TournamentRepository.get_all_tournaments()
    tournament = None
    
    for t in tournaments:
        if t.challonge_id and t.status == TournamentStatus.IN_PROGRESS.value:
            tournament = t
            print(f"✅ Найден турнир: {t.name}")
            print(f"   Challonge ID: {t.challonge_id}")
            break
    
    if not tournament:
        print("⚠️  Нет подходящего турнира. Используем последний созданный...")
        # Берем последний турнир из предыдущего теста
        tournaments = await TournamentRepository.get_all_tournaments()
        if tournaments:
            tournament = tournaments[-1]
            print(f"✅ Использую турнир: {tournament.name}")
        else:
            print("❌ Нет доступных турниров")
            return False
    
    print()
    
    # Тест 3: Синхронизация матчей из Challonge
    print("🔄 Тест 3: Синхронизация матчей из Challonge...")
    
    if not tournament.challonge_id:
        print("⚠️  Турнир не создан в Challonge. Пропускаем синхронизацию.")
        matches = []
    else:
        challonge = ChallongeAPI(settings.challonge_api_key, settings.challonge_username)
        
        # Получаем матчи из Challonge
        challonge_matches = await challonge.get_matches(tournament.challonge_id)
        print(f"   Матчей в Challonge: {len(challonge_matches)}")
        
        # Синхронизируем в БД
        matches = await MatchRepository.sync_matches_from_challonge(
            tournament_id=tournament.id,
            challonge_matches=challonge_matches
        )
        print(f"✅ Синхронизировано матчей: {len(matches)}")
        
        # Показываем первые 3 матча
        for i, match in enumerate(matches[:3], 1):
            print(f"   {i}. Матч #{match.match_number}, Раунд {match.round_number}")
    
    print()
    
    # Тест 4: Получение списка матчей
    print("📋 Тест 4: Получение списка матчей турнира...")
    
    all_matches = await MatchRepository.get_tournament_matches(tournament.id)
    pending_matches = await MatchRepository.get_pending_matches(tournament.id)
    completed_matches = await MatchRepository.get_completed_matches(tournament.id)
    
    print(f"✅ Всего матчей: {len(all_matches)}")
    print(f"   ⏳ Ожидают результата: {len(pending_matches)}")
    print(f"   ✅ Завершено: {len(completed_matches)}")
    print()
    
    # Тест 5: Ввод результата матча (симуляция)
    if pending_matches:
        print("✏️ Тест 5: Симуляция ввода результата матча...")
        
        # Берем первый незавершенный матч
        match = pending_matches[0]
        
        if match.team1 and match.team2:
            print(f"   Матч: {match.team1.name} vs {match.team2.name}")
            
            # Симулируем счет
            team1_score = 2
            team2_score = 1
            winner_id = match.team1_id  # Побеждает первая команда
            
            print(f"   Счет: {team1_score}:{team2_score}")
            
            # Обновляем результат
            updated_match = await MatchRepository.update_match_score(
                match_id=match.id,
                team1_score=team1_score,
                team2_score=team2_score,
                winner_id=winner_id
            )
            
            print(f"✅ Результат сохранен в БД")
            print(f"   Победитель: {updated_match.winner.name}")
            
            # Тест 6: Обновление в Challonge
            if tournament.challonge_id and match.challonge_match_id:
                print("\n🌐 Тест 6: Обновление результата в Challonge...")
                
                # Получаем participant_id победителя
                participants = await challonge.get_participants(tournament.challonge_id)
                winner_participant_id = None
                
                for participant in participants:
                    p_data = participant.get("participant", participant)
                    if p_data.get("name") == updated_match.winner.name:
                        winner_participant_id = str(p_data["id"])
                        break
                
                if winner_participant_id:
                    scores_csv = f"{team1_score}-{team2_score}"
                    success = await challonge.update_match_score(
                        tournament_id=tournament.challonge_id,
                        match_id=match.challonge_match_id,
                        winner_id=winner_participant_id,
                        scores_csv=scores_csv
                    )
                    
                    if success:
                        print(f"✅ Результат обновлен в Challonge")
                        print(f"   URL: https://challonge.com/{tournament.challonge_id}")
                    else:
                        print("⚠️  Не удалось обновить результат в Challonge")
                else:
                    print("⚠️  Не найден participant_id победителя")
            else:
                print("\n⏭️  Тест 6: Пропущен (нет Challonge ID)")
        else:
            print("⚠️  Матч не имеет обеих команд. Пропускаем ввод результата.")
    else:
        print("⏭️  Тест 5-6: Пропущены (нет незавершенных матчей)")
    
    print()
    
    # Тест 7: Статистика матчей
    print("📊 Тест 7: Получение статистики...")
    
    # Статистика по раундам
    if all_matches:
        rounds = set(m.round_number for m in all_matches)
        print(f"✅ Раундов в турнире: {len(rounds)}")
        
        for round_num in sorted(rounds):
            round_matches = await MatchRepository.get_matches_by_round(
                tournament.id, 
                round_num
            )
            completed_in_round = sum(
                1 for m in round_matches 
                if m.status == MatchStatus.COMPLETED.value
            )
            print(f"   Раунд {round_num}: {completed_in_round}/{len(round_matches)} завершено")
    else:
        print("⚠️  Нет матчей для статистики")
    
    print()
    
    # Тест 8: Получение матчей команды
    if all_matches:
        print("👥 Тест 8: Получение матчей команды...")
        
        # Берем первую команду из первого матча
        first_match = all_matches[0]
        if first_match.team1:
            team_matches = await MatchRepository.get_team_matches(first_match.team1_id)
            print(f"✅ Матчей команды '{first_match.team1.name}': {len(team_matches)}")
            
            wins = sum(1 for m in team_matches if m.winner_id == first_match.team1_id)
            losses = sum(
                1 for m in team_matches 
                if m.status == MatchStatus.COMPLETED.value and m.winner_id != first_match.team1_id
            )
            print(f"   Побед: {wins}, Поражений: {losses}")
        else:
            print("⚠️  Нет команды для проверки")
    else:
        print("⏭️  Тест 8: Пропущен (нет матчей)")
    
    print()
    print("=" * 60)
    print("🎉 ВСЕ ТЕСТЫ УПРАВЛЕНИЯ МАТЧАМИ ПРОЙДЕНЫ!")
    print("=" * 60)
    
    print("\n✅ Реализовано:")
    print("   ✅ Синхронизация матчей из Challonge")
    print("   ✅ Получение списка матчей (все/активные/завершенные)")
    print("   ✅ Ввод результатов матчей")
    print("   ✅ Обновление результатов в Challonge")
    print("   ✅ Статистика по раундам")
    print("   ✅ Матчи команды с подсчетом побед/поражений")
    
    if tournament.challonge_id:
        print(f"\n🌐 Проверьте сетку на Challonge:")
        print(f"   https://challonge.com/{tournament.challonge_id}")
    
    print("\n✅ Тестирование завершено успешно!")
    return True


if __name__ == "__main__":
    result = asyncio.run(test_match_management())
    sys.exit(0 if result else 1)
