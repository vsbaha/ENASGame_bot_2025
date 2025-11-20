"""
Утилиты для форматирования турнирных сеток
"""
from typing import Dict, List, Tuple
from database.models import Match


def get_tournament_format_info(format_type: str) -> Dict[str, str]:
    """Получить информацию о формате турнира"""
    formats = {
        'single_elimination': {
            'name': 'Single Elimination',
            'icon': '🏆',
            'description': 'Одно поражение - выбывание'
        },
        'double_elimination': {
            'name': 'Double Elimination',
            'icon': '🎯',
            'description': 'Две жизни, Winner/Loser bracket'
        },
        'round_robin': {
            'name': 'Round Robin',
            'icon': '🔄',
            'description': 'Каждый играет с каждым'
        },
        'swiss': {
            'name': 'Swiss System',
            'icon': '♟️',
            'description': 'Швейцарская система'
        },
        'group_stage_playoffs': {
            'name': 'Groups + Playoffs',
            'icon': '🎪',
            'description': 'Групповой этап + плей-офф'
        }
    }
    
    return formats.get(format_type, {
        'name': format_type.replace('_', ' ').title(),
        'icon': '📋',
        'description': 'Турнирная сетка'
    })


def get_round_name_single_elimination(round_num: int, total_rounds: int) -> str:
    """Название раунда для Single Elimination"""
    if round_num == total_rounds:
        return "🏆 Финал"
    elif round_num == total_rounds - 1:
        return "🥉 Полуфинал"
    elif round_num == total_rounds - 2:
        return "🎯 Четвертьфинал"
    elif round_num == total_rounds - 3:
        return "⭐ 1/8 финала"
    elif round_num == total_rounds - 4:
        return "💫 1/16 финала"
    else:
        return f"📍 Раунд {round_num}"


def get_round_name_double_elimination(round_num: int, bracket_type: str = None) -> str:
    """Название раунда для Double Elimination
    
    В Double Elimination:
    - Положительные раунды = Winner Bracket
    - Отрицательные раунды = Loser Bracket
    """
    if bracket_type == "loser" or round_num < 0:
        # Loser Bracket
        abs_round = abs(round_num)
        return f"🔻 LB Раунд {abs_round}"
    else:
        # Winner Bracket
        if round_num == 1:
            return "🏆 WB Раунд 1"
        else:
            return f"⭐ WB Раунд {round_num}"


def get_round_name_round_robin(round_num: int) -> str:
    """Название раунда для Round Robin"""
    return f"🔄 Тур {round_num}"


def get_round_name_swiss(round_num: int, total_rounds: int = None) -> str:
    """Название раунда для Swiss System"""
    if total_rounds and round_num == total_rounds:
        return f"♟️ Финальный тур {round_num}"
    return f"♟️ Тур {round_num}"


def format_bracket_display(
    matches: List[Match],
    tournament_format: str
) -> Dict[str, List[Match]]:
    """
    Группирует матчи для отображения в зависимости от формата турнира
    
    Returns:
        Dict с ключами-названиями раундов и значениями-списками матчей
    """
    if tournament_format == 'double_elimination':
        return format_double_elimination_bracket(matches)
    elif tournament_format == 'round_robin':
        return format_round_robin_bracket(matches)
    elif tournament_format == 'swiss':
        return format_swiss_bracket(matches)
    else:  # single_elimination или другие
        return format_single_elimination_bracket(matches)


def format_single_elimination_bracket(matches: List[Match]) -> Dict[str, List[Match]]:
    """Группировка для Single Elimination"""
    rounds = {}
    total_rounds = max(m.round_number for m in matches) if matches else 0
    
    for match in matches:
        round_name = get_round_name_single_elimination(match.round_number, total_rounds)
        if round_name not in rounds:
            rounds[round_name] = []
        rounds[round_name].append(match)
    
    return rounds


def format_double_elimination_bracket(matches: List[Match]) -> Dict[str, List[Match]]:
    """Группировка для Double Elimination (Winner/Loser brackets)"""
    winner_bracket = {}
    loser_bracket = {}
    grand_final = {}
    
    for match in matches:
        bracket_type = getattr(match, 'bracket_type', 'winner')
        
        if match.round_number == 999:  # Grand Final (условное значение)
            grand_final["🏆 Гранд-финал"] = [match]
        elif bracket_type == 'loser' or match.round_number < 0:
            # Loser Bracket
            round_name = get_round_name_double_elimination(match.round_number, 'loser')
            if round_name not in loser_bracket:
                loser_bracket[round_name] = []
            loser_bracket[round_name].append(match)
        else:
            # Winner Bracket
            round_name = get_round_name_double_elimination(match.round_number, 'winner')
            if round_name not in winner_bracket:
                winner_bracket[round_name] = []
            winner_bracket[round_name].append(match)
    
    # Объединяем: сначала Winner Bracket, потом Loser Bracket, потом Grand Final
    result = {}
    
    if winner_bracket:
        result["═══ 🏆 WINNER BRACKET ═══"] = []
        result.update(winner_bracket)
    
    if loser_bracket:
        result["═══ 🔻 LOSER BRACKET ═══"] = []
        result.update(loser_bracket)
    
    if grand_final:
        result.update(grand_final)
    
    return result


def format_round_robin_bracket(matches: List[Match]) -> Dict[str, List[Match]]:
    """Группировка для Round Robin"""
    rounds = {}
    
    for match in matches:
        round_name = get_round_name_round_robin(match.round_number)
        if round_name not in rounds:
            rounds[round_name] = []
        rounds[round_name].append(match)
    
    return rounds


def format_swiss_bracket(matches: List[Match]) -> Dict[str, List[Match]]:
    """Группировка для Swiss System"""
    rounds = {}
    total_rounds = max(m.round_number for m in matches) if matches else 0
    
    for match in matches:
        round_name = get_round_name_swiss(match.round_number, total_rounds)
        if round_name not in rounds:
            rounds[round_name] = []
        rounds[round_name].append(match)
    
    return rounds


def get_match_status_icon(match: Match) -> str:
    """Получить иконку статуса матча"""
    from database.models import MatchStatus
    
    if match.status == MatchStatus.COMPLETED.value:
        return "✅"
    elif match.status == MatchStatus.CANCELLED.value:
        return "❌"
    else:
        return "⏳"


def format_match_line(match: Match, include_score: bool = True) -> str:
    """Форматировать строку матча для отображения"""
    from database.models import MatchStatus
    
    team1_name = match.team1.name if match.team1 else "?"
    team2_name = match.team2.name if match.team2 else "?"
    
    # Экранирование HTML
    team1_name = team1_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    team2_name = team2_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    icon = get_match_status_icon(match)
    
    if match.status == MatchStatus.COMPLETED.value and include_score:
        score = f"{match.team1_score or 0}:{match.team2_score or 0}"
        winner_name = match.winner.name if match.winner else "N/A"
        winner_name = winner_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        result = f"   {icon} {team1_name} <b>{score}</b> {team2_name}\n"
        result += f"      🏆 Победитель: {winner_name}\n"
        return result
    elif match.status == MatchStatus.CANCELLED.value:
        return f"   {icon} {team1_name} vs {team2_name} <i>(отменён)</i>\n"
    else:
        return f"   {icon} {team1_name} vs {team2_name}\n"
