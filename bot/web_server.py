"""
Веб-сервер для управления системой публикации постов
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_from_directory
from flask_cors import CORS
from functools import wraps
from threading import Thread
import os
import secrets

# Используем pytz для работы с часовыми поясами (уже установлен как зависимость APScheduler)
import pytz

# Московский часовой пояс
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

from config import ADMIN_ID, API_ID, API_HASH, SESSION_FILE, WEB_PASSWORD
from db import db
from scheduler import PostScheduler
from telegram_client import telegram_client
from handlers.post import PostHandler
from telethon import TelegramClient

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
CORS(app)

# Глобальные переменные для управления
scheduler = None
post_handler = None
telegram_connected = False
web_telegram_client = None

def set_scheduler(scheduler_instance):
    """Установка экземпляра планировщика из main.py"""
    global scheduler
    scheduler = scheduler_instance
    logger.info("Планировщик установлен из main.py")

def login_required(f):
    """Декоратор для защиты endpoints от несанкционированного доступа"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({'error': 'Требуется аутентификация'}), 401
        return f(*args, **kwargs)
    return decorated_function

def validate_group_input(group_input):
    """
    Валидация и санитизация входных данных для группы/канала
    
    Args:
        group_input: Входная строка (username, ID, ссылка)
        
    Returns:
        tuple: (is_valid, sanitized_input, error_message)
    """
    if not group_input or not isinstance(group_input, str):
        return False, None, "Пустой ввод"
    
    # Удаляем пробелы
    group_input = group_input.strip()
    
    if not group_input:
        return False, None, "Пустой ввод"
    
    # Проверяем длину
    if len(group_input) > 255:
        return False, None, "Слишком длинный ввод (максимум 255 символов)"
    
    # Проверяем формат: username, ID или ссылка
    # Username: @username или username
    # ID: числовой ID (может быть отрицательным для групп)
    # Ссылка: https://t.me/username или t.me/username
    
    # Очищаем от потенциально опасных символов
    dangerous_chars = ['<', '>', '"', "'", '&', '\n', '\r']
    for char in dangerous_chars:
        if char in group_input:
            return False, None, f"Недопустимый символ: {char}"
    
    # Нормализуем username (убираем @ если есть)
    if group_input.startswith('@'):
        sanitized = group_input[1:]
    elif group_input.startswith('https://t.me/'):
        sanitized = group_input.replace('https://t.me/', '').strip()
    elif group_input.startswith('t.me/'):
        sanitized = group_input.replace('t.me/', '').strip()
    elif group_input.startswith('http://t.me/'):
        sanitized = group_input.replace('http://t.me/', '').strip()
    else:
        # Проверяем, является ли это числовым ID
        try:
            int(group_input)
            sanitized = group_input
        except ValueError:
            # Если не число, считаем что это username без @
            sanitized = group_input
    
    # Проверяем формат username (только буквы, цифры, подчеркивание)
    if sanitized and not sanitized.startswith('-') and not sanitized.lstrip('-').isdigit():
        if not all(c.isalnum() or c == '_' for c in sanitized):
            return False, None, "Недопустимый формат username (только буквы, цифры и подчеркивание)"
    
    return True, sanitized, None

def run_async(coro):
    """Запуск асинхронной функции"""
    import concurrent.futures
    import threading
    
    # Создаем новый event loop в отдельном потоке
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread)
        return future.result()

