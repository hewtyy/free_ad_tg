"""
Конфигурация для автоматической публикации рекламных постов через Telegram Client API
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram API данные (получить на https://my.telegram.org)
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', 'YOUR_API_HASH_HERE')

# Номер телефона для авторизации
PHONE_NUMBER = os.getenv('PHONE_NUMBER', 'YOUR_PHONE_NUMBER_HERE')

# ID администратора (получить у @userinfobot)
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

# Пути к файлам
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
POST_TEXT_FILE = DATA_DIR / 'post.txt'
POST_IMAGE_FILE = DATA_DIR / 'image.jpg'
DATABASE_FILE = DATA_DIR / 'database.db'
SESSION_FILE = DATA_DIR / 'session.session'

# Настройки публикации
MIN_DELAY = 30  # Минимальная задержка между отправками (секунды)
MAX_DELAY = 120  # Максимальная задержка между отправками (секунды)
DEFAULT_INTERVAL = 24  # Интервал по умолчанию (часы)

# Проверка обязательных параметров
if API_ID == 0:
    raise ValueError("Необходимо установить API_ID в переменных окружения")

if API_HASH == 'YOUR_API_HASH_HERE':
    raise ValueError("Необходимо установить API_HASH в переменных окружения")

if PHONE_NUMBER == 'YOUR_PHONE_NUMBER_HERE':
    raise ValueError("Необходимо установить PHONE_NUMBER в переменных окружения")

if ADMIN_ID == 0:
    raise ValueError("Необходимо установить ADMIN_ID в переменных окружения")
