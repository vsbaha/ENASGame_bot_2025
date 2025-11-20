#!/bin/bash

# Скрипт для восстановления БД из бэкапа

BACKUP_DIR="/home/ENASGame_bot_2025/backups"
DB_PATH="/home/ENASGame_bot_2025/tournament_bot.db"

echo "🔄 Восстановление БД из бэкапа"
echo "================================"
echo ""

# Показываем доступные бэкапы
echo "📋 Доступные бэкапы:"
ls -lh $BACKUP_DIR/tournament_bot_*.db 2>/dev/null | nl -w2 -s'. ' | awk '{print $1, $10, "("$6")"}'

if [ $? -ne 0 ]; then
    echo "❌ Бэкапы не найдены!"
    exit 1
fi

echo ""
read -p "Введите номер бэкапа для восстановления: " backup_num

# Получаем путь к выбранному бэкапу
SELECTED_BACKUP=$(ls -t $BACKUP_DIR/tournament_bot_*.db | sed -n "${backup_num}p")

if [ -z "$SELECTED_BACKUP" ]; then
    echo "❌ Некорректный номер!"
    exit 1
fi

echo ""
echo "⚠️  ВНИМАНИЕ: Текущая БД будет заменена!"
echo "Выбранный бэкап: $(basename $SELECTED_BACKUP)"
read -p "Продолжить? (y/n): " confirm

if [ "$confirm" != "y" ]; then
    echo "❌ Отменено"
    exit 0
fi

# Останавливаем бота
echo ""
echo "🛑 Остановка бота..."
systemctl stop tournament_bot

# Создаём бэкап текущей БД на всякий случай
echo "💾 Создание бэкапа текущей БД..."
cp $DB_PATH "$DB_PATH.before_restore.$(date +%Y%m%d_%H%M%S).db"

# Восстанавливаем из бэкапа
echo "🔄 Восстановление..."
cp $SELECTED_BACKUP $DB_PATH

# Запускаем бота
echo "🚀 Запуск бота..."
systemctl start tournament_bot

sleep 2

if systemctl is-active --quiet tournament_bot; then
    echo ""
    echo "✅ БД успешно восстановлена!"
    echo "✅ Бот запущен"
else
    echo ""
    echo "❌ Ошибка запуска бота! Проверьте логи:"
    echo "sudo journalctl -u tournament_bot -n 50"
fi
