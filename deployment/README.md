# 🚀 Деплой ENAS Tournament Bot

## Быстрый старт (5 минут)

### 1. Подключение к серверу
```bash
ssh root@your_server_ip
```

### 2. Первоначальная настройка (один раз)
```bash
# Скачайте и запустите скрипт настройки
curl -o setup.sh https://raw.githubusercontent.com/vsbaha/ENASGame_bot_2025/main/deployment/setup_server.sh
chmod +x setup.sh
sudo bash setup.sh
```

### 3. Настройка переменных окружения
```bash
nano /home/ENASGame_bot_2025/.env
```

Измените:
```env
BOT_TOKEN=ваш_токен_от_botfather
ADMIN_IDS=ваш_telegram_id,второй_admin_id
ADMIN_CHAT_ID=-1001234567890
CHALLONGE_API_KEY=ваш_challonge_api_key
CHALLONGE_USERNAME=ваш_challonge_username
```

Сохраните: `Ctrl+O`, `Enter`, `Ctrl+X`

### 4. Запуск бота
```bash
sudo systemctl start tournament_bot
sudo systemctl status tournament_bot
```

✅ **Готово!** Бот работает 24/7

---

## Детальная инструкция

### Требования к серверу

**Минимальные:**
- OS: Ubuntu 20.04+ / Debian 11+
- RAM: 512 MB (рекомендуется 1 GB)
- CPU: 1 core
- Disk: 5 GB
- Python: 3.11+

**Рекомендуемые провайдеры:**
- DigitalOcean (от $4/месяц)
- Vultr (от $3.5/месяц)
- Hetzner Cloud (от €4/месяц)
- Timeweb (от 150₽/месяц)
- REG.RU (от 299₽/месяц)

---

## Способ 1: Автоматическая установка (рекомендуется)

### Шаг 1: Скачайте скрипт установки
```bash
cd /tmp
wget https://raw.githubusercontent.com/vsbaha/ENASGame_bot_2025/main/deployment/setup_server.sh
chmod +x setup_server.sh
```

### Шаг 2: Запустите установку
```bash
sudo bash setup_server.sh
```

Скрипт автоматически:
- ✅ Обновит систему
- ✅ Установит Python 3.11, Git, Supervisor
- ✅ Склонирует репозиторий
- ✅ Создаст виртуальное окружение
- ✅ Установит зависимости
- ✅ Настроит systemd сервис
- ✅ Создаст .env файл

### Шаг 3: Настройте .env
```bash
nano /home/ENASGame_bot_2025/.env
```

### Шаг 4: Запустите бота
```bash
sudo systemctl start tournament_bot
sudo systemctl enable tournament_bot  # Автозапуск при перезагрузке
```

---

## Способ 2: Ручная установка

### 1. Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Установка зависимостей
```bash
sudo apt install -y python3.11 python3.11-venv python3-pip git supervisor
```

### 3. Клонирование репозитория
```bash
cd /home
git clone https://github.com/vsbaha/ENASGame_bot_2025.git
cd ENASGame_bot_2025
```

### 4. Создание виртуального окружения
```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 5. Установка зависимостей Python
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Настройка .env
```bash
cp .env.example .env
nano .env
```

### 7. Настройка systemd сервиса
```bash
sudo cp deployment/tournament_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tournament_bot
sudo systemctl start tournament_bot
```

---

## Управление ботом

### Проверка статуса
```bash
sudo systemctl status tournament_bot
```

### Запуск
```bash
sudo systemctl start tournament_bot
```

### Остановка
```bash
sudo systemctl stop tournament_bot
```

### Перезапуск
```bash
sudo systemctl restart tournament_bot
```

### Просмотр логов (реального времени)
```bash
sudo journalctl -u tournament_bot -f
```

### Просмотр последних 100 строк логов
```bash
sudo journalctl -u tournament_bot -n 100
```

### Просмотр логов за сегодня
```bash
sudo journalctl -u tournament_bot --since today
```

---

## Обновление бота

### Автоматическое обновление
```bash
cd /home/ENASGame_bot_2025
sudo bash deployment/deploy.sh
```

### Ручное обновление
```bash
cd /home/ENASGame_bot_2025
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tournament_bot
```

---

## Использование Supervisor (альтернатива systemd)

### 1. Установка
```bash
sudo apt install supervisor
```

### 2. Настройка
```bash
sudo cp deployment/supervisor.conf /etc/supervisor/conf.d/tournament_bot.conf
sudo supervisorctl reread
sudo supervisorctl update
```

### 3. Управление
```bash
sudo supervisorctl status tournament_bot     # Статус
sudo supervisorctl start tournament_bot      # Запуск
sudo supervisorctl stop tournament_bot       # Остановка
sudo supervisorctl restart tournament_bot    # Перезапуск
```

---

## Безопасность

### 1. Создание отдельного пользователя
```bash
sudo adduser botuser
sudo chown -R botuser:botuser /home/ENASGame_bot_2025

