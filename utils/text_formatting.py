"""
Утилиты для форматирования текста в Telegram
"""
import re
from typing import Optional


def escape_markdown(text: str) -> str:
    """
    Экранирует специальные символы Markdown v2 для Telegram
    
    Символы которые нужно экранировать:
    _ * [ ] ( ) ~ ` > # + - = | { } . !
    """
    if not text:
        return ""
    
    # Список символов для экранирования в MarkdownV2
    special_chars = r'_*[]()~`>#+-=|{}.!'
    
    # Экранируем каждый специальный символ
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def escape_markdown_simple(text: str) -> str:
    """
    Простое экранирование основных Markdown символов
    Используется для обычного Markdown (не V2)
    """
    if not text:
        return ""
    
    # Экранируем только основные символы для обычного Markdown
    replacements = {
        '_': '\\_',
        '*': '\\*',
        '[': '\\[',
        '`': '\\`'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


def escape_html(text: str) -> str:
    """
    Экранирует HTML спецсимволы для использования в HTML режиме Telegram
    """
    if not text:
        return ""
    
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


def format_date(date_str: str) -> str:
    """
    Форматирует дату для отображения
    """
    if not date_str:
        return "Не указана"
    return date_str


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезает текст до указанной длины с добавлением суффикса
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
