#!/bin/bash

# Скрипт для создания резервной копии БД

BACKUP_DIR="/home/ENASGame_bot_2025/backups"
DB_PATH="/home/ENASGame_bot_2025/tournament_bot.db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/tournament_bot_$DATE.db"

# Создаём папку для бэкапов если не существует
mkdir -p $BACKUP_DIR

# Создаём бэкап
echo "📦 Создание резервной копии БД..."
cp $DB_PATH $BACKUP_FILE

if [ $? -eq 0 ]; then
    echo "✅ Бэкап создан: $BACKUP_FILE"
    
    # Показываем размер
    SIZE=$(du -h $BACKUP_FILE | cut -f1)
    echo "📊 Размер: $SIZE"
    
    # Удаляем бэкапы старше 30 дней
    find $BACKUP_DIR -name "tournament_bot_*.db" -mtime +30 -delete
    echo "🗑️  Старые бэкапы (>30 дней) удалены"
    
    # Показываем список всех бэкапов
    echo ""
    echo "📋 Доступные бэкапы:"
    ls -lh $BACKUP_DIR/tournament_bot_*.db 2>/dev/null | awk '{print $9, "("$5")"}'
else
    echo "❌ Ошибка создания бэкапа!"
    exit 1
fi
