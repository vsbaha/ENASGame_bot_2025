#!/bin/bash

# ================================
# HEALTH CHECK - Проверка работоспособности бота
# ================================

EXIT_CODE=0
BOT_NAME="tournament_bot"
PROJECT_DIR="/home/ENASGame_bot_2025"

echo "🏥 Health Check ENAS Tournament Bot"
echo "===================================="
echo ""

# 1. Проверка сервиса
echo -n "🔍 Проверка сервиса... "
if systemctl is-active --quiet $BOT_NAME; then
    echo "✅ OK"
else
    echo "❌ FAIL - Сервис не запущен"
    EXIT_CODE=1
fi

# 2. Проверка процесса
echo -n "🔍 Проверка процесса Python... "
if pgrep -f "python.*main.py" > /dev/null; then
    echo "✅ OK"
else
    echo "❌ FAIL - Процесс не найден"
    EXIT_CODE=1
fi

# 3. Проверка базы данных
echo -n "🔍 Проверка базы данных... "
if [ -f "$PROJECT_DIR/tournament_bot.db" ]; then
    DB_SIZE=$(stat -f%z "$PROJECT_DIR/tournament_bot.db" 2>/dev/null || stat -c%s "$PROJECT_DIR/tournament_bot.db" 2>/dev/null)
    if [ $DB_SIZE -gt 0 ]; then
        echo "✅ OK ($(numfmt --to=iec-i --suffix=B $DB_SIZE))"
    else
        echo "⚠️  WARNING - БД пустая"
        EXIT_CODE=2
    fi
else
    echo "❌ FAIL - БД не найдена"
    EXIT_CODE=1
fi

# 4. Проверка .env файла
echo -n "🔍 Проверка .env файла... "
if [ -f "$PROJECT_DIR/.env" ]; then
    if grep -q "BOT_TOKEN=" "$PROJECT_DIR/.env" && ! grep -q "your_bot_token_here" "$PROJECT_DIR/.env"; then
        echo "✅ OK"
    else
        echo "⚠️  WARNING - Токен не настроен"
        EXIT_CODE=2
    fi
else
    echo "❌ FAIL - .env не найден"
    EXIT_CODE=1
fi

# 5. Проверка интернета
echo -n "🔍 Проверка интернет соединения... "
if ping -c 1 -W 2 8.8.8.8 &> /dev/null; then
    echo "✅ OK"
else
    echo "❌ FAIL - Нет соединения"
    EXIT_CODE=1
fi

# 6. Проверка Telegram API
echo -n "🔍 Проверка доступа к Telegram API... "
if curl -s --max-time 5 https://api.telegram.org &> /dev/null; then
    echo "✅ OK"
else
    echo "❌ FAIL - API недоступен"
    EXIT_CODE=1
fi

# 7. Проверка свободного места
echo -n "🔍 Проверка свободного места... "
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 90 ]; then
    echo "✅ OK ($DISK_USAGE% используется)"
else
    echo "⚠️  WARNING - Мало места ($DISK_USAGE% используется)"
    EXIT_CODE=2
fi

# 8. Проверка памяти
echo -n "🔍 Проверка использования памяти... "
MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
if [ $MEM_USAGE -lt 90 ]; then
    echo "✅ OK ($MEM_USAGE% используется)"
else
    echo "⚠️  WARNING - Высокое использование ($MEM_USAGE%)"
    EXIT_CODE=2
fi

# 9. Проверка логов на ошибки
echo -n "🔍 Проверка последних логов на ошибки... "
ERROR_COUNT=$(journalctl -u $BOT_NAME --since "5 minutes ago" | grep -i "error\|exception\|critical" | wc -l)
if [ $ERROR_COUNT -eq 0 ]; then
    echo "✅ OK"
else
    echo "⚠️  WARNING - Найдено ошибок: $ERROR_COUNT"
    EXIT_CODE=2
fi

# 10. Проверка времени работы
echo -n "🔍 Время работы бота... "
UPTIME=$(systemctl show $BOT_NAME --property=ActiveEnterTimestamp | cut -d= -f2)
if [ -n "$UPTIME" ]; then
    echo "✅ $UPTIME"
else
    echo "⚠️  Неизвестно"
fi

echo ""
echo "===================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Все проверки пройдены успешно!"
elif [ $EXIT_CODE -eq 2 ]; then
    echo "⚠️  Есть предупреждения, но бот работает"
else
    echo "❌ Обнаружены критические проблемы!"
    echo ""
    echo "Для диагностики выполните:"
    echo "  sudo journalctl -u $BOT_NAME -n 50"
    echo "  sudo systemctl status $BOT_NAME"
fi

exit $EXIT_CODE
