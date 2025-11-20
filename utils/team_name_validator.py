"""
Валидатор названий команд
Проверяет на недопустимые символы и популярные киберспортивные бренды
"""
import re
from typing import Tuple


# Список популярных киберспортивных организаций (запрещены к использованию)
FORBIDDEN_TEAM_NAMES = {
    # Tier 1 Organizations
    'team liquid', 'liquid', 'tl',
    'natus vincere', 'navi', "na'vi", 'na vi',
    'faze clan', 'faze', 'fazeclan',
    'g2 esports', 'g2', 'g2esports',
    'fnatic', 'fnc',
    'cloud9', 'cloud 9', 'c9',
    'team vitality', 'vitality', 'vit',
    'astralis',
    't1', 'team t1', 'skt t1', 'sk telecom t1',
    'evil geniuses', 'eg',
    'optic gaming', 'optic',
    'team secret', 'secret',
    'og', 'og esports',
    'psg talon', 'psg.talon', 'psg',
    'tundra esports', 'tundra',
    'newbee',
    'invictus gaming', 'ig',
    'lgd gaming', 'lgd', 'psg.lgd',
    'vici gaming', 'vg',
    'royal never give up', 'rng',
    'edward gaming', 'edg', 'edward gaming',
    'jd gaming', 'jdg',
    'top esports', 'tes',
    'fpx', 'funplus phoenix', 'fun plus phoenix',
    'damwon gaming', 'dwg', 'damwon',
    'gen.g', 'geng', 'gen g',
    'drx',
    'kt rolster', 'kt',
    'sk gaming', 'sk',
    'mousesports', 'mouz',
    'complexity gaming', 'complexity', 'col',
    'mibr', 'made in brazil',
    'pain gaming', 'pain', 'png',
    'imperial esports', 'imperial',
    'furia esports', 'furia',
    'loud',
    
    # Mobile Esports
    'nova esports', 'nova',
    'omega esports', 'omega',
    'blacklist international', 'blacklist',
    'onic esports', 'onic',
    'echo',
    'rrq', 'rex regum qeon',
    'evos esports', 'evos',
    'geek fam', 'geekfam',
    'alter ego', 'ae',
    'bren esports', 'bren',
    
    # CIS Teams
    'virtus pro', 'virtus.pro', 'vp',
    'team spirit', 'spirit',
    'gambit esports', 'gambit',
    'forze',
    'nemiga gaming', 'nemiga',
    
    # Other Notable
    '100 thieves', '100t',
    'sentinels', 'sen',
    'tsm', 'team solomid',
    'dignitas', 'dig',
    'immortals', 'imt',
    'misfits gaming', 'misfits',
    'rogue',
    'mad lions', 'mad',
    'karmine corp', 'kc', 'kcorp',
    'team envy', 'envy', 'nv',
    'nip', 'ninjas in pyjamas',
    'ence',
    'north',
    'heroic',
    'big', 'berlin international gaming',
    'sprout',
    'movistar riders', 'riders',
}

# Паттерны для проверки (только буквы, цифры, пробелы и базовые символы)
ALLOWED_PATTERN = re.compile(r'^[a-zA-Zа-яА-ЯёЁ0-9\s\-_.]+$')

# Минимальное и максимальное количество букв (должны быть хоть какие-то буквы)
MIN_LETTERS = 2


def validate_team_name(name: str) -> Tuple[bool, str]:
    """
    Валидация названия команды
    
    Args:
        name: Название команды для проверки
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
        - is_valid: True если название допустимо, False если нет
        - error_message: Сообщение об ошибке (пустая строка если валидно)
    """
    # Базовые проверки
    if not name or not name.strip():
        return False, "❌ Название не может быть пустым"
    
    cleaned_name = name.strip()
    
    # СНАЧАЛА проверяем на запрещённые бренды (даже короткие типа T1, OG)
    name_lower = cleaned_name.lower()
    
    # Точное совпадение
    if name_lower in FORBIDDEN_TEAM_NAMES:
        return False, f"❌ Название '{cleaned_name}' зарезервировано\n\n💡 Это название известной киберспортивной организации. Выберите уникальное название для вашей команды."
    
    # Проверка длины (ПОСЛЕ проверки брендов)
    if len(cleaned_name) < 3:
        return False, "❌ Название слишком короткое (минимум 3 символа)"
    
    if len(cleaned_name) > 50:
        return False, "❌ Название слишком длинное (максимум 50 символов)"
    
    # Проверка на недопустимые спецсимволы
    if not ALLOWED_PATTERN.match(cleaned_name):
        # Находим недопустимые символы
        invalid_chars = set()
        for char in cleaned_name:
            if not re.match(r'[a-zA-Zа-яА-ЯёЁ0-9\s\-_.]', char):
                invalid_chars.add(char)
        
        if invalid_chars:
            chars_str = ', '.join(f'"{c}"' for c in invalid_chars)
            return False, f"❌ Название содержит недопустимые символы: {chars_str}\n\n💡 Разрешены: буквы (A-Z, а-я), цифры, пробелы, дефис, точка, подчёркивание"
        
        return False, "❌ Название содержит недопустимые символы\n\n💡 Разрешены: буквы (A-Z, а-я), цифры, пробелы, дефис, точка, подчёркивание"
    
    # Проверка что есть хоть какие-то буквы
    letter_count = sum(1 for c in cleaned_name if c.isalpha())
    if letter_count < MIN_LETTERS:
        return False, f"❌ Название должно содержать минимум {MIN_LETTERS} буквы"
    
    # Проверка на вхождение известных брендов как отдельных слов
    name_words = set(name_lower.split())
    for forbidden_name in FORBIDDEN_TEAM_NAMES:
        forbidden_words = set(forbidden_name.split())
        
        # Если все слова из запрещенного названия есть в названии команды
        if forbidden_words and forbidden_words.issubset(name_words):
            return False, f"❌ Название содержит бренд известной организации\n\n💡 Не используйте названия профессиональных киберспортивных команд."
    
    # Всё ок
    return True, ""


def is_valid_team_name(name: str) -> bool:
    """
    Быстрая проверка валидности названия (без сообщения об ошибке)
    
    Args:
        name: Название команды
        
    Returns:
        bool: True если название допустимо
    """
    is_valid, _ = validate_team_name(name)
    return is_valid


def get_validation_help() -> str:
    """
    Получить справку по правилам валидации названий команд
    
    Returns:
        str: Текст справки
    """
    return """📋 **Требования к названию команды:**

✅ **Допустимо:**
▪️ Длина: от 3 до 50 символов
▪️ Буквы: латиница (A-Z), кириллица (а-я)
▪️ Цифры: 0-9
▪️ Символы: пробел, дефис (-), точка (.), подчёркивание (_)
▪️ Минимум 2 буквы в названии

❌ **Запрещено:**
▪️ Спецсимволы: @, #, $, %, &, *, и т.д.
▪️ Эмодзи и юникод символы
▪️ Названия известных киберспортивных организаций
▪️ Только цифры без букв

💡 **Примеры правильных названий:**
▪️ Cyber Warriors
▪️ Pro-Gamers_KG
▪️ Team Alpha 2025
▪️ Киберспорт.КГ
▪️ Легенды_Бишкек

💡 **Примеры неправильных названий:**
▪️ Team Liquid (зарезервировано)
▪️ Na`Vi Pro (спецсимвол `)
▪️ Team@123 (спецсимвол @)
▪️ 12345 (только цифры)
▪️ FaZe Clan (зарезервировано)"""