# Измените User в service файле
sudo nano /etc/systemd/system/tournament_bot.service
# Замените: User=root -> User=botuser

sudo systemctl daemon-reload
sudo systemctl restart tournament_bot
```

### 2. Настройка Firewall
```bash
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
sudo ufw status
```

### 3. Ограничение доступа к .env
```bash
chmod 600 /home/ENASGame_bot_2025/.env
```

---

## Мониторинг

### Проверка использования ресурсов
```bash
htop
```

### Проверка дискового пространства
```bash
df -h
```

### Проверка памяти
```bash
free -h
```

### Размер базы данных
```bash
du -h /home/ENASGame_bot_2025/tournament_bot.db
```

---

## Резервное копирование

### Создание бэкапа БД
```bash
cd /home/ENASGame_bot_2025
cp tournament_bot.db backups/tournament_bot_$(date +%Y%m%d_%H%M%S).db
```

### Автоматический бэкап (cron)
```bash
sudo crontab -e
```

Добавьте строку (бэкап каждый день в 3:00):
```cron
0 3 * * * cp /home/ENASGame_bot_2025/tournament_bot.db /home/ENASGame_bot_2025/backups/tournament_bot_$(date +\%Y\%m\%d).db
```

---

## Устранение неполадок

### Бот не запускается
```bash
# Проверьте логи
sudo journalctl -u tournament_bot -n 50

# Проверьте .env файл
cat /home/ENASGame_bot_2025/.env

# Проверьте права доступа
ls -la /home/ENASGame_bot_2025/

# Запустите вручную для отладки
cd /home/ENASGame_bot_2025
source venv/bin/activate
python main.py
```

### Бот падает после запуска
```bash
# Проверьте токен бота
grep BOT_TOKEN /home/ENASGame_bot_2025/.env

# Проверьте зависимости
source /home/ENASGame_bot_2025/venv/bin/activate
pip list
```

### Ошибки базы данных
```bash
# Проверьте существование БД
ls -la /home/ENASGame_bot_2025/tournament_bot.db

# Пересоздайте БД (ВНИМАНИЕ: удалит все данные!)
rm /home/ENASGame_bot_2025/tournament_bot.db
cd /home/ENASGame_bot_2025
source venv/bin/activate
python -c "from database.db_manager import init_db; import asyncio; asyncio.run(init_db())"
```

### Нет интернета на сервере
```bash
ping -c 4 google.com
ping -c 4 8.8.8.8
```

---

## Полезные команды

### Перезагрузка сервера
```bash
sudo reboot
```

### Проверка версии Python
```bash
python3.11 --version
```

### Обновление системных пакетов
```bash
sudo apt update && sudo apt upgrade -y
```

### Очистка места на диске
```bash
sudo apt autoremove -y
sudo apt clean
```

---

## CI/CD (GitHub Actions)

Создайте файл `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Server

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /home/ENASGame_bot_2025
            sudo bash deployment/deploy.sh
```

Добавьте секреты в GitHub: Settings → Secrets → Actions

---

## Поддержка

При возникновении проблем:
1. Проверьте логи: `sudo journalctl -u tournament_bot -f`
2. Создайте Issue на GitHub
3. Напишите в Telegram: @your_support_username

---

## Контрольный чеклист ✅

- [ ] Сервер с Ubuntu 20.04+ арендован
- [ ] SSH доступ настроен
- [ ] Скрипт setup_server.sh запущен
- [ ] .env файл настроен с реальными токенами
- [ ] Бот запущен: `systemctl start tournament_bot`
- [ ] Статус активен: `systemctl status tournament_bot`
- [ ] Логи без ошибок: `journalctl -u tournament_bot -f`
- [ ] Бот отвечает в Telegram
- [ ] Автозапуск включён: `systemctl enable tournament_bot`
- [ ] Настроен firewall (если нужно)
- [ ] Настроены бэкапы БД (опционально)

**Если всё ✅ - бот готов к продакшену!** 🎉
