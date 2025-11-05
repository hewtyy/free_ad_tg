"""
Планировщик для автоматической публикации постов
"""
import asyncio
import random
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from config import MIN_DELAY, MAX_DELAY
from db import db
from handlers.post import PostHandler

# Настройка логирования
logger = logging.getLogger(__name__)


class PostScheduler:
    """Класс для управления расписанием публикации постов"""
    
    def __init__(self):
        # Настройка планировщика с правильными параметрами
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 1
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'  # Используем UTC для избежания проблем с часовыми поясами
        )
        self.post_handler = PostHandler()
        self.is_running = False
        
        # Статус публикации
        self.publication_status = {
            'is_publishing': False,
            'current_step': None,
            'total_groups': 0,
            'completed_groups': 0,
            'current_group': None,
            'start_time': None,
            'last_update': None,
            'errors': []
        }
    
    async def start(self):
        """Запуск планировщика"""
        try:
            # Инициализация базы данных
            await db.init_db()
            
            # Получаем интервал из базы данных
            interval_minutes = await db.get_post_interval_minutes()
            
            # Добавляем задачу в планировщик
            self.scheduler.add_job(
                self._scheduled_post,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id='post_job',
                replace_existing=True
            )
            
            # Запускаем планировщик
            if not self.scheduler.running:
                self.scheduler.start()
                print("Планировщик запущен")
            else:
                print("Планировщик уже запущен")
            
            self.is_running = True
            
            # Форматируем интервал для вывода
            if interval_minutes < 60:
                print(f"Планировщик запущен с интервалом {interval_minutes} минут")
            else:
                hours = interval_minutes // 60
                minutes = interval_minutes % 60
                if minutes > 0:
                    print(f"Планировщик запущен с интервалом {hours}ч {minutes}м")
                else:
                    print(f"Планировщик запущен с интервалом {hours} часов")
                    
        except Exception as e:
            print(f"Ошибка запуска планировщика: {e}")
            self.is_running = False
    
    async def stop(self):
        """Остановка планировщика"""
        try:
            # Удаляем задачу из планировщика
            if self.scheduler.get_job('post_job'):
                self.scheduler.remove_job('post_job')
                print("Задача удалена из планировщика")
            
            # Останавливаем планировщик
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                print("Планировщик остановлен")
            
            self.is_running = False
            print("Планировщик полностью остановлен")
        except Exception as e:
            print(f"Ошибка при остановке планировщика: {e}")
            self.is_running = False
    
    async def update_interval_minutes(self, minutes: int):
        """
        Обновление интервала публикации в минутах
        
        Args:
            minutes: Новый интервал в минутах
        """
        # Сохраняем в базу данных
        await db.set_post_interval_minutes(minutes)
        
        # Обновляем задачу в планировщике
        if self.scheduler.running:
            self.scheduler.remove_job('post_job')
            self.scheduler.add_job(
                self._scheduled_post,
                trigger=IntervalTrigger(minutes=minutes),
                id='post_job',
                replace_existing=True
            )
        
        # Форматируем интервал для вывода
        if minutes < 60:
            print(f"Интервал публикации обновлен на {minutes} минут")
        else:
            hours = minutes // 60
            mins = minutes % 60
            if mins > 0:
                print(f"Интервал публикации обновлен на {hours}ч {mins}м")
            else:
                print(f"Интервал публикации обновлен на {hours} часов")
    
    async def update_interval(self, hours: int):
        """
        Обновление интервала публикации в часах (для обратной совместимости)
        
        Args:
            hours: Новый интервал в часах
        """
        minutes = hours * 60
        await self.update_interval_minutes(minutes)
    
    async def post_now(self):
        """
        Немедленная публикация постов во все группы
        """
        print("Запуск немедленной публикации...")
        await self._scheduled_post()
    
    async def _scheduled_post(self):
        """
        Выполнение запланированной публикации с задержками между группами
        """
        # Инициализируем статус публикации
        self.publication_status.update({
            'is_publishing': True,
            'current_step': 'Инициализация',
            'total_groups': 0,
            'completed_groups': 0,
            'current_group': None,
            'start_time': datetime.now(),
            'last_update': datetime.now(),
            'errors': []
        })
        
        try:
            logger.info("🚀 Начинаем процесс публикации постов")
            self._update_status("Получение списка групп...")
            
            # Получаем список всех групп
            groups = await db.get_all_groups()
            
            if not groups:
                logger.warning("❌ Нет групп для публикации")
                self._update_status("Нет групп для публикации")
                return
            
            # Обновляем статус
            self.publication_status.update({
                'total_groups': len(groups),
                'current_step': f'Публикация в {len(groups)} групп'
            })
            
            logger.info(f"📊 Начинаем публикацию в {len(groups)} групп...")
            self._update_status(f"Публикация в {len(groups)} групп")
            
            for i, group in enumerate(groups):
                try:
                    # Обрабатываем разные форматы данных
                    if len(group) >= 5:
                        chat_id, title, username, added_at, last_posted = group
                    elif len(group) >= 4:
                        chat_id, title, added_at, last_posted = group
                        username = None
                    else:
                        chat_id, title = group[0], group[1] if len(group) > 1 else "Unknown"
                        username = None
                    
                    # Обновляем текущую группу
                    group_name = title or username or chat_id
                    self.publication_status.update({
                        'current_group': group_name,
                        'current_step': f'Публикация в группу {i+1}/{len(groups)}: {group_name}'
                    })
                    
                    logger.info(f"📤 [{i+1}/{len(groups)}] Публикация в группу: {group_name}")
                    self._update_status(f"Публикация в группу {i+1}/{len(groups)}: {group_name}")
                    
                    # Публикуем пост, используя username если доступен
                    target = username if username else chat_id
                    success = await self.post_handler.send_post_to_group(target)
                    
                    if success:
                        # Обновляем время последней публикации
                        await db.update_last_posted(chat_id)
                        logger.info(f"✅ [{i+1}/{len(groups)}] Пост отправлен в группу {group_name}")
                        self._update_status(f"✅ Группа {i+1}/{len(groups)}: {group_name} - успешно")
                    else:
                        error_msg = f"Ошибка отправки в группу {group_name}"
                        logger.error(f"❌ [{i+1}/{len(groups)}] {error_msg}")
                        self.publication_status['errors'].append({
                            'group': group_name,
                            'error': error_msg,
                            'time': datetime.now()
                        })
                        self._update_status(f"❌ Группа {i+1}/{len(groups)}: {group_name} - ошибка")
                    
                    # Обновляем счетчик завершенных групп
                    self.publication_status['completed_groups'] = i + 1
                    
                    # Добавляем случайную задержку между отправками (кроме последней)
                    if i < len(groups) - 1:
                        delay = random.randint(MIN_DELAY, MAX_DELAY)
                        logger.info(f"⏳ Ожидание {delay} секунд перед следующей отправкой...")
                        self._update_status(f"Ожидание {delay} секунд...")
                        await asyncio.sleep(delay)
                
                except Exception as e:
                    error_msg = f"Ошибка при публикации в группу {chat_id}: {e}"
                    logger.error(f"❌ {error_msg}")
                    self.publication_status['errors'].append({
                        'group': chat_id,
                        'error': error_msg,
                        'time': datetime.now()
                    })
                    continue
            
            # Завершаем публикацию
            total_errors = len(self.publication_status['errors'])
            if total_errors == 0:
                logger.info("🎉 Публикация завершена успешно!")
                self._update_status("Публикация завершена успешно!")
            else:
                logger.warning(f"⚠️ Публикация завершена с {total_errors} ошибками")
                self._update_status(f"Публикация завершена с {total_errors} ошибками")
            
        except Exception as e:
            error_msg = f"Критическая ошибка при публикации: {e}"
            logger.error(f"💥 {error_msg}")
            self.publication_status['errors'].append({
                'group': 'SYSTEM',
                'error': error_msg,
                'time': datetime.now()
            })
            self._update_status(f"Критическая ошибка: {e}")
        finally:
            # Сбрасываем статус публикации только после полного завершения
            # Не сбрасываем сразу, чтобы показать финальный статус
            self.publication_status.update({
                'is_publishing': False,
                'current_step': 'Завершено',
                'last_update': datetime.now()
            })
    
    def _update_status(self, step: str):
        """Обновление статуса публикации"""
        self.publication_status['current_step'] = step
        self.publication_status['last_update'] = datetime.now()
        logger.info(f"📊 Статус: {step}")
    
    def get_next_run_time(self) -> datetime:
        """
        Получение времени следующего запуска
        
        Returns:
            Время следующего запуска или None
        """
        try:
            job = self.scheduler.get_job('post_job')
            if job and job.next_run_time:
                # Конвертируем UTC время в локальное время
                return job.next_run_time
            return None
        except Exception as e:
            print(f"Ошибка получения времени следующего запуска: {e}")
            return None
    
    def get_status(self) -> dict:
        """
        Получение статуса планировщика
        
        Returns:
            Словарь со статусом
        """
        job = self.scheduler.get_job('post_job')
        # Проверяем реальное состояние планировщика
        scheduler_running = self.scheduler.running if hasattr(self.scheduler, 'running') else False
        job_exists = job is not None
        
        # Планировщик считается запущенным, если он работает И есть задача
        is_running = scheduler_running and job_exists
        
        return {
            'is_running': is_running,
            'next_run': job.next_run_time if job else None,
            'job_exists': job_exists,
            'scheduler_running': scheduler_running
        }
    
    def reset_publication_status(self):
        """Сброс статуса публикации"""
        self.publication_status.update({
            'is_publishing': False,
            'current_step': None,
            'total_groups': 0,
            'completed_groups': 0,
            'current_group': None,
            'start_time': None,
            'last_update': None,
            'errors': []
        })
    
    def get_publication_status(self) -> dict:
        """
        Получение детального статуса публикации
        
        Returns:
            Словарь со статусом публикации
        """
        status = self.publication_status.copy()
        
        # Добавляем вычисляемые поля
        if status['is_publishing'] and status['total_groups'] > 0:
            progress_percent = (status['completed_groups'] / status['total_groups']) * 100
            status['progress_percent'] = round(progress_percent, 1)
        else:
            # Показываем прогресс даже после завершения
            if status['total_groups'] > 0:
                progress_percent = (status['completed_groups'] / status['total_groups']) * 100
                status['progress_percent'] = round(progress_percent, 1)
            else:
                status['progress_percent'] = 0
        
        # Форматируем время
        if status['start_time']:
            status['start_time_str'] = status['start_time'].strftime('%H:%M:%S')
        else:
            status['start_time_str'] = None
            
        if status['last_update']:
            status['last_update_str'] = status['last_update'].strftime('%H:%M:%S')
        else:
            status['last_update_str'] = None
        
        return status
