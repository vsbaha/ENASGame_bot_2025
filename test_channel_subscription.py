"""
Тест проверки подписки на обязательные каналы
"""
import asyncio
import logging
from aiogram import Bot
from config.settings import settings
from utils.channel_checker import (
    check_channel_subscription,
    check_all_channels_subscription,
    format_channel_url,
    format_channel_name
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_channel_checker():
    """Тестирование функций проверки подписки"""
    
    print("=" * 60)
    print("🔍 ТЕСТ ПРОВЕРКИ ПОДПИСКИ НА КАНАЛЫ")
    print("=" * 60)
    
    # Создаём бота
    bot = Bot(token=settings.bot_token)
    
    try:
        # Тестовые данные - используем известный ID администратора
        test_user_id = 1189473577  # ID администратора из БД
        test_channels = [
            "@telegram",  # Официальный канал Telegram (публичный)
            "@durov",      # Канал Дурова (публичный)
        ]
        
        print(f"\n👤 Тестовый пользователь: {test_user_id}")
        print(f"📢 Тестовые каналы: {', '.join(test_channels)}\n")
        
        # Тест 1: Проверка одного канала
        print("━" * 60)
        print("ТЕСТ 1: Проверка одного канала")
        print("━" * 60)
        
        for channel in test_channels:
            result = await check_channel_subscription(bot, test_user_id, channel)
            status = "✅ Подписан" if result else "❌ Не подписан"
            print(f"{status}: {channel}")
        
        # Тест 2: Проверка всех каналов
        print("\n" + "━" * 60)
        print("ТЕСТ 2: Проверка всех каналов сразу")
        print("━" * 60)
        
        is_all_subscribed, unsubscribed = await check_all_channels_subscription(
            bot, test_user_id, test_channels
        )
        
        if is_all_subscribed:
            print("✅ Пользователь подписан на все каналы!")
        else:
            print(f"❌ Не подписан на {len(unsubscribed)} канал(ов):")
            for ch in unsubscribed:
                print(f"   • {ch}")
        
        # Тест 3: Форматирование URL и имён
        print("\n" + "━" * 60)
        print("ТЕСТ 3: Форматирование URL и имён")
        print("━" * 60)
        
        test_formats = ["@telegram", "durov", "@channel_name"]
        for channel in test_formats:
            name = format_channel_name(channel)
            url = format_channel_url(channel)
            print(f"Исходный: {channel:20} → Имя: {name:20} → URL: {url}")
        
        # Тест 4: Обработка ошибок
        print("\n" + "━" * 60)
        print("ТЕСТ 4: Обработка несуществующего канала")
        print("━" * 60)
        
        fake_channel = "@nonexistent_channel_12345678"
        result = await check_channel_subscription(bot, test_user_id, fake_channel)
        status = "✅ Подписан" if result else "❌ Не найден/Нет доступа"
        print(f"{status}: {fake_channel}")
        
        print("\n" + "=" * 60)
        print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Ошибка теста: {e}")
        print(f"\n❌ Ошибка выполнения теста: {e}")
    
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(test_channel_checker())
    except KeyboardInterrupt:
        print("\n\n⏹️ Тест прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
