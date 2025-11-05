"""
Модуль для работы с Telegram Client API через Telethon
"""
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.types import User, Channel, Chat
from config import API_ID, API_HASH, PHONE_NUMBER, SESSION_FILE, ADMIN_ID

logger = logging.getLogger(__name__)


class TelegramClientManager:
    """Менеджер для работы с Telegram Client API"""
    
    def __init__(self):
        self.client = TelegramClient(
            str(SESSION_FILE),
            API_ID,
            API_HASH
        )
        self.is_authorized = False
        self.admin_id = ADMIN_ID
    
    async def start(self):
        """Запуск клиента и авторизация"""
        try:
            # Проверяем, есть ли уже сохраненная сессия
            if self.client.is_connected():
                await self.client.disconnect()
            
            # Пытаемся подключиться с сохраненной сессией
            await self.client.connect()
            
            # Проверяем, авторизован ли уже
            if await self.client.is_user_authorized():
                self.is_authorized = True
                me = await self.client.get_me()
                logger.info(f"Авторизован как: {me.first_name} (@{me.username})")
                return True
            
            # Если не авторизован, запрашиваем код
            await self.client.send_code_request(PHONE_NUMBER)
            logger.info("Код отправлен в Telegram")
            
            # Запрашиваем код интерактивно
            import asyncio
            code = await asyncio.get_event_loop().run_in_executor(
                None, input, "Please enter the code you received: "
            )
            
            # Авторизуемся с кодом
            try:
                await self.client.sign_in(PHONE_NUMBER, code)
            except SessionPasswordNeededError:
                # Требуется двухфакторная аутентификация
                logger.info("Требуется двухфакторная аутентификация")
                
                # Запрашиваем пароль интерактивно
                import asyncio
                password = await asyncio.get_event_loop().run_in_executor(
                    None, input, "Please enter your 2FA password: "
                )
                
                # Авторизуемся с паролем
                await self.client.sign_in(password=password)
            
            self.is_authorized = True
            
            # Получаем информацию о текущем пользователе
            me = await self.client.get_me()
            logger.info(f"Авторизован как: {me.first_name} (@{me.username})")
            
            return True
        except PhoneCodeInvalidError:
            logger.error("Неверный код подтверждения")
            return False
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            return False
    
    async def stop(self):
        """Остановка клиента"""
        if self.client.is_connected():
            await self.client.disconnect()
        logger.info("Telegram клиент отключен")
    
    async def send_message(self, chat_id, text, image_path=None):
        """
        Отправка сообщения в чат
        
        Args:
            chat_id: ID чата или username
            text: Текст сообщения
            image_path: Путь к изображению (опционально)
            
        Returns:
            True если сообщение отправлено успешно
        """
        try:
            if image_path and image_path.exists():
                # Отправляем фото с подписью
                await self.client.send_file(
                    chat_id,
                    str(image_path),
                    caption=text,
                    parse_mode='html'
                )
            else:
                # Отправляем только текст
                await self.client.send_message(
                    chat_id,
                    text,
                    parse_mode='html'
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в {chat_id}: {e}")
            return False
    
    async def get_chat_info(self, chat_identifier):
        """
        Получение информации о чате
        
        Args:
            chat_identifier: ID чата, username или ссылка
            
        Returns:
            Кортеж (chat_id, title, chat_type) или None
        """
        try:
            chat = await self.client.get_entity(chat_identifier)
            
            chat_id = str(chat.id)
            title = getattr(chat, 'title', 'Unknown')
            chat_type = type(chat).__name__
            
            logger.info(f"Найден чат: {chat_id}, {title}, {chat_type}")
            
            return (chat_id, title, chat_type)
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о чате {chat_identifier}: {e}")
            return None
    
    async def check_chat_access(self, chat_id):
        """
        Проверка доступа к чату
        
        Args:
            chat_id: ID чата
            
        Returns:
            True если есть доступ к чату
        """
        try:
            chat = await self.client.get_entity(chat_id)
            
            # Проверяем, можем ли мы отправлять сообщения
            if hasattr(chat, 'send_message'):
                return True
            
            # Для каналов проверяем права
            if isinstance(chat, Channel):
                # Проверяем, является ли пользователь участником
                try:
                    await self.client.get_participants(chat, limit=1)
                    return True
                except:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка проверки доступа к чату {chat_id}: {e}")
            return False
    
    
    def is_connected(self):
        """Проверка подключения"""
        return self.client.is_connected()
    
    async def get_me(self):
        """Получение информации о текущем пользователе"""
        try:
            return await self.client.get_me()
        except Exception as e:
            logger.error(f"Ошибка получения информации о пользователе: {e}")
            return None


# Глобальный экземпляр клиента
telegram_client = TelegramClientManager()
