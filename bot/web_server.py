"""
Веб-сервер для управления системой публикации постов
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from threading import Thread
import os

from config import ADMIN_ID, API_ID, API_HASH, SESSION_FILE
from db import db
from scheduler import PostScheduler
from telegram_client import telegram_client
from handlers.post import PostHandler
from telethon import TelegramClient

logger = logging.getLogger(__name__)

app = Flask(__name__)
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
    """Форматирование временной метки"""
    if not timestamp:
        return "Никогда"
    
    try:
        # Если это уже строка, возвращаем как есть
        if isinstance(timestamp, str):
            return timestamp
        # Если это datetime объект, форматируем
        elif hasattr(timestamp, 'strftime'):
            # Если это naive datetime, считаем что это UTC и конвертируем в московское время
            if timestamp.tzinfo is None:
                from datetime import timezone
                utc_time = timestamp.replace(tzinfo=timezone.utc)
                local_time = utc_time.astimezone(timezone(timedelta(hours=3)))
                return local_time.strftime('%d.%m.%Y %H:%M:%S')
            else:
                return timestamp.strftime('%d.%m.%Y %H:%M:%S')
        else:
            return str(timestamp)
    except Exception:
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

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/api/status')
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
        next_run = "Неизвестно"
        publication_status = None
        
        if scheduler:
            status_info = scheduler.get_status()
            scheduler_status = "Запущен" if status_info['is_running'] else "Остановлен"
            
            # Получаем детальный статус публикации
            publication_status = scheduler.get_publication_status()
            
            if status_info['next_run']:
                # Конвертируем UTC время в локальное время для отображения
                next_run_time = status_info['next_run']
                logger.info(f"Next run time: {next_run_time}, type: {type(next_run_time)}")
                
                if hasattr(next_run_time, 'astimezone'):
                    # Если это datetime объект с timezone, конвертируем в московское время
                    from datetime import timezone
                    moscow_tz = timezone(timedelta(hours=3))
                    local_time = next_run_time.astimezone(moscow_tz)
                else:
                    # Если это naive datetime, считаем что это UTC
                    from datetime import timezone
                    utc_time = next_run_time.replace(tzinfo=timezone.utc)
                    # Добавляем 3 часа для московского времени (UTC+3)
                    local_time = utc_time.astimezone(timezone(timedelta(hours=3)))
                
                logger.info(f"Local time: {local_time}")
                # Форматируем время в московском часовом поясе
                next_run = local_time.strftime('%d.%m.%Y %H:%M:%S')
        
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
def api_groups():
    """API для получения списка групп"""
    try:
        groups = run_async(db.get_all_groups())
        groups_data = []
        
        logger.info(f"Получены группы из БД: {groups}")
        
        for group in groups:
            logger.info(f"Обрабатываем группу: {group}, тип: {type(group)}, длина: {len(group) if hasattr(group, '__len__') else 'N/A'}")
            
            if isinstance(group, (list, tuple)) and len(group) >= 5:
                # База данных возвращает: (chat_id, title, username, added_at, last_posted)
                chat_id, title, username, added_at, last_post_time = group
                groups_data.append({
                    'id': chat_id,
                    'title': title,
                    'username': username,
                    'last_post': _format_timestamp(last_post_time)
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
        
        return jsonify(groups_data)
    except Exception as e:
        logger.error(f"Ошибка получения групп: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/groups', methods=['POST'])
def api_add_group():
    """API для добавления группы"""
    try:
        data = request.get_json()
        group_input = data.get('group_input', '').strip()
        
        if not group_input:
            return jsonify({'error': 'Не указан идентификатор группы'}), 400
        
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
        # Извлекаем username из group_input если это username
        username = None
        if group_input.startswith('@'):
            username = group_input
        elif group_input.startswith('https://t.me/'):
            username = '@' + group_input.split('/')[-1]
        
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
def api_start_scheduler():
    """API для запуска планировщика"""
    try:
        if not scheduler:
            return jsonify({'error': 'Планировщик не инициализирован'}), 500
        
        # Запускаем планировщик в отдельном потоке
        import threading
        def start_scheduler_thread():
            try:
                # Создаем новый event loop для планировщика
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(scheduler.start())
            except Exception as e:
                logger.error(f"Ошибка в потоке планировщика: {e}")
        
        thread = threading.Thread(target=start_scheduler_thread, daemon=True)
        thread.start()
        
        return jsonify({'success': True, 'message': 'Планировщик запущен'})
        
    except Exception as e:
        logger.error(f"Ошибка запуска планировщика: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scheduler/stop', methods=['POST'])
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
def api_reload_post():
    """API для перезагрузки поста"""
    try:
        if not post_handler:
            return jsonify({'error': 'Обработчик постов не инициализирован'}), 500
        
        post_handler._load_post_content()
        post_info = post_handler.get_post_info()
        
        return jsonify({
            'success': True,
            'message': 'Пост перезагружен',
            'post_info': post_info
        })
        
    except Exception as e:
        logger.error(f"Ошибка перезагрузки поста: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset_publication_status', methods=['POST'])
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

def run_web_server(host='0.0.0.0', port=5000, debug=False):
    """Запуск веб-сервера"""
    init_web_server()
    app.run(host=host, port=port, debug=debug, threaded=True)

if __name__ == '__main__':
    run_web_server(debug=True)
