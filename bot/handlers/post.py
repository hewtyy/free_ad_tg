"""
Модуль для публикации постов в группы и каналы
"""
import asyncio
from pathlib import Path
from config import POST_TEXT_FILE, POST_IMAGE_FILE
from telegram_client import telegram_client


class PostHandler:
    """Класс для обработки публикации постов"""
    
    def __init__(self):
        self.post_text = None
        self.post_image_path = None
        self._load_post_content()
    
    def _load_post_content(self):
        """Загрузка содержимого поста из файлов"""
        try:
            # Загружаем текст поста
            if POST_TEXT_FILE.exists():
                with open(POST_TEXT_FILE, 'r', encoding='utf-8') as f:
                    self.post_text = f.read().strip()
                print(f"Текст поста загружен из {POST_TEXT_FILE}")
            else:
                self.post_text = "Тестовый пост для автоматической публикации"
                print("Файл с текстом поста не найден, используется текст по умолчанию")
            
            # Проверяем наличие изображения
            if POST_IMAGE_FILE.exists():
                self.post_image_path = POST_IMAGE_FILE
                print(f"Изображение найдено: {POST_IMAGE_FILE}")
            else:
                self.post_image_path = None
                print("Файл с изображением не найден, будет отправлен только текст")
                
        except Exception as e:
            print(f"Ошибка при загрузке содержимого поста: {e}")
            self.post_text = "Ошибка загрузки поста"
            self.post_image_path = None
    
    async def send_post_to_group(self, chat_id: str) -> bool:
        """
        Отправка поста в группу или канал
        
        Args:
            chat_id: ID чата для отправки
            
        Returns:
            True если пост отправлен успешно, False в противном случае
        """
        try:
            # Проверяем, что у нас есть текст для отправки
            if not self.post_text:
                print("Нет текста для отправки")
                return False
            
            # Временно отключаем проверку доступа из-за проблем с event loop
            # has_access = await telegram_client.check_chat_access(chat_id)
            # if not has_access:
            #     print(f"Нет доступа к чату {chat_id}")
            #     # Удаляем группу из базы данных
            #     from db import db
            #     await db.remove_group(chat_id)
            #     return False
            
            # Отправляем пост через Telegram Client API
            # Используем синхронный подход для избежания проблем с event loop
            success = await self._send_message_sync(
                chat_id=chat_id,
                text=self.post_text,
                image_path=self.post_image_path
            )
            
            if success:
                print(f"✓ Пост отправлен в {chat_id}")
            else:
                print(f"✗ Ошибка отправки в {chat_id}")
                # Удаляем группу из базы данных при ошибке
                from db import db
                await db.remove_group(chat_id)
            
            return success
            
        except Exception as e:
            print(f"Неожиданная ошибка при отправке в чат {chat_id}: {e}")
            # Удаляем группу из базы данных при ошибке
            from db import db
            await db.remove_group(chat_id)
            return False
    
    async def test_post(self, chat_id: str) -> bool:
        """
        Тестовая отправка поста для проверки
        
        Args:
            chat_id: ID чата для тестирования
            
        Returns:
            True если тест прошел успешно
        """
        print(f"Тестирование отправки поста в чат {chat_id}...")
        return await self.send_post_to_group(chat_id)
    
    def reload_post_content(self):
        """Перезагрузка содержимого поста из файлов"""
        print("Перезагрузка содержимого поста...")
        self._load_post_content()
    
    async def _send_message_sync(self, chat_id: str, text: str, image_path: Path = None) -> bool:
        """Упрощенная отправка сообщения через основной клиент"""
        try:
            # Используем основной клиент напрямую, но в новом event loop
            import asyncio
            import threading
            from telethon import TelegramClient
            from config import API_ID, API_HASH, SESSION_FILE
            
            def send_in_thread():
                # Создаем новый event loop в отдельном потоке
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def send_async():
                    # Создаем отдельную сессию для отправки
                    send_session_file = str(SESSION_FILE).replace('.session', '_send.session')
                    client = TelegramClient(send_session_file, API_ID, API_HASH)
                    
                    try:
                        await client.connect()
                        
                        # Проверяем, авторизован ли клиент
                        if not await client.is_user_authorized():
                            # Копируем данные из основной сессии
                            import shutil
                            shutil.copy2(str(SESSION_FILE), send_session_file)
                            await client.disconnect()
                            client = TelegramClient(send_session_file, API_ID, API_HASH)
                            await client.connect()
                        
                        # Отправляем сообщение
                        # Пробуем разные способы получения entity
                        entity = None
                        
                        # Сначала пробуем как числовой ID
                        try:
                            entity_id = int(chat_id)
                            entity = await client.get_entity(entity_id)
                        except (ValueError, Exception):
                            pass
                        
                        # Если не получилось, пробуем как строку
                        if entity is None:
                            try:
                                entity = await client.get_entity(chat_id)
                            except Exception:
                                pass
                        
                        # Если все еще не получилось, пробуем как username
                        if entity is None:
                            try:
                                # Добавляем @ если его нет
                                username = chat_id if chat_id.startswith('@') else f'@{chat_id}'
                                entity = await client.get_entity(username)
                            except Exception:
                                pass
                        
                        if entity is None:
                            raise Exception(f"Не удалось найти канал с ID: {chat_id}")
                        
                        if image_path and image_path.exists():
                            await client.send_file(entity, file=str(image_path), caption=text, parse_mode='html')
                        else:
                            await client.send_message(entity, text, parse_mode='html')
                        
                        return True
                        
                    except Exception as e:
                        print(f"Ошибка отправки в {chat_id}: {e}")
                        return False
                    finally:
                        await client.disconnect()
                
                return loop.run_until_complete(send_async())
            
            # Запускаем в отдельном потоке
            result = [False]
            def run_send():
                result[0] = send_in_thread()
            
            thread = threading.Thread(target=run_send)
            thread.start()
            thread.join(timeout=30)  # Таймаут 30 секунд
            
            if thread.is_alive():
                print(f"Таймаут отправки в {chat_id}")
                return False
            
            return result[0]
            
        except Exception as e:
            print(f"Ошибка в _send_message_sync для {chat_id}: {e}")
            return False

    def get_post_info(self) -> dict:
        """
        Получение информации о текущем посте
        
        Returns:
            Словарь с информацией о посте
        """
        return {
            'text_length': len(self.post_text) if self.post_text else 0,
            'has_image': self.post_image_path is not None and self.post_image_path.exists(),
            'text_preview': self.post_text[:100] + '...' if self.post_text and len(self.post_text) > 100 else self.post_text
        }
