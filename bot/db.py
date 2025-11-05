"""
Модуль для работы с базой данных SQLite
"""
import aiosqlite
import asyncio
from datetime import datetime
from typing import List, Optional, Tuple
from config import DATABASE_FILE


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self):
        self.db_path = DATABASE_FILE
    
    async def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица групп
            await db.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT UNIQUE NOT NULL,
                    title TEXT,
                    username TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_posted TIMESTAMP
                )
            ''')
            
            # Таблица настроек
            await db.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            # Вставляем настройки по умолчанию
            await db.execute('''
                INSERT OR IGNORE INTO settings (key, value) 
                VALUES ('post_interval_minutes', '1440')
            ''')
            
            # Миграция: добавляем поле username если его нет
            try:
                await db.execute('ALTER TABLE groups ADD COLUMN username TEXT')
            except Exception:
                # Поле уже существует
                pass
            
            # Миграция: обновляем старый формат интервала на новый (минуты)
            try:
                # Проверяем, есть ли старый формат
                cursor = await db.execute('SELECT value FROM settings WHERE key = "post_interval"')
                old_interval = await cursor.fetchone()
                if old_interval:
                    # Конвертируем часы в минуты
                    hours = int(old_interval[0])
                    minutes = hours * 60
                    await db.execute(
                        'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                        ('post_interval_minutes', str(minutes))
                    )
                    # Удаляем старый ключ
                    await db.execute('DELETE FROM settings WHERE key = "post_interval"')
            except Exception:
                # Миграция не нужна или уже выполнена
                pass
            
            await db.commit()
    
    async def add_group(self, chat_id: str, title: str = None, username: str = None) -> bool:
        """
        Добавление группы в базу данных
        
        Args:
            chat_id: ID чата
            title: Название группы
            username: Username чата
            
        Returns:
            True если группа добавлена, False если уже существует
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR IGNORE INTO groups (chat_id, title, username) VALUES (?, ?, ?)',
                    (chat_id, title, username)
                )
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при добавлении группы: {e}")
            return False
    
    async def remove_group(self, chat_id: str) -> bool:
        """
        Удаление группы из базы данных
        
        Args:
            chat_id: ID чата
            
        Returns:
            True если группа удалена, False если не найдена
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'DELETE FROM groups WHERE chat_id = ?',
                    (chat_id,)
                )
                await db.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Ошибка при удалении группы: {e}")
            return False
    
    async def get_all_groups(self) -> List[Tuple[str, str, str, str, str]]:
        """
        Получение списка всех групп
        
        Returns:
            Список кортежей (chat_id, title, username, added_at, last_posted)
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT chat_id, title, username, added_at, last_posted FROM groups ORDER BY added_at'
                )
                return await cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении списка групп: {e}")
            return []
    
    async def update_last_posted(self, chat_id: str):
        """
        Обновление времени последней публикации для группы
        
        Args:
            chat_id: ID чата
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE groups SET last_posted = CURRENT_TIMESTAMP WHERE chat_id = ?',
                    (chat_id,)
                )
                await db.commit()
        except Exception as e:
            print(f"Ошибка при обновлении времени публикации: {e}")
    
    async def get_post_interval_minutes(self) -> int:
        """
        Получение интервала публикации в минутах
        
        Returns:
            Интервал в минутах
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT value FROM settings WHERE key = "post_interval_minutes"'
                )
                result = await cursor.fetchone()
                return int(result[0]) if result else 1440  # 24 часа по умолчанию
        except Exception as e:
            print(f"Ошибка при получении интервала: {e}")
            return 1440
    
    async def get_post_interval_hours(self) -> int:
        """
        Получение интервала публикации в часах (для обратной совместимости)
        
        Returns:
            Интервал в часах
        """
        minutes = await self.get_post_interval_minutes()
        return minutes // 60
    
    async def set_post_interval_minutes(self, minutes: int) -> bool:
        """
        Установка интервала публикации в минутах
        
        Args:
            minutes: Интервал в минутах
            
        Returns:
            True если успешно установлено
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                    ('post_interval_minutes', str(minutes))
                )
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при установке интервала: {e}")
            return False
    
    async def set_post_interval(self, hours: int) -> bool:
        """
        Установка интервала публикации в часах (для обратной совместимости)
        
        Args:
            hours: Интервал в часах
            
        Returns:
            True если успешно установлено
        """
        minutes = hours * 60
        return await self.set_post_interval_minutes(minutes)


# Глобальный экземпляр базы данных
db = Database()