def get_chat_info_sync(chat_identifier):
    """Синхронное получение информации о чате через основной клиент"""
    import subprocess
    import json
    import tempfile
    import os
    
    # Создаем временный скрипт для получения информации о чате
    script_content = f"""
import asyncio
import sys
import os
sys.path.append('/app/bot')
from telethon import TelegramClient
from config import API_ID, API_HASH, SESSION_FILE

async def get_chat():
    # Создаем отдельную сессию для веб-клиента
    web_session_file = str(SESSION_FILE).replace('.session', '_web.session')
    client = TelegramClient(web_session_file, API_ID, API_HASH)
    await client.connect()
    
    # Проверяем, авторизован ли клиент
    if not await client.is_user_authorized():
        # Если не авторизован, копируем данные из основной сессии
        import shutil
        try:
            shutil.copy2(str(SESSION_FILE), web_session_file)
            await client.disconnect()
            client = TelegramClient(web_session_file, API_ID, API_HASH)
            await client.connect()
        except Exception as e:
            print(f"Ошибка копирования сессии: {{e}}")
            return {{"success": False, "error": f"Ошибка авторизации: {{e}}"}}
    
    try:
        chat = await client.get_entity("{chat_identifier}")
        result = {{
            "success": True,
            "chat_id": str(chat.id),
            "title": getattr(chat, 'title', 'Unknown'),
            "chat_type": type(chat).__name__
        }}
    except Exception as e:
        result = {{
            "success": False,
            "error": str(e)
        }}
    finally:
        await client.disconnect()
    
    print(json.dumps(result))

if __name__ == "__main__":
    import json
    asyncio.run(get_chat())
"""
    
    # Записываем скрипт во временный файл
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        script_path = f.name
    
    try:
        # Запускаем скрипт
        result = subprocess.run([
            'python', script_path
        ], capture_output=True, text=True, cwd='/app/bot')
        
        if result.returncode == 0:
            data = json.loads(result.stdout.strip())
            if data['success']:
                return (data['chat_id'], data['title'], data['chat_type'])
            else:
                logger.error(f"Ошибка получения информации о чате {chat_identifier}: {data['error']}")
                return None
        else:
            logger.error(f"Ошибка выполнения скрипта: {result.stderr}")
            return None
            
    finally:
        # Удаляем временный файл
        os.unlink(script_path)

def _format_timestamp(timestamp):
    """Форматирование временной метки в московском часовом поясе"""
    if not timestamp:
        return "Никогда"
    
    try:
        # Если это уже строка, пытаемся распарсить её
        if isinstance(timestamp, str):
            # Пробуем разные форматы времени из БД
            from datetime import datetime as dt
            try:
                # Формат из SQLite: "2025-11-05 18:21:22"
                parsed_time = dt.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                # Считаем что это UTC время из базы данных
                utc_time = pytz.utc.localize(parsed_time)
                moscow_time = utc_time.astimezone(MOSCOW_TZ)
                return moscow_time.strftime('%d.%m.%Y %H:%M:%S')
            except ValueError:
                # Если не удалось распарсить, возвращаем как есть
                return timestamp
        # Если это datetime объект, форматируем
        elif hasattr(timestamp, 'strftime'):
            # Конвертируем в московское время
            if timestamp.tzinfo is None:
                # Если naive datetime, считаем что это UTC и конвертируем в московское время
                utc_time = pytz.utc.localize(timestamp)
                moscow_time = utc_time.astimezone(MOSCOW_TZ)
            else:
                # Если уже с timezone, конвертируем в московское время
                moscow_time = timestamp.astimezone(MOSCOW_TZ)
            return moscow_time.strftime('%d.%m.%Y %H:%M:%S')
        else:
            return str(timestamp)
    except Exception as e:
        logger.error(f"Ошибка форматирования времени: {e}, timestamp: {timestamp}")
        return "Неизвестно"

