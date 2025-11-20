#!/bin/bash

# ================================
# СКРИПТ ДЕПЛОЯ БОТА НА СЕРВЕР
# ================================

set -e  # Остановка при ошибке

echo "🚀 Начало деплоя ENAS Tournament Bot..."

# Переменные
PROJECT_DIR="/home/ENASGame_bot_2025"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="tournament_bot"

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Проверка root прав
if [ "$EUID" -ne 0 ]; then 
    print_error "Запустите скрипт с правами root: sudo bash deploy.sh"
    exit 1
fi

# 1. Обновление кода из Git
print_info "Обновление кода из GitHub..."
cd $PROJECT_DIR
git pull origin main
print_success "Код обновлён"

# 2. Активация виртуального окружения
print_info "Активация виртуального окружения..."
source $VENV_DIR/bin/activate
print_success "Виртуальное окружение активировано"

# 3. Установка/обновление зависимостей
print_info "Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt
print_success "Зависимости установлены"

# 4. Миграции базы данных (если есть)
if [ -d "alembic" ]; then
    print_info "Применение миграций БД..."
    alembic upgrade head
    print_success "Миграции применены"
fi

# 5. Проверка .env файла
if [ ! -f "$PROJECT_DIR/.env" ]; then
    print_error "Файл .env не найден! Создайте его на основе .env.example"
    exit 1
fi

# 6. Перезапуск сервиса
print_info "Перезапуск сервиса $SERVICE_NAME..."

if systemctl is-active --quiet $SERVICE_NAME; then
    systemctl restart $SERVICE_NAME
    print_success "Сервис перезапущен"
else
    systemctl start $SERVICE_NAME
    print_success "Сервис запущен"
fi

# 7. Проверка статуса
sleep 2
if systemctl is-active --quiet $SERVICE_NAME; then
    print_success "Бот успешно запущен!"
    systemctl status $SERVICE_NAME --no-pager
else
    print_error "Ошибка запуска бота! Проверьте логи:"
    echo "sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

# 8. Информация
print_info "Полезные команды:"
echo "  - Просмотр логов: sudo journalctl -u $SERVICE_NAME -f"
echo "  - Статус: sudo systemctl status $SERVICE_NAME"
echo "  - Перезапуск: sudo systemctl restart $SERVICE_NAME"
echo "  - Остановка: sudo systemctl stop $SERVICE_NAME"

print_success "Деплой завершён успешно! 🎉"
