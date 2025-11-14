"""
Автоматическая конвертация parse_mode='Markdown' в parse_mode='HTML'
Заменяет **text** на <b>text</b> и добавляет HTML-экранирование где необходимо
"""
import os
import re

# Список файлов для обработки
files_to_process = [
    "handlers/admin/formats.py",
    "handlers/admin/statistics.py",
]

def convert_file(filepath):
    """Конвертирует один файл из Markdown в HTML"""
    print(f"\n{'='*60}")
    print(f"Обработка: {filepath}")
    print(f"{'='*60}")
    
    if not os.path.exists(filepath):
        print(f"⚠️  Файл не найден: {filepath}")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Подсчитываем вхождения
    markdown_count = content.count('parse_mode="Markdown"')
    print(f"Найдено вхождений parse_mode='Markdown': {markdown_count}")
    
    if markdown_count == 0:
        print("✅ Файл уже использует HTML или не требует изменений")
        return
    
    # Простая замена parse_mode
    content = content.replace('parse_mode="Markdown"', 'parse_mode="HTML"')
    
    # Информация о необходимости ручной правки
    if '**' in content:
        print("⚠️  ВНИМАНИЕ: В файле найдены маркеры **text** - требуется ручная конвертация в <b>text</b>")
        print("   Также проверьте наличие HTML-экранирования для динамических данных")
    
    # Сохраняем изменения
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Файл обновлен: заменено {markdown_count} вхождений")
    else:
        print("ℹ️  Изменений не требуется")


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║     АВТОМАТИЧЕСКАЯ КОНВЕРТАЦИЯ MARKDOWN → HTML              ║
╚══════════════════════════════════════════════════════════════╝

ВНИМАНИЕ: Этот скрипт выполняет базовую замену parse_mode.
Для полной конвертации требуется:
1. Заменить **text** на <b>text</b>
2. Заменить *text* на <i>text</i>  
3. Добавить HTML-экранирование: & → &amp;, < → &lt;, > → &gt;
4. Проверить форматирование вручную

Файлы будут изменены БЕЗ создания бэкапов!
""")
    
    response = input("Продолжить? (yes/no): ").lower()
    if response not in ['yes', 'y', 'да']:
        print("Отменено")
        return
    
    for filepath in files_to_process:
        convert_file(filepath)
    
    print(f"\n{'='*60}")
    print("ИТОГО")
    print(f"{'='*60}")
    print(f"Обработано файлов: {len(files_to_process)}")
    print("\n⚠️  СЛЕДУЮЩИЕ ШАГИ:")
    print("1. Проверьте каждый файл вручную")
    print("2. Замените **text** на <b>text</b>")
    print("3. Добавьте HTML-экранирование для переменных")
    print("4. Протестируйте бота")


if __name__ == "__main__":
    main()