def init_web_server():
    """Инициализация веб-сервера"""
    global scheduler, post_handler, telegram_connected
    
    # Инициализируем компоненты только если они еще не установлены
    if scheduler is None:
        scheduler = PostScheduler()
        logger.info("Создан новый экземпляр планировщика в web_server")
    
    if post_handler is None:
        post_handler = PostHandler()
    
    # Проверяем подключение к Telegram
    telegram_connected = telegram_client.is_connected()

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Сервирование статических файлов (изображений)"""
    try:
        data_dir = Path(__file__).parent / 'data'
        return send_from_directory(str(data_dir), filename)
    except Exception as e:
        logger.error(f"Ошибка загрузки файла {filename}: {e}")
        return jsonify({'error': 'File not found'}), 404

@app.route('/')
def index():
    """Главная страница"""
    if not session.get('authenticated'):
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == WEB_PASSWORD:
            session['authenticated'] = True
            session.permanent = True
            return jsonify({'success': True, 'redirect': '/'})
        else:
            return jsonify({'success': False, 'error': 'Неверный пароль'}), 401
    
    # GET запрос - показываем страницу входа
    if session.get('authenticated'):
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    """Выход из системы"""
    session.pop('authenticated', None)
    return jsonify({'success': True, 'redirect': '/login'})

@app.route('/api/login', methods=['POST'])
def api_login():
    """API для аутентификации"""
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        if password == WEB_PASSWORD:
            session['authenticated'] = True
            session.permanent = True
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Неверный пароль'}), 401
    except Exception as e:
        logger.error(f"Ошибка аутентификации: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
@login_required
def api_status():
    """API для получения статуса системы"""
    try:
        # Получаем информацию о группах
        groups = run_async(db.get_all_groups())
        groups_count = len(groups)
        
        # Получаем интервал публикации в минутах
        interval_minutes = run_async(db.get_post_interval_minutes())
        
        # Форматируем интервал для отображения
        if interval_minutes < 60:
            interval_display = f"{interval_minutes} мин"
        elif interval_minutes == 60:
            interval_display = "1 час"
        else:
            hours = interval_minutes // 60
            minutes = interval_minutes % 60
            if minutes > 0:
                interval_display = f"{hours}ч {minutes}м"
            else:
                interval_display = f"{hours}ч"
        
        # Статус планировщика
        scheduler_status = "Не инициализирован"
        next_run = None  # Используем None вместо "Неизвестно", чтобы клиент мог форматировать
        publication_status = None
        
        if scheduler:
            status_info = scheduler.get_status()
            scheduler_status = "Запущен" if status_info['is_running'] else "Остановлен"
            
            # Получаем детальный статус публикации
            publication_status = scheduler.get_publication_status()
            
            if status_info['next_run']:
                # Конвертируем UTC время в московское время для отображения
                next_run_time = status_info['next_run']
                logger.info(f"Next run time: {next_run_time}, type: {type(next_run_time)}")
                
                # Конвертируем в московское время
                if hasattr(next_run_time, 'astimezone'):
                    # Если это datetime объект с timezone, конвертируем в московское время
                    moscow_time = next_run_time.astimezone(MOSCOW_TZ)
                else:
                    # Если это naive datetime, считаем что это UTC
                    from datetime import timezone
                    utc_time = next_run_time.replace(tzinfo=timezone.utc)
                    moscow_time = utc_time.astimezone(MOSCOW_TZ)
                
                logger.info(f"Moscow time: {moscow_time}")
                # Форматируем время в московском часовом поясе
                next_run = moscow_time.strftime('%d.%m.%Y %H:%M:%S')
        
        # Информация о посте
        post_info = post_handler.get_post_info() if post_handler else {}
        
        return jsonify({
            'telegram_connected': telegram_connected,
            'groups_count': groups_count,
            'interval': interval_display,
            'interval_minutes': interval_minutes,
            'scheduler_status': scheduler_status,
            'next_run': next_run,
            'post_info': post_info,
            'publication_status': publication_status
        })
    except Exception as e:
        logger.error(f"Ошибка получения статуса: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/groups')
@login_required
def api_groups():
    """API для получения списка групп"""
    try:
        groups = run_async(db.get_all_groups())
        groups_data = []
        
        logger.info(f"Получены группы из БД: {groups}")
        
        for group in groups:
            logger.info(f"Обрабатываем группу: {group}, тип: {type(group)}, длина: {len(group) if hasattr(group, '__len__') else 'N/A'}")
            
            if isinstance(group, (list, tuple)) and len(group) >= 6:
                # База данных возвращает: (chat_id, title, username, added_at, last_posted, is_disabled)
                chat_id, title, username, added_at, last_post_time, is_disabled = group
                groups_data.append({
                    'id': chat_id,
                    'title': title,
                    'username': username,
                    'last_post': _format_timestamp(last_post_time),
                    'is_disabled': bool(is_disabled)
                })
            elif isinstance(group, (list, tuple)) and len(group) >= 5:
                # База данных возвращает: (chat_id, title, username, added_at, last_posted)
                chat_id, title, username, added_at, last_post_time = group
                groups_data.append({
                    'id': chat_id,
                    'title': title,
                    'username': username,
                    'last_post': _format_timestamp(last_post_time),
                    'is_disabled': False
                })
            elif isinstance(group, (list, tuple)) and len(group) >= 4:
                # Fallback для старого формата: (chat_id, title, added_at, last_posted)
                chat_id, title, added_at, last_post_time = group
                groups_data.append({
                    'id': chat_id,
                    'title': title,
                    'username': None,
                    'last_post': _format_timestamp(last_post_time)
                })
            elif isinstance(group, (list, tuple)) and len(group) >= 3:
                # Fallback для старого формата
                chat_id, title, last_post_time = group
                groups_data.append({
                    'id': chat_id,
                    'title': title,
                    'last_post': _format_timestamp(last_post_time)
                })
            elif isinstance(group, (list, tuple)) and len(group) > 0:
                # Обработка случая, когда в группе меньше 3 элементов
                chat_id = group[0] if len(group) > 0 else "unknown"
                title = group[1] if len(group) > 1 else "Unknown"
                last_post_time = group[2] if len(group) > 2 else None
                groups_data.append({
                    'id': chat_id,
                    'title': title,
                    'last_post': _format_timestamp(last_post_time)
                })
            else:
                logger.warning(f"Неожиданный формат группы: {group}")
                groups_data.append({
                    'id': "unknown",
                    'title': "Unknown",
                    'last_post': "Никогда"
                })
        
        return jsonify({'groups': groups_data})
    except Exception as e:
        logger.error(f"Ошибка получения групп: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/groups', methods=['POST'])
@login_required
def api_add_group():
    """API для добавления группы"""
    try:
        # Валидация входных данных
        data = request.get_json()
        group_input = data.get('group_input', '')
        
        is_valid, sanitized_input, error_message = validate_group_input(group_input)
        if not is_valid:
            return jsonify({'error': error_message or 'Неверный формат группы'}), 400
        
        # Используем очищенный ввод
        group_input = sanitized_input
        
        # Получаем информацию о чате
        try:
            result = get_chat_info_sync(group_input)
            logger.info(f"Результат get_chat_info_sync для '{group_input}': {result}")
            
            if not result or result[0] is None:
                return jsonify({'error': f'Не удалось найти чат "{group_input}". Проверьте, что чат существует и ваша учетная запись имеет к нему доступ.'}), 400
            
            chat_id, title, chat_type = result
            logger.info(f"Найден чат: ID={chat_id}, Title={title}, Type={chat_type}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о чате '{group_input}': {e}")
            return jsonify({'error': f'Ошибка при получении информации о чате: {str(e)}'}), 400
        
        # Добавляем группу в базу данных
        # Извлекаем username из sanitized_input если это username (не числовой ID)
        username = None
        # Проверяем, является ли sanitized_input числовым ID
        try:
            int(sanitized_input.lstrip('-'))
            # Это числовой ID, username будет None
            username = None
        except ValueError:
            # Это не числовой ID, значит это username
            username = '@' + sanitized_input if not sanitized_input.startswith('@') else sanitized_input
        
        success = run_async(db.add_group(chat_id, title, username))
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Чат "{title}" добавлен',
                'group': {
                    'id': chat_id,
                    'title': title,
                    'type': chat_type
                }
            })
        else:
            return jsonify({'error': 'Чат уже добавлен или произошла ошибка'}), 400
            
    except Exception as e:
        logger.error(f"Ошибка добавления группы: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/groups/<chat_id>', methods=['DELETE'])
@login_required
def api_remove_group(chat_id):
    """API для удаления группы"""
    try:
        success = run_async(db.remove_group(chat_id))
        
        if success:
            return jsonify({'success': True, 'message': f'Чат {chat_id} удален'})
        else:
            return jsonify({'error': 'Чат не найден или произошла ошибка'}), 400
            
    except Exception as e:
        logger.error(f"Ошибка удаления группы: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/interval', methods=['POST'])
@login_required
def api_set_interval():
    """API для установки интервала публикации"""
    try:
        data = request.get_json()
        minutes = data.get('minutes')
        hours = data.get('hours')  # Для обратной совместимости
        
        # Определяем интервал в минутах
        if minutes is not None:
            interval_minutes = minutes
        elif hours is not None:
            interval_minutes = hours * 60
        else:
            return jsonify({'error': 'Не указан интервал'}), 400
        
        if not isinstance(interval_minutes, int) or interval_minutes <= 0:
            return jsonify({'error': 'Неверный интервал'}), 400
        
        # Максимальный интервал: 7 дней (10080 минут)
        if interval_minutes > 10080:
            return jsonify({'error': 'Максимальный интервал: 10080 минут (7 дней)'}), 400
        
        success = run_async(db.set_post_interval_minutes(interval_minutes))
        
        if success:
            # Обновляем планировщик
            if scheduler:
                try:
                    run_async(scheduler.update_interval_minutes(interval_minutes))
                except Exception as e:
                    logger.error(f"Ошибка обновления планировщика: {e}")
                    # Продолжаем, даже если планировщик не обновился
            
            # Форматируем сообщение
            if interval_minutes < 60:
                message = f'Интервал установлен: {interval_minutes} минут'
            else:
                hours = interval_minutes // 60
                mins = interval_minutes % 60
                if mins > 0:
                    message = f'Интервал установлен: {hours}ч {mins}м'
                else:
                    message = f'Интервал установлен: {hours} часов'
            
            return jsonify({
                'success': True,
                'message': message,
                'interval_minutes': interval_minutes
            })
        else:
            return jsonify({'error': 'Ошибка установки интервала'}), 400
            
    except Exception as e:
        logger.error(f"Ошибка установки интервала: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/post_now', methods=['POST'])
@login_required
def api_post_now():
    """API для немедленной публикации"""
    try:
        if not scheduler:
            return jsonify({'error': 'Планировщик не инициализирован'}), 500
        
        # Запускаем публикацию
        run_async(scheduler.post_now())
        
        return jsonify({'success': True, 'message': 'Публикация запущена'})
        
    except Exception as e:
        logger.error(f"Ошибка публикации: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scheduler/start', methods=['POST'])
@login_required
def api_start_scheduler():
    """API для запуска планировщика"""
    try:
        if not scheduler:
            return jsonify({'error': 'Планировщик не инициализирован'}), 500
        
        # Запускаем планировщик в отдельном потоке с постоянным event loop
        import threading
        def start_scheduler_thread():
            try:
                # Создаем новый event loop для планировщика
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Запускаем планировщик
                loop.run_until_complete(scheduler.start())
                
                # Запускаем event loop постоянно, чтобы планировщик мог работать
                loop.run_forever()
            except Exception as e:
                logger.error(f"Ошибка в потоке планировщика: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        thread = threading.Thread(target=start_scheduler_thread, daemon=True)
        thread.start()
        
        return jsonify({'success': True, 'message': 'Планировщик запущен'})
        
    except Exception as e:
        logger.error(f"Ошибка запуска планировщика: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scheduler/stop', methods=['POST'])
@login_required
def api_stop_scheduler():
    """API для остановки планировщика"""
    try:
        if not scheduler:
            return jsonify({'error': 'Планировщик не инициализирован'}), 500
        
        run_async(scheduler.stop())
        
        return jsonify({'success': True, 'message': 'Планировщик остановлен'})
        
    except Exception as e:
        logger.error(f"Ошибка остановки планировщика: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reload_post', methods=['POST'])
@login_required
def api_reload_post():
    """API для перезагрузки поста"""
    try:
        if not post_handler:
            logger.error("post_handler не инициализирован")
            return jsonify({'error': 'Обработчик постов не инициализирован'}), 500
        
        logger.info("Начинаем перезагрузку поста...")
        
        # Перезагружаем пост в веб-сервере
        post_handler._load_post_content()
        post_info = post_handler.get_post_info()
        
        # Перезагружаем пост в планировщике (если он есть)
        if scheduler:
            scheduler.reload_post()
            logger.info("Пост перезагружен и в планировщике")
        
        logger.info(f"Пост успешно перезагружен: {post_info}")
        
        return jsonify({
            'success': True,
            'message': 'Пост перезагружен',
            'post_info': post_info
        })
        
    except Exception as e:
        logger.error(f"Ошибка перезагрузки поста: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset_publication_status', methods=['POST'])
@login_required
def api_reset_publication_status():
    """API для сброса статуса публикации"""
    try:
        if not scheduler:
            return jsonify({'error': 'Планировщик не инициализирован'}), 500
        
        scheduler.reset_publication_status()
        
        return jsonify({
            'success': True,
            'message': 'Статус публикации сброшен'
        })
        
    except Exception as e:
        logger.error(f"Ошибка сброса статуса публикации: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/publication_history', methods=['GET'])
@login_required
def api_publication_history():
    """API для получения истории публикаций"""
    try:
        # Получаем параметры фильтрации
        limit = request.args.get('limit', default=100, type=int)
        offset = request.args.get('offset', default=0, type=int)
        chat_id = request.args.get('chat_id', default=None, type=str)
        status = request.args.get('status', default=None, type=str)
        start_date = request.args.get('start_date', default=None, type=str)
        end_date = request.args.get('end_date', default=None, type=str)
        search = request.args.get('search', default=None, type=str)
        
        # Получаем историю
        history = run_async(db.get_publication_history(
            limit=limit,
            offset=offset,
            chat_id=chat_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            search=search
        ))
        
        # Форматируем данные для ответа
        history_data = []
        for record in history:
            id, chat_id_val, chat_title, chat_username, status_val, error_message, published_at, retry_count = record
            history_data.append({
                'id': id,
                'chat_id': chat_id_val,
                'chat_title': chat_title,
                'chat_username': chat_username,
                'status': status_val,
                'error_message': error_message,
                'published_at': _format_timestamp(published_at),
                'retry_count': retry_count
            })
        
        return jsonify({
            'success': True,
            'history': history_data,
            'total': len(history_data)
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения истории публикаций: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/publication_statistics', methods=['GET'])
@login_required
def api_publication_statistics():
    """API для получения статистики публикаций"""
    try:
        # Получаем параметры фильтрации по датам
        start_date = request.args.get('start_date', default=None, type=str)
        end_date = request.args.get('end_date', default=None, type=str)
        
        # Получаем статистику
        statistics = run_async(db.get_publication_statistics(
            start_date=start_date,
            end_date=end_date
        ))
        
        return jsonify({
            'success': True,
            'statistics': statistics
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/publication_history/clear', methods=['POST'])
@login_required
def api_clear_publication_history():
    """API для очистки истории публикаций"""
    try:
        data = request.get_json() or {}
        days = data.get('days', None)
        
        if days is not None:
            days = int(days)
        
        success = run_async(db.clear_publication_history(days=days))
        
        if success:
            return jsonify({
                'success': True,
                'message': f'История очищена' + (f' (оставлены записи за последние {days} дней)' if days else '')
            })
        else:
            return jsonify({'error': 'Ошибка при очистке истории'}), 500
        
    except Exception as e:
        logger.error(f"Ошибка очистки истории: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates', methods=['GET'])
@login_required
def api_get_templates():
    """API для получения списка шаблонов"""
    try:
        templates = run_async(db.get_all_templates())
        
        templates_data = []
        for template in templates:
            id, name, content, is_active, created_at, updated_at = template
            templates_data.append({
                'id': id,
                'name': name,
                'content': content,
                'is_active': bool(is_active),
                'created_at': _format_timestamp(created_at),
                'updated_at': _format_timestamp(updated_at)
            })
        
        return jsonify({
            'success': True,
            'templates': templates_data
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения шаблонов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates', methods=['POST'])
@login_required
def api_create_template():
    """API для создания шаблона"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'content' not in data:
            return jsonify({'error': 'Не указаны name и content'}), 400
        
        template_id = run_async(db.add_post_template(data['name'], data['content']))
        
        if template_id:
            return jsonify({
                'success': True,
                'message': 'Шаблон создан',
                'template_id': template_id
            })
        else:
            return jsonify({'error': 'Ошибка при создании шаблона'}), 500
        
    except Exception as e:
        logger.error(f"Ошибка создания шаблона: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates/<int:template_id>', methods=['PUT'])
@login_required
def api_update_template(template_id):
    """API для обновления шаблона"""
    try:
        data = request.get_json() or {}
        
        name = data.get('name')
        content = data.get('content')
        
        success = run_async(db.update_template(template_id, name=name, content=content))
        
        if success:
            # Перезагружаем пост, если это активный шаблон
            if post_handler:
                post_handler.reload_post_content()
            
            return jsonify({
                'success': True,
                'message': 'Шаблон обновлен'
            })
        else:
            return jsonify({'error': 'Ошибка при обновлении шаблона'}), 500
        
    except Exception as e:
        logger.error(f"Ошибка обновления шаблона: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
@login_required
def api_delete_template(template_id):
    """API для удаления шаблона"""
    try:
        success = run_async(db.delete_template(template_id))
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Шаблон удален'
            })
        else:
            return jsonify({'error': 'Ошибка при удалении шаблона'}), 500
        
    except Exception as e:
        logger.error(f"Ошибка удаления шаблона: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates/<int:template_id>/activate', methods=['POST'])
@login_required
def api_activate_template(template_id):
    """API для активации шаблона"""
    try:
        success = run_async(db.set_active_template(template_id))
        
        if success:
            # Перезагружаем пост
            if post_handler:
                post_handler.reload_post_content()
            
            return jsonify({
                'success': True,
                'message': 'Шаблон активирован'
            })
        else:
            return jsonify({'error': 'Ошибка при активации шаблона'}), 500
        
    except Exception as e:
        logger.error(f"Ошибка активации шаблона: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/post/info', methods=['GET'])
@login_required
def api_post_info():
    """API для получения информации о текущем посте"""
    try:
        if not post_handler:
            return jsonify({'error': 'Post handler не инициализирован'}), 500
        
        info = post_handler.get_post_info()
        
        # Получаем путь к изображению, если есть
        image_url = None
        if info.get('has_image') and info.get('image_path'):
            # Проверяем, что файл действительно существует
            image_path = Path(info['image_path'])
            if image_path.exists() and image_path.is_file():
                # Возвращаем относительный путь к изображению
                image_url = f'/static/{image_path.name}'
            else:
                # Файл не существует, не возвращаем URL
                image_url = None
        
        return jsonify({
            'success': True,
            'post': {
                'text': info.get('text', ''),
                'text_length': info.get('text_length', 0),
                'has_image': image_url is not None,  # Устанавливаем has_image только если URL действителен
                'image_url': image_url,
                'use_template': info.get('use_template', False),
                'template_name': info.get('template_name'),
                'template_id': info.get('template_id')
            }
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения информации о посте: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/post/preview', methods=['POST'])
@login_required
def api_post_preview():
    """API для предпросмотра поста с заменой переменных"""
    try:
        data = request.get_json() or {}
        chat_id = data.get('chat_id', '123456789')
        chat_title = data.get('chat_title', 'Тестовая группа')
        
        # Получаем текущий текст поста
        if not post_handler:
            return jsonify({'error': 'Post handler не инициализирован'}), 500
        
        # Получаем текст с заменой переменных
        preview_text = run_async(post_handler.get_post_text(chat_id, chat_title))
        
        # Получаем информацию об изображении
        info = post_handler.get_post_info()
        image_url = None
        has_image = False
        if info.get('has_image') and info.get('image_path'):
            # Проверяем, что файл действительно существует
            image_path = Path(info['image_path'])
            if image_path.exists() and image_path.is_file():
                image_url = f'/static/{image_path.name}'
                has_image = True
        
        return jsonify({
            'success': True,
            'preview': {
                'text': preview_text,
                'has_image': has_image,
                'image_url': image_url if has_image else None
            }
        })
        
    except Exception as e:
        logger.error(f"Ошибка предпросмотра поста: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules', methods=['GET'])
@login_required
def api_get_schedules():
    """API для получения списка расписаний"""
    try:
        schedules = run_async(db.get_all_schedules())
        
        schedules_data = []
        for schedule in schedules:
            id, schedule_type, schedule_data, is_active, created_at, updated_at = schedule
            schedules_data.append({
                'id': id,
                'schedule_type': schedule_type,
                'schedule_data': schedule_data,
                'is_active': bool(is_active),
                'created_at': _format_timestamp(created_at),
                'updated_at': _format_timestamp(updated_at)
            })
        
        return jsonify({
            'success': True,
            'schedules': schedules_data
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения расписаний: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules', methods=['POST'])
@login_required
def api_create_schedule():
    """API для создания расписания"""
    try:
        data = request.get_json()
        
        if not data or 'schedule_type' not in data or 'schedule_data' not in data:
            return jsonify({'error': 'Не указаны schedule_type и schedule_data'}), 400
        
        schedule_id = run_async(db.add_schedule(data['schedule_type'], data['schedule_data']))
        
        if schedule_id:
            # Если это первое расписание или оно помечено как активное, активируем его
            if data.get('is_active', False):
                run_async(db.set_active_schedule(schedule_id))
                # Перезагружаем расписание в планировщике
                if scheduler:
                    async def reload():
                        await scheduler.reload_schedule()
                    run_async(reload())
            
            return jsonify({
                'success': True,
                'message': 'Расписание создано',
                'schedule_id': schedule_id
            })
        else:
            return jsonify({'error': 'Ошибка при создании расписания'}), 500
        
    except Exception as e:
        logger.error(f"Ошибка создания расписания: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules/<int:schedule_id>', methods=['PUT'])
@login_required
def api_update_schedule(schedule_id):
    """API для обновления расписания"""
    try:
        data = request.get_json() or {}
        
        schedule_type = data.get('schedule_type')
        schedule_data = data.get('schedule_data')
        
        success = run_async(db.update_schedule(schedule_id, schedule_type=schedule_type, schedule_data=schedule_data))
        
        if success:
            # Если расписание активно, перезагружаем его
            schedule = run_async(db.get_active_schedule())
            if schedule and schedule[0] == schedule_id:
                if scheduler:
                    run_async(scheduler.reload_schedule())
            
            return jsonify({
                'success': True,
                'message': 'Расписание обновлено'
            })
        else:
            return jsonify({'error': 'Ошибка при обновлении расписания'}), 500
        
    except Exception as e:
        logger.error(f"Ошибка обновления расписания: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
@login_required
def api_delete_schedule(schedule_id):
    """API для удаления расписания"""
    try:
        success = run_async(db.delete_schedule(schedule_id))
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Расписание удалено'
            })
        else:
            return jsonify({'error': 'Ошибка при удалении расписания'}), 500
        
    except Exception as e:
        logger.error(f"Ошибка удаления расписания: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules/<int:schedule_id>/activate', methods=['POST'])
@login_required
def api_activate_schedule(schedule_id):
    """API для активации расписания"""
    try:
        success = run_async(db.set_active_schedule(schedule_id))
        
        if success:
            # Перезагружаем расписание в планировщике
            if scheduler:
                run_async(scheduler.reload_schedule())
            
            return jsonify({
                'success': True,
                'message': 'Расписание активировано'
            })
        else:
            return jsonify({'error': 'Ошибка при активации расписания'}), 500
        
    except Exception as e:
        logger.error(f"Ошибка активации расписания: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/groups/<chat_id>/toggle-disabled', methods=['POST'])
@login_required
def api_toggle_group_disabled(chat_id):
    """API для добавления/удаления группы из черного списка"""
    try:
        data = request.get_json() or {}
        is_disabled = data.get('is_disabled', True)
        
        success = run_async(db.set_group_disabled(chat_id, is_disabled))
        
        if success:
            action = 'добавлена в черный список' if is_disabled else 'удалена из черного списка'
            return jsonify({
                'success': True,
                'message': f'Группа {action}'
            })
        else:
            return jsonify({'error': 'Группа не найдена или произошла ошибка'}), 400
            
    except Exception as e:
        logger.error(f"Ошибка изменения статуса группы: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates/preview', methods=['POST'])
@login_required
def api_preview_template():
    """API для предпросмотра шаблона с заменой переменных"""
    try:
        data = request.get_json() or {}
        content = data.get('content', '')
        
        # Создаем временный экземпляр для замены переменных
        from handlers.post import PostHandler
        temp_handler = PostHandler()
        preview_text = temp_handler._replace_variables(content, '123456789', 'Тестовая группа')
        
        return jsonify({
            'success': True,
            'preview': preview_text
        })
        
    except Exception as e:
        logger.error(f"Ошибка предпросмотра шаблона: {e}")
        return jsonify({'error': str(e)}), 500

def run_web_server(host='0.0.0.0', port=5000, debug=False):
    """Запуск веб-сервера"""
    init_web_server()
    app.run(host=host, port=port, debug=debug, threaded=True)

if __name__ == '__main__':
    run_web_server(debug=True)
