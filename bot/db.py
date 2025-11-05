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
            
            # Таблица шаблонов постов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS post_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    is_active INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица расписаний публикаций
            await db.execute('''
                CREATE TABLE IF NOT EXISTS publication_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_type TEXT NOT NULL,
                    schedule_data TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица истории публикаций
            await db.execute('''
                CREATE TABLE IF NOT EXISTS publication_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    chat_title TEXT,
                    chat_username TEXT,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    retry_count INTEGER DEFAULT 0
                )
            ''')
            
            # Индексы для быстрого поиска
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_publication_history_chat_id 
                ON publication_history(chat_id)
            ''')
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_publication_history_status 
                ON publication_history(status)
            ''')
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_publication_history_published_at 
                ON publication_history(published_at)
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
            
            # Миграция: добавляем поле is_disabled для черного списка
            try:
                await db.execute('ALTER TABLE groups ADD COLUMN is_disabled INTEGER DEFAULT 0')
            except Exception:
                # Поле уже существует
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
    
    async def get_all_groups(self) -> List[Tuple[str, str, str, str, str, int]]:
        """
        Получение списка всех групп (включая отключенные)
        
        Returns:
            Список кортежей (chat_id, title, username, added_at, last_posted, is_disabled)
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT chat_id, title, username, added_at, last_posted, COALESCE(is_disabled, 0) as is_disabled FROM groups ORDER BY added_at'
                )
                return await cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении списка групп: {e}")
            return []
    
    async def get_active_groups(self) -> List[Tuple[str, str, str, str, str]]:
        """
        Получение списка только активных групп (не в черном списке)
        
        Returns:
            Список кортежей (chat_id, title, username, added_at, last_posted)
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT chat_id, title, username, added_at, last_posted FROM groups WHERE COALESCE(is_disabled, 0) = 0 ORDER BY added_at'
                )
                return await cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении списка активных групп: {e}")
            return []
    
    async def set_group_disabled(self, chat_id: str, is_disabled: bool) -> bool:
        """
        Добавление/удаление группы из черного списка
        
        Args:
            chat_id: ID чата
            is_disabled: True для добавления в черный список, False для удаления
            
        Returns:
            True если успешно обновлено
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE groups SET is_disabled = ? WHERE chat_id = ?',
                    (1 if is_disabled else 0, chat_id)
                )
                await db.commit()
                
                # Проверяем, что группа была обновлена
                cursor = await db.execute(
                    'SELECT chat_id FROM groups WHERE chat_id = ?',
                    (chat_id,)
                )
                return (await cursor.fetchone()) is not None
        except Exception as e:
            print(f"Ошибка при изменении статуса группы: {e}")
            return False
    
    async def is_group_disabled(self, chat_id: str) -> bool:
        """
        Проверка, находится ли группа в черном списке
        
        Args:
            chat_id: ID чата
            
        Returns:
            True если группа в черном списке, False если активна
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT COALESCE(is_disabled, 0) FROM groups WHERE chat_id = ?',
                    (chat_id,)
                )
                result = await cursor.fetchone()
                return bool(result[0]) if result else False
        except Exception as e:
            print(f"Ошибка при проверке статуса группы: {e}")
            return False
    
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
    
    async def add_publication_history(
        self, 
        chat_id: str, 
        chat_title: str = None, 
        chat_username: str = None,
        status: str = 'success',
        error_message: str = None,
        retry_count: int = 0
    ) -> bool:
        """
        Добавление записи в историю публикаций
        
        Args:
            chat_id: ID чата
            chat_title: Название чата
            chat_username: Username чата
            status: Статус публикации ('success' или 'error')
            error_message: Сообщение об ошибке (если есть)
            retry_count: Количество попыток
            
        Returns:
            True если успешно добавлено
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO publication_history 
                    (chat_id, chat_title, chat_username, status, error_message, retry_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (chat_id, chat_title, chat_username, status, error_message, retry_count))
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при добавлении в историю публикаций: {e}")
            return False
    
    async def get_publication_history(
        self,
        limit: int = 100,
        offset: int = 0,
        chat_id: str = None,
        status: str = None,
        start_date: str = None,
        end_date: str = None,
        search: str = None
    ) -> List[Tuple]:
        """
        Получение истории публикаций с фильтрами
        
        Args:
            limit: Максимальное количество записей
            offset: Смещение для пагинации
            chat_id: Фильтр по ID чата
            status: Фильтр по статусу ('success' или 'error')
            start_date: Начальная дата (формат: 'YYYY-MM-DD HH:MM:SS')
            end_date: Конечная дата (формат: 'YYYY-MM-DD HH:MM:SS')
            search: Поиск по названию чата или username
            
        Returns:
            Список кортежей (id, chat_id, chat_title, chat_username, status, error_message, published_at, retry_count)
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = 'SELECT id, chat_id, chat_title, chat_username, status, error_message, published_at, retry_count FROM publication_history WHERE 1=1'
                params = []
                
                if chat_id:
                    query += ' AND chat_id = ?'
                    params.append(chat_id)
                
                if status:
                    query += ' AND status = ?'
                    params.append(status)
                
                if start_date:
                    query += ' AND published_at >= ?'
                    params.append(start_date)
                
                if end_date:
                    query += ' AND published_at <= ?'
                    params.append(end_date)
                
                if search:
                    query += ' AND (chat_title LIKE ? OR chat_username LIKE ?)'
                    search_pattern = f'%{search}%'
                    params.extend([search_pattern, search_pattern])
                
                query += ' ORDER BY published_at DESC LIMIT ? OFFSET ?'
                params.extend([limit, offset])
                
                cursor = await db.execute(query, params)
                return await cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении истории публикаций: {e}")
            return []
    
    async def get_publication_statistics(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> dict:
        """
        Получение статистики публикаций
        
        Args:
            start_date: Начальная дата (формат: 'YYYY-MM-DD HH:MM:SS')
            end_date: Конечная дата (формат: 'YYYY-MM-DD HH:MM:SS')
            
        Returns:
            Словарь со статистикой
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                date_filter = ''
                params = []
                
                if start_date:
                    date_filter += ' AND published_at >= ?'
                    params.append(start_date)
                
                if end_date:
                    date_filter += ' AND published_at <= ?'
                    params.append(end_date)
                
                # Общее количество публикаций
                cursor = await db.execute(
                    f'SELECT COUNT(*) FROM publication_history WHERE 1=1 {date_filter}',
                    params
                )
                total = (await cursor.fetchone())[0]
                
                # Успешные публикации
                cursor = await db.execute(
                    f'SELECT COUNT(*) FROM publication_history WHERE status = "success" {date_filter}',
                    params
                )
                successful = (await cursor.fetchone())[0]
                
                # Неудачные публикации
                cursor = await db.execute(
                    f'SELECT COUNT(*) FROM publication_history WHERE status = "error" {date_filter}',
                    params
                )
                failed = (await cursor.fetchone())[0]
                
                # Топ групп по публикациям
                cursor = await db.execute(f'''
                    SELECT chat_id, chat_title, COUNT(*) as count 
                    FROM publication_history 
                    WHERE 1=1 {date_filter}
                    GROUP BY chat_id 
                    ORDER BY count DESC 
                    LIMIT 10
                ''', params)
                top_groups = await cursor.fetchall()
                
                # Статистика по дням для графика активности
                cursor = await db.execute(f'''
                    SELECT DATE(published_at) as date, 
                           COUNT(*) as total,
                           SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                           SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed
                    FROM publication_history 
                    WHERE 1=1 {date_filter}
                    GROUP BY DATE(published_at)
                    ORDER BY date DESC
                    LIMIT 30
                ''', params)
                daily_stats = await cursor.fetchall()
                
                # Статистика по часам для графика активности по времени суток
                cursor = await db.execute(f'''
                    SELECT CAST(strftime('%H', published_at) AS INTEGER) as hour,
                           COUNT(*) as count
                    FROM publication_history 
                    WHERE 1=1 {date_filter}
                    GROUP BY hour
                    ORDER BY hour
                ''', params)
                hourly_stats = await cursor.fetchall()
                
                return {
                    'total': total,
                    'successful': successful,
                    'failed': failed,
                    'success_rate': round((successful / total * 100) if total > 0 else 0, 2),
                    'top_groups': [{'chat_id': g[0], 'title': g[1], 'count': g[2]} for g in top_groups],
                    'daily_stats': [{'date': d[0], 'total': d[1], 'successful': d[2], 'failed': d[3]} for d in daily_stats],
                    'hourly_stats': [{'hour': h[0], 'count': h[1]} for h in hourly_stats]
                }
        except Exception as e:
            print(f"Ошибка при получении статистики: {e}")
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0,
                'top_groups': [],
                'daily_stats': [],
                'hourly_stats': []
            }
    
    async def clear_publication_history(self, days: int = None) -> bool:
        """
        Очистка истории публикаций
        
        Args:
            days: Оставить записи только за последние N дней (если None - удалить все)
            
        Returns:
            True если успешно очищено
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if days:
                    await db.execute(
                        'DELETE FROM publication_history WHERE published_at < datetime("now", ?)',
                        (f'-{days} days',)
                    )
                else:
                    await db.execute('DELETE FROM publication_history')
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при очистке истории: {e}")
            return False
    
    async def add_post_template(self, name: str, content: str) -> int:
        """
        Добавление шаблона поста
        
        Args:
            name: Название шаблона
            content: Содержимое шаблона
            
        Returns:
            ID созданного шаблона
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    INSERT INTO post_templates (name, content)
                    VALUES (?, ?)
                ''', (name, content))
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Ошибка при добавлении шаблона: {e}")
            return None
    
    async def get_all_templates(self) -> List[Tuple]:
        """
        Получение списка всех шаблонов
        
        Returns:
            Список кортежей (id, name, content, is_active, created_at, updated_at)
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT id, name, content, is_active, created_at, updated_at
                    FROM post_templates
                    ORDER BY is_active DESC, created_at DESC
                ''')
                return await cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении шаблонов: {e}")
            return []
    
    async def get_active_template(self) -> Optional[Tuple]:
        """
        Получение активного шаблона
        
        Returns:
            Кортеж (id, name, content, is_active, created_at, updated_at) или None
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT id, name, content, is_active, created_at, updated_at
                    FROM post_templates
                    WHERE is_active = 1
                    LIMIT 1
                ''')
                return await cursor.fetchone()
        except Exception as e:
            print(f"Ошибка при получении активного шаблона: {e}")
            return None
    
    async def update_template(self, template_id: int, name: str = None, content: str = None) -> bool:
        """
        Обновление шаблона
        
        Args:
            template_id: ID шаблона
            name: Новое название (опционально)
            content: Новое содержимое (опционально)
            
        Returns:
            True если успешно обновлено
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                updates = []
                params = []
                
                if name is not None:
                    updates.append('name = ?')
                    params.append(name)
                
                if content is not None:
                    updates.append('content = ?')
                    params.append(content)
                
                if not updates:
                    return False
                
                updates.append('updated_at = CURRENT_TIMESTAMP')
                params.append(template_id)
                
                await db.execute(f'''
                    UPDATE post_templates
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при обновлении шаблона: {e}")
            return False
    
    async def set_active_template(self, template_id: int) -> bool:
        """
        Установка активного шаблона (деактивирует остальные)
        
        Args:
            template_id: ID шаблона для активации
            
        Returns:
            True если успешно установлено
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Деактивируем все шаблоны
                await db.execute('UPDATE post_templates SET is_active = 0')
                # Активируем выбранный
                await db.execute('UPDATE post_templates SET is_active = 1 WHERE id = ?', (template_id,))
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при установке активного шаблона: {e}")
            return False
    
    async def delete_template(self, template_id: int) -> bool:
        """
        Удаление шаблона
        
        Args:
            template_id: ID шаблона
            
        Returns:
            True если успешно удалено
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('DELETE FROM post_templates WHERE id = ?', (template_id,))
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при удалении шаблона: {e}")
            return False
    
    async def add_schedule(self, schedule_type: str, schedule_data: dict) -> int:
        """
        Добавление расписания публикации
        
        Args:
            schedule_type: Тип расписания (interval, time, days, hours)
            schedule_data: Словарь с данными расписания (сериализуется в JSON)
            
        Returns:
            ID созданного расписания
        """
        try:
            import json
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    INSERT INTO publication_schedules (schedule_type, schedule_data)
                    VALUES (?, ?)
                ''', (schedule_type, json.dumps(schedule_data)))
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Ошибка при добавлении расписания: {e}")
            return None
    
    async def get_all_schedules(self) -> List[Tuple]:
        """
        Получение списка всех расписаний
        
        Returns:
            Список кортежей (id, schedule_type, schedule_data, is_active, created_at, updated_at)
        """
        try:
            import json
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT id, schedule_type, schedule_data, is_active, created_at, updated_at
                    FROM publication_schedules
                    ORDER BY is_active DESC, created_at DESC
                ''')
                results = await cursor.fetchall()
                # Парсим JSON для каждого результата
                parsed_results = []
                for row in results:
                    id, schedule_type, schedule_data_json, is_active, created_at, updated_at = row
                    try:
                        schedule_data = json.loads(schedule_data_json)
                    except:
                        schedule_data = {}
                    parsed_results.append((id, schedule_type, schedule_data, is_active, created_at, updated_at))
                return parsed_results
        except Exception as e:
            print(f"Ошибка при получении расписаний: {e}")
            return []
    
    async def get_active_schedule(self) -> Optional[Tuple]:
        """
        Получение активного расписания
        
        Returns:
            Кортеж (id, schedule_type, schedule_data, is_active, created_at, updated_at) или None
        """
        try:
            import json
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT id, schedule_type, schedule_data, is_active, created_at, updated_at
                    FROM publication_schedules
                    WHERE is_active = 1
                    LIMIT 1
                ''')
                result = await cursor.fetchone()
                if result:
                    id, schedule_type, schedule_data_json, is_active, created_at, updated_at = result
                    try:
                        schedule_data = json.loads(schedule_data_json)
                    except:
                        schedule_data = {}
                    return (id, schedule_type, schedule_data, is_active, created_at, updated_at)
                return None
        except Exception as e:
            print(f"Ошибка при получении активного расписания: {e}")
            return None
    
    async def update_schedule(self, schedule_id: int, schedule_type: str = None, schedule_data: dict = None) -> bool:
        """
        Обновление расписания
        
        Args:
            schedule_id: ID расписания
            schedule_type: Новый тип расписания (опционально)
            schedule_data: Новые данные расписания (опционально)
            
        Returns:
            True если успешно обновлено
        """
        try:
            import json
            async with aiosqlite.connect(self.db_path) as db:
                updates = []
                params = []
                
                if schedule_type is not None:
                    updates.append('schedule_type = ?')
                    params.append(schedule_type)
                
                if schedule_data is not None:
                    updates.append('schedule_data = ?')
                    params.append(json.dumps(schedule_data))
                
                if not updates:
                    return False
                
                updates.append('updated_at = CURRENT_TIMESTAMP')
                params.append(schedule_id)
                
                await db.execute(f'''
                    UPDATE publication_schedules
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при обновлении расписания: {e}")
            return False
    
    async def set_active_schedule(self, schedule_id: int) -> bool:
        """
        Установка активного расписания (деактивирует остальные)
        
        Args:
            schedule_id: ID расписания для активации
            
        Returns:
            True если успешно установлено
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Деактивируем все расписания
                await db.execute('UPDATE publication_schedules SET is_active = 0')
                # Активируем выбранное
                await db.execute('UPDATE publication_schedules SET is_active = 1 WHERE id = ?', (schedule_id,))
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при установке активного расписания: {e}")
            return False
    
    async def delete_schedule(self, schedule_id: int) -> bool:
        """
        Удаление расписания
        
        Args:
            schedule_id: ID расписания
            
        Returns:
            True если успешно удалено
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('DELETE FROM publication_schedules WHERE id = ?', (schedule_id,))
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при удалении расписания: {e}")
            return False


# Глобальный экземпляр базы данных
db = Database()
