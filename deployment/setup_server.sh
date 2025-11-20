#!/bin/bash

# ================================
# ПЕРВОНАЧАЛЬНАЯ НАСТРОЙКА СЕРВЕРА
# ================================

set -e

echo "🔧 Настройка сервера для ENAS Tournament Bot..."

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${YELLOW}ℹ️  $1${NC}"; }

# Проверка root
if [ "$EUID" -ne 0 ]; then 
    print_error "Запустите с правами root: sudo bash setup_server.sh"
    exit 1
fi

# 1. Обновление системы
print_info "Обновление системы..."
apt update && apt upgrade -y
print_success "Система обновлена"

# 2. Установка необходимых пакетов
print_info "Установка базовых пакетов..."
apt install -y python3.11 python3.11-venv python3-pip git supervisor curl wget htop
print_success "Пакеты установлены"

# 3. Создание пользователя для бота (опционально)
print_info "Хотите создать отдельного пользователя для бота? (рекомендуется)"
read -p "Создать пользователя 'botuser'? (y/n): " create_user

if [ "$create_user" = "y" ]; then
    if id "botuser" &>/dev/null; then
        print_info "Пользователь 'botuser' уже существует"
    else
        useradd -m -s /bin/bash botuser
        print_success "Пользователь 'botuser' создан"
    fi
fi

# 4. Клонирование репозитория
print_info "Клонирование репозитория..."
cd /home

if [ -d "ENASGame_bot_2025" ]; then
    print_info "Репозиторий уже существует, обновляем..."
    cd ENASGame_bot_2025
    git pull origin main
else
    git clone https://github.com/vsbaha/ENASGame_bot_2025.git
    cd ENASGame_bot_2025
fi
print_success "Репозиторий готов"

# 5. Создание виртуального окружения
print_info "Создание виртуального окружения..."
python3.11 -m venv venv
source venv/bin/activate
print_success "Виртуальное окружение создано"

# 6. Установка зависимостей
print_info "Установка Python зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt
print_success "Зависимости установлены"

# 7. Создание .env файла
if [ ! -f ".env" ]; then
    print_info "Создание .env файла..."
    cp .env.example .env
    print_error "ВАЖНО: Отредактируйте файл .env с вашими настройками!"
    echo "nano /home/ENASGame_bot_2025/.env"
else
    print_success "Файл .env уже существует"
fi

# 8. Настройка прав доступа
if [ "$create_user" = "y" ]; then
    print_info "Настройка прав доступа..."
    chown -R botuser:botuser /home/ENASGame_bot_2025
    print_success "Права настроены для пользователя botuser"
fi

# 9. Установка systemd service
print_info "Установка systemd сервиса..."
cp deployment/tournament_bot.service /etc/systemd/system/

# Если создан пользователь, меняем User в service файле
if [ "$create_user" = "y" ]; then
    sed -i 's/User=root/User=botuser/g' /etc/systemd/system/tournament_bot.service
fi

systemctl daemon-reload
systemctl enable tournament_bot
print_success "Systemd сервис настроен"

# 10. Настройка firewall (опционально)
print_info "Настроить firewall? (y/n):"
read -p "Настроить UFW? (y/n): " setup_firewall

if [ "$setup_firewall" = "y" ]; then
    print_info "Настройка UFW..."
    ufw allow 22/tcp
    ufw --force enable
    print_success "Firewall настроен (разрешён SSH на порту 22)"
fi

# 11. Создание базы данных (если нужно)
print_info "Инициализация базы данных..."
if [ -f "database/database.py" ]; then
    source venv/bin/activate
    python -c "from database.db_manager import init_db; import asyncio; asyncio.run(init_db())" 2>/dev/null || true
    print_success "База данных инициализирована"
fi

# Итоговая информация
print_success "
===========================================
🎉 СЕРВЕР НАСТРОЕН УСПЕШНО!
===========================================

СЛЕДУЮЩИЕ ШАГИ:

1️⃣  Отредактируйте .env файл с вашими настройками:
   nano /home/ENASGame_bot_2025/.env

2️⃣  Запустите бота:
   sudo systemctl start tournament_bot

3️⃣  Проверьте статус:
   sudo systemctl status tournament_bot

4️⃣  Просмотр логов:
   sudo journalctl -u tournament_bot -f

ПОЛЕЗНЫЕ КОМАНДЫ:
- Перезапуск: sudo systemctl restart tournament_bot
- Остановка: sudo systemctl stop tournament_bot
- Обновление: cd /home/ENASGame_bot_2025 && sudo bash deployment/deploy.sh

===========================================
"
