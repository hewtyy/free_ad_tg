"""
Основной файл запуска для автоматической публикации рекламных постов через Telegram Client API
с веб-интерфейсом для управления
"""
import asyncio
import logging
import sys
import threading
from pathlib import Path

from config import API_ID, API_HASH, PHONE_NUMBER, ADMIN_ID, DATA_DIR
from db import db
from scheduler import PostScheduler
from telegram_client import telegram_client
from web_server import run_web_server


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


async def on_startup():
    """Функция, выполняемая при запуске"""
    logger.info("Запуск системы публикации...")
    
    # Создаем директорию для данных, если её нет
    DATA_DIR.mkdir(exist_ok=True)
    
    # Инициализируем базу данных
    await db.init_db()
    logger.info("База данных инициализирована")
    
    # Запускаем Telegram клиент
    success = await telegram_client.start()
    if not success:
        logger.error("Не удалось авторизоваться в Telegram")
        return False
    
    # Создаем и запускаем планировщик
    scheduler = PostScheduler()
    await scheduler.start()

    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(
        target=run_web_server,
        args=('0.0.0.0', 5000, False),
        daemon=True
    )
    web_thread.start()
    logger.info("Веб-сервер запущен на порту 5000")
    
    # Получаем информацию о пользователе для логирования
    try:
        me = await telegram_client.get_me()
        logger.info(f"Авторизован как: {me.first_name} (@{me.username})")
    except Exception as e:
        logger.warning(f"Не удалось получить информацию о пользователе: {e}")
    
    logger.info("Система успешно запущена и готова к работе")
    return True


async def on_shutdown():
    """Функция, выполняемая при остановке"""
    logger.info("Остановка системы...")

    # Останавливаем Telegram клиент
    await telegram_client.stop()
    logger.info("Система остановлена")


async def main():
    """Основная функция запуска"""
    try:
        # Запускаем систему
        success = await on_startup()
        if not success:
            logger.error("Не удалось запустить систему")
            return

        logger.info("Система запущена. Веб-интерфейс доступен на http://localhost:5000")
        logger.info("Ожидание веб-запросов...")

        # Ожидаем до получения сигнала остановки
        try:
            while telegram_client.is_connected():
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки (Ctrl+C)")

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise
    finally:
        # Останавливаем систему
        await on_shutdown()


if __name__ == "__main__":
    try:
        # Проверяем наличие API данных
        if API_ID == 0:
            print("❌ Ошибка: Не установлен API_ID")
            print("Создайте файл .env и добавьте в него:")
            print("API_ID=your_api_id_here")
            print("API_HASH=your_api_hash_here")
            print("PHONE_NUMBER=your_phone_number_here")
            print("ADMIN_ID=your_admin_id_here")
            sys.exit(1)
        
        if API_HASH == 'YOUR_API_HASH_HERE':
            print("❌ Ошибка: Не установлен API_HASH")
            print("Получите API данные на https://my.telegram.org")
            sys.exit(1)
        
        if PHONE_NUMBER == 'YOUR_PHONE_NUMBER_HERE':
            print("❌ Ошибка: Не установлен PHONE_NUMBER")
            print("Добавьте в .env файл ваш номер телефона")
            sys.exit(1)
        
        if ADMIN_ID == 0:
            print("❌ Ошибка: Не установлен ADMIN_ID")
            print("Добавьте в .env файл ваш Telegram ID")
            sys.exit(1)
        
        print("🚀 Запуск системы автоматической публикации...")
        print(f"📱 Номер телефона: {PHONE_NUMBER}")
        print(f"📊 Администратор: {ADMIN_ID}")
        print(f"📁 Директория данных: {DATA_DIR}")
        print("⚠️  При первом запуске потребуется ввести код подтверждения")
        
        # Запускаем систему
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n👋 Система остановлена пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
