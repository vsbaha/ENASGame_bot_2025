"""
Тест проверки подписки на каналы с логированием
"""
import asyncio
from database.database import init_db
from database.repositories.tournament_repository import TournamentRepository
from utils.channel_checker import check_all_channels_subscription
from aiogram import Bot
from config.settings import settings


async def test_subscription_check():
    """Тест проверки подписки с детальным логированием"""
    
    print("=" * 60)
    print("🔍 ТЕСТ ПРОВЕРКИ ПОДПИСКИ НА КАНАЛЫ")
    print("=" * 60)
    
    # Инициализация
    await init_db()
    bot = Bot(token=settings.bot_token)
    
    try:
        # Получаем турнир
        tournament = await TournamentRepository.get_by_id(1)
        
        if not tournament:
            print("❌ Турнир ID=1 не найден")
            return
        
        print(f"\n📋 Турнир: {tournament.name}")
        print(f"   Статус: {tournament.status}")
        
        # Получаем каналы
        channels = tournament.required_channels_list
        print(f"\n📢 Обязательные каналы:")
        print(f"   Тип: {type(channels)}")
        print(f"   Значение: {channels}")
        print(f"   Длина: {len(channels) if isinstance(channels, (list, str)) else 'N/A'}")
        
        if channels:
            print(f"\n   Элементы списка:")
            for i, ch in enumerate(channels, 1):
                print(f"     {i}. {repr(ch)} (тип: {type(ch).__name__})")
        
        # Тестовый пользователь
        test_user_id = 1189473577
        
        print(f"\n👤 Проверка для пользователя: {test_user_id}")
        print(f"   Запуск check_all_channels_subscription...")
        
        # Проверяем подписку
        is_subscribed, unsubscribed = await check_all_channels_subscription(
            bot,
            test_user_id,
            channels
        )
        
        print(f"\n✅ Результат:")
        print(f"   Все подписаны: {is_subscribed}")
        print(f"   Неподписанные: {unsubscribed}")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await bot.session.close()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_subscription_check())
