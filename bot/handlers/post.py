"""
Модуль для публикации постов в группы и каналы
"""
import asyncio
from pathlib import Path
from datetime import datetime
import random
import pytz
from config import POST_TEXT_FILE, POST_IMAGE_FILE
from telegram_client import telegram_client
from db import db

MOSCOW_TZ = pytz.timezone('Europe/Moscow')


class PostHandler:
    """Класс для обработки публикации постов"""
    
    def __init__(self):
        self.post_text = None
        self.post_image_path = None
        self.use_template = False
        self._load_post_content()
    
    def _load_post_content(self):
        """Загрузка содержимого поста из файлов или шаблона"""
        try:
            # Проверяем, есть ли активный шаблон
            # Используем более безопасный подход для работы с asyncio
            template = None
            try:
                # Пытаемся получить event loop
                try:
                    loop = asyncio.get_running_loop()
                    # Если event loop уже запущен, создаем задачу через create_task
                    # Но это синхронный метод, поэтому используем другой подход
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, db.get_active_template())
                        template = future.result(timeout=1)
                except RuntimeError:
                    # Нет запущенного event loop, можно использовать asyncio.run
                    template = asyncio.run(db.get_active_template())
            except Exception:
                # Если не удалось получить шаблон, просто пропускаем его
                template = None
            
            if template:
                self.post_text = template[2]  # content
                self.use_template = True
                print(f"✓ Текст поста загружен из шаблона '{template[1]}' ({len(self.post_text)} символов)")
            else:
                # Загружаем из файла
                if POST_TEXT_FILE.exists():
                    with open(POST_TEXT_FILE, 'r', encoding='utf-8') as f:
                        self.post_text = f.read().strip()
                    print(f"✓ Текст поста загружен из {POST_TEXT_FILE} ({len(self.post_text)} символов)")
                else:
                    self.post_text = "Тестовый пост для автоматической публикации"
                    print(f"⚠ Файл с текстом поста не найден ({POST_TEXT_FILE}), используется текст по умолчанию")
                self.use_template = False
            
            # Проверяем наличие изображения
            if POST_IMAGE_FILE.exists():
                self.post_image_path = POST_IMAGE_FILE
                print(f"✓ Изображение найдено: {POST_IMAGE_FILE}")
            else:
                self.post_image_path = None
                print(f"ℹ Файл с изображением не найден ({POST_IMAGE_FILE}), будет отправлен только текст")
                
        except Exception as e:
            print(f"❌ Ошибка при загрузке содержимого поста: {e}")
            import traceback
            traceback.print_exc()
            self.post_text = "Ошибка загрузки поста"
            self.post_image_path = None
            self.use_template = False
    
    def _replace_variables(self, text: str, chat_id: str = None, chat_title: str = None) -> str:
        """
        Замена переменных в тексте шаблона
        
        Доступные переменные:
        - {date} - текущая дата
        - {time} - текущее время
        - {datetime} - дата и время
        - {chat_id} - ID чата
        - {chat_title} - название чата
        - {random_number} - случайное число от 1 до 1000
        - {random_number:min:max} - случайное число от min до max
        
        Args:
            text: Текст с переменными
            chat_id: ID чата (опционально)
            chat_title: Название чата (опционально)
            
        Returns:
            Текст с замененными переменными
        """
        now = datetime.now(pytz.utc).astimezone(MOSCOW_TZ)
        
        # Заменяем переменные
        text = text.replace('{date}', now.strftime('%d.%m.%Y'))
        text = text.replace('{time}', now.strftime('%H:%M'))
        text = text.replace('{datetime}', now.strftime('%d.%m.%Y %H:%M'))
        
        if chat_id:
            text = text.replace('{chat_id}', str(chat_id))
        
        if chat_title:
            text = text.replace('{chat_title}', chat_title)
        
        # Обработка {random_number}
        import re
        
        # Заменяем {random_number}
        text = re.sub(r'\{random_number\}', lambda m: str(random.randint(1, 1000)), text)
        
        # Заменяем {random_number:min:max}
        def replace_random_range(match):
            try:
                min_val = int(match.group(1))
                max_val = int(match.group(2))
                return str(random.randint(min_val, max_val))
            except:
                return match.group(0)
        
        text = re.sub(r'\{random_number:(\d+):(\d+)\}', replace_random_range, text)
        
        return text
    
    async def get_post_text(self, chat_id: str = None, chat_title: str = None) -> str:
        """
        Получение текста поста с заменой переменных
        
        Args:
            chat_id: ID чата (для переменных)
            chat_title: Название чата (для переменных)
            
        Returns:
            Текст поста с замененными переменными
        """
        if not self.post_text:
            return ""
        
        if self.use_template:
            return self._replace_variables(self.post_text, chat_id, chat_title)
        else:
            return self.post_text
    
    async def send_post_to_group(self, chat_id: str, chat_title: str = None) -> bool:
        """
        Отправка поста в группу или канал
        
        Args:
            chat_id: ID чата для отправки
            chat_title: Название чата (для переменных в шаблонах)
            
        Returns:
            True если пост отправлен успешно, False в противном случае
        """
        try:
            # Получаем текст поста с заменой переменных
            post_text = await self.get_post_text(chat_id, chat_title)
            
            # Проверяем, что у нас есть текст для отправки
            if not post_text:
                print("Нет текста для отправки")
                return False
            
            # Отправляем пост через Telegram Client API
            success = await self._send_message_sync(
                chat_id=chat_id,
                text=post_text,
                image_path=self.post_image_path
            )
            
            if success:
                print(f"✓ Пост отправлен в {chat_id}")
            else:
                print(f"✗ Ошибка отправки в {chat_id}")
                # Удаляем группу из базы данных при ошибке
                await db.remove_group(chat_id)
            
            return success
            
        except Exception as e:
            print(f"Неожиданная ошибка при отправке в чат {chat_id}: {e}")
            # Удаляем группу из базы данных при ошибке
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
        template = None
        try:
            try:
                loop = asyncio.get_running_loop()
                # Если event loop уже запущен, используем ThreadPoolExecutor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, db.get_active_template())
                    template = future.result(timeout=1)
            except RuntimeError:
                # Нет запущенного event loop, можно использовать asyncio.run
                template = asyncio.run(db.get_active_template())
        except Exception:
            template = None
        
        return {
            'text': self.post_text or '',
            'text_length': len(self.post_text) if self.post_text else 0,
            'has_image': self.post_image_path is not None and (self.post_image_path.exists() if self.post_image_path else False),
            'image_path': str(self.post_image_path) if self.post_image_path else None,
            'text_preview': self.post_text[:100] + '...' if self.post_text and len(self.post_text) > 100 else (self.post_text or ''),
            'use_template': self.use_template,
            'template_name': template[1] if template else None,
            'template_id': template[0] if template else None
        }
