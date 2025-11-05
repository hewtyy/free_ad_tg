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
from config import MIN_DELAY, MAX_DELAY, PUBLICATION_RETRY_ATTEMPTS, PUBLICATION_RETRY_DELAY
from db import db
from handlers.post import PostHandler

# Используем pytz для работы с часовыми поясами (уже установлен как зависимость APScheduler)
import pytz

# Московский часовой пояс
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

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
    
    def reload_post(self):
        """Перезагрузка содержимого поста из файлов"""
        logger.info("Перезагрузка поста в планировщике...")
        if self.post_handler:
            self.post_handler._load_post_content()
            logger.info("Пост успешно перезагружен в планировщике")
        else:
            logger.warning("post_handler не инициализирован в планировщике")
    
    async def start(self):
        """Запуск планировщика"""
        try:
            # Инициализация базы данных
            await db.init_db()
            
            # Получаем интервал из базы данных
            interval_minutes = await db.get_post_interval_minutes()
            
            # Устанавливаем флаг запуска ПЕРЕД добавлением задачи
            self.is_running = True
            logger.info(f"✅ Флаг is_running установлен в True")
            
            # Если планировщик не запущен, запускаем его
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("Планировщик запущен")
                print("Планировщик запущен")
            else:
                logger.info("Планировщик уже запущен")
                print("Планировщик уже запущен")
            
            # Добавляем задачу в планировщик
            self.scheduler.add_job(
                self._scheduled_post,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id='post_job',
                replace_existing=True
            )
            logger.info(f"✅ Задача 'post_job' добавлена в планировщик")
            
            # Форматируем интервал для вывода
            if interval_minutes < 60:
                logger.info(f"Планировщик запущен с интервалом {interval_minutes} минут")
                print(f"Планировщик запущен с интервалом {interval_minutes} минут")
            else:
                hours = interval_minutes // 60
                minutes = interval_minutes % 60
                if minutes > 0:
                    logger.info(f"Планировщик запущен с интервалом {hours}ч {minutes}м")
                    print(f"Планировщик запущен с интервалом {hours}ч {minutes}м")
                else:
                    logger.info(f"Планировщик запущен с интервалом {hours} часов")
                    print(f"Планировщик запущен с интервалом {hours} часов")
                    
        except Exception as e:
            logger.error(f"Ошибка запуска планировщика: {e}")
            print(f"Ошибка запуска планировщика: {e}")
            self.is_running = False
    
    async def stop(self):
        """Остановка планировщика"""
        try:
            # Устанавливаем флаг остановки ПЕРВЫМ ДЕЛОМ
            self.is_running = False
            logger.info("🛑 Флаг is_running установлен в False")
            print("🛑 Флаг is_running установлен в False")
            
            # Удаляем задачу из планировщика
            try:
                job = self.scheduler.get_job('post_job')
                if job:
                    self.scheduler.remove_job('post_job')
                    logger.info("✅ Задача 'post_job' удалена из планировщика")
                    print("✅ Задача 'post_job' удалена из планировщика")
                else:
                    logger.warning("⚠️ Задача 'post_job' не найдена в планировщике")
                    print("⚠️ Задача 'post_job' не найдена в планировщике")
            except Exception as e:
                logger.error(f"❌ Ошибка при удалении задачи: {e}")
                print(f"❌ Ошибка при удалении задачи: {e}")
            
            # Останавливаем планировщик
            try:
                if self.scheduler.running:
                    # Используем shutdown с wait=False для немедленной остановки
                    self.scheduler.shutdown(wait=False)
                    logger.info("✅ Планировщик остановлен")
                    print("✅ Планировщик остановлен")
                else:
                    logger.info("ℹ️ Планировщик уже был остановлен")
                    print("ℹ️ Планировщик уже был остановлен")
            except Exception as e:
                logger.error(f"❌ Ошибка при остановке планировщика: {e}")
                print(f"❌ Ошибка при остановке планировщика: {e}")
            
            # Проверяем, что планировщик действительно остановлен
            if not self.scheduler.running:
                logger.info("✅ Планировщик полностью остановлен")
                print("✅ Планировщик полностью остановлен")
            else:
                logger.warning("⚠️ Планировщик все еще работает!")
                print("⚠️ Планировщик все еще работает!")
                
        except Exception as e:
            logger.error(f"💥 Критическая ошибка при остановке планировщика: {e}")
            print(f"💥 Критическая ошибка при остановке планировщика: {e}")
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
        logger.info("🚀 Запуск немедленной публикации...")
        print("Запуск немедленной публикации...")
        
        # Временно устанавливаем флаг для немедленной публикации
        # Сохраняем исходное состояние
        original_is_running = self.is_running
        self.is_running = True
        
        try:
            await self._scheduled_post()
        finally:
            # Восстанавливаем исходное состояние только если планировщик не был запущен
            if not original_is_running and not self.scheduler.running:
                self.is_running = False
    
    async def _scheduled_post(self):
        """
        Выполнение запланированной публикации с задержками между группами
        """
        # Определяем, является ли это запланированной задачей или немедленной публикацией
        # Для этого проверяем, есть ли задача в планировщике
        job = self.scheduler.get_job('post_job')
        is_scheduled_job = job is not None
        
        logger.info(f"📋 Запуск публикации: is_scheduled_job={is_scheduled_job}, is_running={self.is_running}, scheduler.running={self.scheduler.running if hasattr(self.scheduler, 'running') else 'N/A'}")
        
        # Для запланированных задач проверяем флаг запуска
        # Для немедленной публикации (post_now) флаг будет установлен временно
        # Но если планировщик работает и есть задача, значит это запланированная публикация
        if is_scheduled_job:
            # Для запланированных задач проверяем флаг is_running
            if not self.is_running:
                logger.warning("⚠️ Планировщик остановлен, публикация отменена")
                return
        # Для немедленной публикации (post_now) проверка не нужна, т.к. флаг уже установлен
        
        # Инициализируем статус публикации
        # Получаем текущее время в UTC и конвертируем в московское
        utc_now = datetime.now(pytz.utc)
        moscow_now = utc_now.astimezone(MOSCOW_TZ)
        
        self.publication_status.update({
            'is_publishing': True,
            'current_step': 'Инициализация',
            'total_groups': 0,
            'completed_groups': 0,
            'current_group': None,
            'start_time': moscow_now,
            'last_update': moscow_now,
            'errors': []
        })
        
        try:
            logger.info("🚀 Начинаем процесс публикации постов")
            self._update_status("Получение списка групп...")
            
            # Проверяем статус перед началом публикации только для запланированных задач
            if is_scheduled_job and not self.is_running:
                logger.warning("⚠️ Планировщик остановлен перед началом публикации")
                return
            
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
                # Проверяем статус перед каждой публикацией только для запланированных задач
                if is_scheduled_job and not self.is_running:
                    logger.warning(f"⚠️ Планировщик остановлен во время публикации. Остановлено на группе {i+1}/{len(groups)}")
                    self._update_status(f"Публикация остановлена на группе {i+1}/{len(groups)}")
                    break
                
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
                    
                    # Пытаемся отправить пост с повторными попытками
                    success = await self._send_post_with_retry(target, group_name, i+1, len(groups))
                    
                    if success:
                        # Обновляем время последней публикации
                        await db.update_last_posted(chat_id)
                        logger.info(f"✅ [{i+1}/{len(groups)}] Пост отправлен в группу {group_name}")
                        self._update_status(f"✅ Группа {i+1}/{len(groups)}: {group_name} - успешно")
                    else:
                        error_msg = f"Ошибка отправки в группу {group_name} после {PUBLICATION_RETRY_ATTEMPTS} попыток"
                        logger.error(f"❌ [{i+1}/{len(groups)}] {error_msg}")
                        self.publication_status['errors'].append({
                            'group': group_name,
                            'error': error_msg,
                            'time': datetime.now(pytz.utc).astimezone(MOSCOW_TZ)
                        })
                        self._update_status(f"❌ Группа {i+1}/{len(groups)}: {group_name} - ошибка")
                    
                    # Обновляем счетчик завершенных групп
                    self.publication_status['completed_groups'] = i + 1
                    
                    # Добавляем случайную задержку между отправками (кроме последней)
                    if i < len(groups) - 1:
                        delay = random.randint(MIN_DELAY, MAX_DELAY)
                        logger.info(f"⏳ Ожидание {delay} секунд перед следующей отправкой...")
                        self._update_status(f"Ожидание {delay} секунд...")
                        
                        # Проверяем статус во время задержки только для запланированных задач
                        if is_scheduled_job:
                            for _ in range(delay):
                                if not self.is_running:
                                    logger.warning("⚠️ Планировщик остановлен во время задержки")
                                    break
                                await asyncio.sleep(1)
                            
                            # Если планировщик остановлен, прекращаем публикацию
                            if not self.is_running:
                                break
                        else:
                            # Для немедленной публикации просто ждем
                            await asyncio.sleep(delay)
                
                except Exception as e:
                    error_msg = f"Ошибка при публикации в группу {chat_id}: {e}"
                    logger.error(f"❌ {error_msg}")
                    self.publication_status['errors'].append({
                        'group': chat_id,
                        'error': error_msg,
                            'time': datetime.now(pytz.utc).astimezone(MOSCOW_TZ)
                    })
                    continue
            
            # Завершаем публикацию
            total_errors = len(self.publication_status['errors'])
            if is_scheduled_job and not self.is_running:
                logger.warning("⚠️ Публикация прервана из-за остановки планировщика")
                self._update_status("Публикация прервана")
            elif total_errors == 0:
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
                            'time': datetime.now(pytz.utc).astimezone(MOSCOW_TZ)
            })
            self._update_status(f"Критическая ошибка: {e}")
        finally:
            # Сбрасываем статус публикации только после полного завершения
            # Не сбрасываем сразу, чтобы показать финальный статус
            self.publication_status.update({
                'is_publishing': False,
                'current_step': 'Завершено' if (not is_scheduled_job or self.is_running) else 'Прервано',
                'last_update': datetime.now(pytz.utc).astimezone(MOSCOW_TZ)
            })
    
    async def _send_post_with_retry(self, target: str, group_name: str, current: int, total: int) -> bool:
        """
        Отправка поста с повторными попытками при ошибках
        
        Args:
            target: Целевой чат (username или chat_id)
            group_name: Название группы для логирования
            current: Номер текущей группы
            total: Всего групп
            
        Returns:
            True если отправка успешна, False если все попытки исчерпаны
        """
        for attempt in range(1, PUBLICATION_RETRY_ATTEMPTS + 1):
            try:
                success = await self.post_handler.send_post_to_group(target)
                
                if success:
                    if attempt > 1:
                        logger.info(f"✅ [{current}/{total}] Пост отправлен в группу {group_name} после {attempt} попыток")
                    return True
                else:
                    if attempt < PUBLICATION_RETRY_ATTEMPTS:
                        logger.warning(f"⚠️ [{current}/{total}] Попытка {attempt}/{PUBLICATION_RETRY_ATTEMPTS} не удалась для {group_name}. Повтор через {PUBLICATION_RETRY_DELAY} сек...")
                        await asyncio.sleep(PUBLICATION_RETRY_DELAY)
                    else:
                        logger.error(f"❌ [{current}/{total}] Все {PUBLICATION_RETRY_ATTEMPTS} попыток отправки в {group_name} не удались")
                        return False
            except Exception as e:
                if attempt < PUBLICATION_RETRY_ATTEMPTS:
                    logger.warning(f"⚠️ [{current}/{total}] Исключение при попытке {attempt}/{PUBLICATION_RETRY_ATTEMPTS} для {group_name}: {e}. Повтор через {PUBLICATION_RETRY_DELAY} сек...")
                    await asyncio.sleep(PUBLICATION_RETRY_DELAY)
                else:
                    logger.error(f"❌ [{current}/{total}] Исключение после всех {PUBLICATION_RETRY_ATTEMPTS} попыток для {group_name}: {e}")
                    return False
        
        return False
    
    def _update_status(self, step: str):
        """Обновление статуса публикации"""
        self.publication_status['current_step'] = step
        # Получаем текущее время в UTC и конвертируем в московское
        utc_now = datetime.now(pytz.utc)
        self.publication_status['last_update'] = utc_now.astimezone(MOSCOW_TZ)
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
        
        # Форматируем время в московском часовом поясе
        # Время уже должно быть в московском часовом поясе
        if status['start_time']:
            start_time = status['start_time']
            # Убеждаемся, что время в московском часовом поясе
            if start_time.tzinfo is None:
                # Если naive datetime, считаем что это UTC и конвертируем
                start_time = pytz.utc.localize(start_time).astimezone(MOSCOW_TZ)
            elif start_time.tzinfo != MOSCOW_TZ:
                # Если не в московском часовом поясе, конвертируем
                start_time = start_time.astimezone(MOSCOW_TZ)
            # Форматируем время - оно уже в московском часовом поясе
            status['start_time_str'] = start_time.strftime('%H:%M:%S')
        else:
            status['start_time_str'] = None
            
        if status['last_update']:
            last_update = status['last_update']
            # Убеждаемся, что время в московском часовом поясе
            if last_update.tzinfo is None:
                # Если naive datetime, считаем что это UTC и конвертируем
                last_update = pytz.utc.localize(last_update).astimezone(MOSCOW_TZ)
            elif last_update.tzinfo != MOSCOW_TZ:
                # Если не в московском часовом поясе, конвертируем
                last_update = last_update.astimezone(MOSCOW_TZ)
            # Форматируем время - оно уже в московском часовом поясе
            status['last_update_str'] = last_update.strftime('%H:%M:%S')
        else:
            status['last_update_str'] = None
        
        return status
