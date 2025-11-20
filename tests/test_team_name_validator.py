"""
Юнит-тесты для валидатора названий команд
"""
import unittest
from utils.team_name_validator import validate_team_name, is_valid_team_name, get_validation_help


class TestTeamNameValidator(unittest.TestCase):
    """Тесты валидатора названий команд"""
    
    # ========== ТЕСТЫ НА КОРРЕКТНЫЕ НАЗВАНИЯ ==========
    
    def test_valid_english_name(self):
        """Тест: корректное английское название"""
        is_valid, error = validate_team_name("Cyber Warriors")
        self.assertTrue(is_valid, f"Название 'Cyber Warriors' должно быть валидным, но получено: {error}")
        self.assertEqual(error, "")
    
    def test_valid_russian_name(self):
        """Тест: корректное русское название"""
        is_valid, error = validate_team_name("Киберспорт КГ")
        self.assertTrue(is_valid, f"Название 'Киберспорт КГ' должно быть валидным, но получено: {error}")
        self.assertEqual(error, "")
    
    def test_valid_mixed_language(self):
        """Тест: смешанное название (латиница + кириллица)"""
        is_valid, error = validate_team_name("Team Легенда")
        self.assertTrue(is_valid, f"Название 'Team Легенда' должно быть валидным, но получено: {error}")
        self.assertEqual(error, "")
    
    def test_valid_with_numbers(self):
        """Тест: название с цифрами"""
        is_valid, error = validate_team_name("Pro Gamers 2025")
        self.assertTrue(is_valid, f"Название 'Pro Gamers 2025' должно быть валидным, но получено: {error}")
        self.assertEqual(error, "")
    
    def test_valid_with_dash(self):
        """Тест: название с дефисом"""
        is_valid, error = validate_team_name("Pro-Gamers")
        self.assertTrue(is_valid, f"Название 'Pro-Gamers' должно быть валидным, но получено: {error}")
        self.assertEqual(error, "")
    
    def test_valid_with_underscore(self):
        """Тест: название с подчёркиванием"""
        is_valid, error = validate_team_name("Cyber_Warriors")
        self.assertTrue(is_valid, f"Название 'Cyber_Warriors' должно быть валидным, но получено: {error}")
        self.assertEqual(error, "")
    
    def test_valid_with_dot(self):
        """Тест: название с точкой"""
        is_valid, error = validate_team_name("Team.Pro")
        self.assertTrue(is_valid, f"Название 'Team.Pro' должно быть валидным, но получено: {error}")
        self.assertEqual(error, "")
    
    def test_valid_all_allowed_symbols(self):
        """Тест: название со всеми разрешёнными символами"""
        is_valid, error = validate_team_name("Team_Pro-2025.КГ")
        self.assertTrue(is_valid, f"Название 'Team_Pro-2025.КГ' должно быть валидным, но получено: {error}")
        self.assertEqual(error, "")
    
    def test_valid_min_length(self):
        """Тест: минимальная длина (3 символа)"""
        is_valid, error = validate_team_name("ABC")
        self.assertTrue(is_valid, f"Название 'ABC' должно быть валидным, но получено: {error}")
        self.assertEqual(error, "")
    
    def test_valid_max_length(self):
        """Тест: максимальная длина (50 символов)"""
        long_name = "A" * 50
        is_valid, error = validate_team_name(long_name)
        self.assertTrue(is_valid, f"Название из 50 символов должно быть валидным, но получено: {error}")
        self.assertEqual(error, "")
    
    # ========== ТЕСТЫ НА ДЛИНУ ==========
    
    def test_invalid_too_short(self):
        """Тест: слишком короткое название (< 3 символов)"""
        is_valid, error = validate_team_name("AB")
        self.assertFalse(is_valid, "Название 'AB' должно быть невалидным (слишком короткое)")
        self.assertIn("короткое", error.lower())
    
    def test_invalid_too_long(self):
        """Тест: слишком длинное название (> 50 символов)"""
        long_name = "A" * 51
        is_valid, error = validate_team_name(long_name)
        self.assertFalse(is_valid, "Название из 51 символа должно быть невалидным (слишком длинное)")
        self.assertIn("длинное", error.lower())
    
    def test_invalid_empty(self):
        """Тест: пустое название"""
        is_valid, error = validate_team_name("")
        self.assertFalse(is_valid, "Пустое название должно быть невалидным")
        self.assertIn("пустым", error.lower())
    
    def test_invalid_only_spaces(self):
        """Тест: только пробелы"""
        is_valid, error = validate_team_name("   ")
        self.assertFalse(is_valid, "Название из пробелов должно быть невалидным")
        self.assertIn("пустым", error.lower())
    
    # ========== ТЕСТЫ НА СПЕЦСИМВОЛЫ ==========
    
    def test_invalid_special_char_at(self):
        """Тест: недопустимый символ @"""
        is_valid, error = validate_team_name("Team@Pro")
        self.assertFalse(is_valid, "Название 'Team@Pro' должно быть невалидным (символ @)")
        self.assertIn("@", error)
    
    def test_invalid_special_char_hash(self):
        """Тест: недопустимый символ #"""
        is_valid, error = validate_team_name("Team#Pro")
        self.assertFalse(is_valid, "Название 'Team#Pro' должно быть невалидным (символ #)")
        self.assertIn("#", error)
    
    def test_invalid_special_char_dollar(self):
        """Тест: недопустимый символ $"""
        is_valid, error = validate_team_name("Team$Pro")
        self.assertFalse(is_valid, "Название 'Team$Pro' должно быть невалидным (символ $)")
        self.assertIn("$", error)
    
    def test_invalid_special_char_percent(self):
        """Тест: недопустимый символ %"""
        is_valid, error = validate_team_name("Team%Pro")
        self.assertFalse(is_valid, "Название 'Team%Pro' должно быть невалидным (символ %)")
        self.assertIn("%", error)
    
    def test_invalid_special_char_ampersand(self):
        """Тест: недопустимый символ &"""
        is_valid, error = validate_team_name("Team&Pro")
        self.assertFalse(is_valid, "Название 'Team&Pro' должно быть невалидным (символ &)")
        self.assertIn("&", error)
    
    def test_invalid_special_char_asterisk(self):
        """Тест: недопустимый символ *"""
        is_valid, error = validate_team_name("Team*Pro")
        self.assertFalse(is_valid, "Название 'Team*Pro' должно быть невалидным (символ *)")
        self.assertIn("*", error)
    
    def test_invalid_special_char_parenthesis(self):
        """Тест: недопустимые символы ()"""
        is_valid, error = validate_team_name("Team(Pro)")
        self.assertFalse(is_valid, "Название 'Team(Pro)' должно быть невалидным (символы скобок)")
        self.assertTrue("(" in error or ")" in error)
    
    def test_invalid_special_char_plus(self):
        """Тест: недопустимый символ +"""
        is_valid, error = validate_team_name("Team+Pro")
        self.assertFalse(is_valid, "Название 'Team+Pro' должно быть невалидным (символ +)")
        self.assertIn("+", error)
    
    def test_invalid_special_char_equals(self):
        """Тест: недопустимый символ ="""
        is_valid, error = validate_team_name("Team=Pro")
        self.assertFalse(is_valid, "Название 'Team=Pro' должно быть невалидным (символ =)")
        self.assertIn("=", error)
    
    def test_invalid_special_char_brackets(self):
        """Тест: недопустимые символы []"""
        is_valid, error = validate_team_name("Team[Pro]")
        self.assertFalse(is_valid, "Название 'Team[Pro]' должно быть невалидным (символы [])")
        self.assertTrue("[" in error or "]" in error)
    
    def test_invalid_special_char_slash(self):
        """Тест: недопустимый символ /"""
        is_valid, error = validate_team_name("Team/Pro")
        self.assertFalse(is_valid, "Название 'Team/Pro' должно быть невалидным (символ /)")
        self.assertIn("/", error)
    
    def test_invalid_special_char_backslash(self):
        """Тест: недопустимый символ \\"""
        is_valid, error = validate_team_name("Team\\Pro")
        self.assertFalse(is_valid, "Название 'Team\\Pro' должно быть невалидным (символ \\)")
        self.assertIn("\\", error)
    
    def test_invalid_emoji(self):
        """Тест: эмодзи недопустимы"""
        is_valid, error = validate_team_name("Team 🔥 Pro")
        self.assertFalse(is_valid, "Название с эмодзи должно быть невалидным")
        self.assertIn("символы", error.lower())
    
    # ========== ТЕСТЫ НА МИНИМАЛЬНОЕ КОЛИЧЕСТВО БУКВ ==========
    
    def test_invalid_only_numbers(self):
        """Тест: только цифры без букв"""
        is_valid, error = validate_team_name("12345")
        self.assertFalse(is_valid, "Название '12345' должно быть невалидным (только цифры)")
        self.assertIn("букв", error.lower())
    
    def test_invalid_one_letter(self):
        """Тест: только одна буква"""
        is_valid, error = validate_team_name("A123")
        self.assertFalse(is_valid, "Название 'A123' должно быть невалидным (только 1 буква)")
        self.assertIn("букв", error.lower())
    
    def test_valid_two_letters(self):
        """Тест: две буквы (минимум)"""
        is_valid, error = validate_team_name("AB1")
        self.assertTrue(is_valid, f"Название 'AB1' должно быть валидным (2 буквы), но получено: {error}")
    
    # ========== ТЕСТЫ НА ЗАПРЕЩЁННЫЕ БРЕНДЫ ==========
    
    def test_invalid_team_liquid(self):
        """Тест: Team Liquid запрещено"""
        is_valid, error = validate_team_name("Team Liquid")
        self.assertFalse(is_valid, "Название 'Team Liquid' должно быть запрещено")
        self.assertTrue("зарезервировано" in error.lower() or "организации" in error.lower())
    
    def test_invalid_navi(self):
        """Тест: Navi запрещено"""
        is_valid, error = validate_team_name("Navi")
        self.assertFalse(is_valid, "Название 'Navi' должно быть запрещено")
        self.assertTrue("зарезервировано" in error.lower() or "организации" in error.lower())
    
    def test_invalid_faze_clan(self):
        """Тест: FaZe Clan запрещено"""
        is_valid, error = validate_team_name("FaZe Clan")
        self.assertFalse(is_valid, "Название 'FaZe Clan' должно быть запрещено")
        self.assertTrue("зарезервировано" in error.lower() or "организации" in error.lower())
    
    def test_invalid_g2_esports(self):
        """Тест: G2 Esports запрещено"""
        is_valid, error = validate_team_name("G2 Esports")
        self.assertFalse(is_valid, "Название 'G2 Esports' должно быть запрещено")
        self.assertTrue("зарезервировано" in error.lower() or "организации" in error.lower())
    
    def test_invalid_fnatic(self):
        """Тест: Fnatic запрещено"""
        is_valid, error = validate_team_name("Fnatic")
        self.assertFalse(is_valid, "Название 'Fnatic' должно быть запрещено")
        self.assertTrue("зарезервировано" in error.lower() or "организации" in error.lower())
    
    def test_invalid_cloud9(self):
        """Тест: Cloud9 запрещено"""
        is_valid, error = validate_team_name("Cloud9")
        self.assertFalse(is_valid, "Название 'Cloud9' должно быть запрещено")
        self.assertTrue("зарезервировано" in error.lower() or "организации" in error.lower())
    
    def test_invalid_t1(self):
        """Тест: T1 запрещено"""
        is_valid, error = validate_team_name("T1")
        self.assertFalse(is_valid, "Название 'T1' должно быть запрещено")
        self.assertTrue("зарезервировано" in error.lower() or "организации" in error.lower())
    
    def test_invalid_og(self):
        """Тест: OG запрещено"""
        is_valid, error = validate_team_name("OG")
        self.assertFalse(is_valid, "Название 'OG' должно быть запрещено")
        self.assertTrue("зарезервировано" in error.lower() or "организации" in error.lower())
    
    def test_invalid_secret(self):
        """Тест: Team Secret запрещено"""
        is_valid, error = validate_team_name("Team Secret")
        self.assertFalse(is_valid, "Название 'Team Secret' должно быть запрещено")
        self.assertTrue("зарезервировано" in error.lower() or "организации" in error.lower())
    
    def test_invalid_virtus_pro(self):
        """Тест: Virtus Pro запрещено"""
        is_valid, error = validate_team_name("Virtus Pro")
        self.assertFalse(is_valid, "Название 'Virtus Pro' должно быть запрещено")
        self.assertTrue("зарезервировано" in error.lower() or "организации" in error.lower())
    
    def test_invalid_nip(self):
        """Тест: NiP запрещено"""
        is_valid, error = validate_team_name("NiP")
        self.assertFalse(is_valid, "Название 'NiP' должно быть запрещено")
        self.assertTrue("зарезервировано" in error.lower() or "организации" in error.lower())
    
    def test_invalid_case_insensitive(self):
        """Тест: проверка регистронезависимости для брендов"""
        test_cases = ["team liquid", "TEAM LIQUID", "TeAm LiQuId", "tEaM lIqUiD"]
        for name in test_cases:
            is_valid, error = validate_team_name(name)
            self.assertFalse(is_valid, f"Название '{name}' должно быть запрещено (любой регистр)")
            self.assertTrue("зарезервировано" in error.lower() or "организации" in error.lower())
    
    def test_invalid_brand_in_middle(self):
        """Тест: бренд в середине названия"""
        is_valid, error = validate_team_name("Pro Liquid Gaming")
        self.assertFalse(is_valid, "Название 'Pro Liquid Gaming' должно быть запрещено (содержит Liquid)")
        self.assertTrue("организации" in error.lower() or "бренд" in error.lower())
    
    # ========== ТЕСТЫ НА ГРАНИЧНЫЕ СЛУЧАИ ==========
    
    def test_valid_similar_to_brand(self):
        """Тест: похожее, но допустимое название"""
        is_valid, error = validate_team_name("Team Liquidators")
        self.assertTrue(is_valid, f"Название 'Team Liquidators' должно быть валидным (не точное совпадение), но получено: {error}")
    
    def test_invalid_none_input(self):
        """Тест: None как входное значение"""
        is_valid, error = validate_team_name(None)
        self.assertFalse(is_valid, "None должен быть невалидным")
        self.assertIn("пустым", error.lower())
    
    def test_whitespace_trimming(self):
        """Тест: обрезка пробелов"""
        is_valid, error = validate_team_name("  Cyber Warriors  ")
        self.assertTrue(is_valid, f"Название с пробелами по краям должно быть валидным, но получено: {error}")
    
    # ========== ТЕСТЫ ВСПОМОГАТЕЛЬНЫХ ФУНКЦИЙ ==========
    
    def test_is_valid_team_name_function(self):
        """Тест: функция is_valid_team_name"""
        self.assertTrue(is_valid_team_name("Cyber Warriors"))
        self.assertFalse(is_valid_team_name("Team@Pro"))
        self.assertFalse(is_valid_team_name("Team Liquid"))
    
    def test_get_validation_help(self):
        """Тест: функция get_validation_help возвращает строку"""
        help_text = get_validation_help()
        self.assertIsInstance(help_text, str)
        self.assertTrue(len(help_text) > 0)
        self.assertIn("Допустимо", help_text)
        self.assertIn("Запрещено", help_text)


# ========== ЗАПУСК ТЕСТОВ ==========

if __name__ == '__main__':
    # Запуск с детальным выводом
    unittest.main(verbosity=2)
