// Утилиты: переводы, безопасный fetch, toast, форматирование
// Используется как обычный скрипт (не ES6 модуль)

(function() {
    'use strict';
    
    // Переводы
    window.translations = {
        ru: {
            'app.title': 'Система публикации постов',
            'connection.checking': 'Проверка подключения...',
            'connection.connected': 'Подключен',
            'connection.disconnected': 'Отключен',
            'status.groups': 'Группы',
            'status.interval': 'Интервал',
            'status.scheduler': 'Планировщик',
            'status.nextPublication': 'Следующая публикация',
            'status.publication': 'Статус публикации',
            'status.running': 'Запущен',
            'status.stopped': 'Остановлен',
            'status.notActive': 'Неактивно',
            'status.publishing': 'Публикация',
            'status.waiting': 'Ожидание',
            'publication.details': 'Детальный статус публикации',
            'publication.currentStep': 'Текущий этап:',
            'publication.progress': 'Прогресс:',
            'publication.startTime': 'Время начала:',
            'publication.lastUpdate': 'Последнее обновление:',
            'publication.errors': 'Ошибки:',
            'actions.quick': 'Быстрые действия',
            'actions.publishNow': 'Опубликовать сейчас',
            'actions.startScheduler': 'Запустить планировщик',
            'actions.stop': 'Остановить',
            'actions.reloadPost': 'Перезагрузить пост',
            'settings.title': 'Настройки',
            'settings.interval': 'Интервал публикации',
            'settings.set': 'Установить',
            'settings.maxMinutes': 'Максимум: 10080 минут (7 дней). Минимум: 1 минута.',
            'groups.add': 'Добавить группу/канал',
            'groups.input': 'Ссылка, @username или ID',
            'groups.addButton': 'Добавить группу',
            'groups.list': 'Список групп/каналов',
            'groups.empty': 'Нет добавленных групп',
            'groups.emptyDesc': 'Добавьте группу или канал для начала работы',
            'groups.loading': 'Загрузка групп...',
            'groups.lastPost': 'Последняя публикация:',
            'groups.delete': 'Удалить группу',
            'groups.deleteConfirm': 'Удалить эту группу?',
            'groups.active': 'Активна',
            'groups.disabled': 'Отключена',
            'groups.enable': 'Включить группу',
            'groups.disable': 'Отключить группу',
            'groups.disabledSuccess': 'Группа отключена',
            'groups.enabledSuccess': 'Группа включена',
            'toast.notification': 'Уведомление',
            'toast.enterGroup': 'Введите ссылку, @username или ID группы',
            'toast.maxInterval': 'Максимальный интервал: 10080 минут (7 дней)',
            'toast.invalidInterval': 'Введите корректный интервал (больше 0)',
            'toast.unknownUnit': 'Неизвестная единица измерения',
            'toast.errorPublishing': 'Ошибка публикации',
            'toast.errorStartScheduler': 'Ошибка запуска планировщика',
            'toast.errorStopScheduler': 'Ошибка остановки планировщика',
            'toast.errorReloadPost': 'Ошибка перезагрузки поста',
            'toast.errorAddGroup': 'Ошибка добавления группы',
            'toast.errorToggleGroup': 'Ошибка изменения статуса группы',
            'toast.errorSetInterval': 'Ошибка установки интервала',
            'toast.groupNotFound': 'Не удалось найти чат. Проверьте, что чат существует и ваша учетная запись имеет к нему доступ.',
            'toast.groupNotSpecified': 'Не указан идентификатор группы',
            'toast.groupAlreadyAdded': 'Чат уже добавлен или произошла ошибка',
            'toast.groupDeleted': 'Группа удалена',
            'toast.groupAdded': 'Группа добавлена',
            'toast.intervalNotSpecified': 'Не указан интервал',
            'toast.invalidInterval': 'Неверный интервал',
            'toast.maxIntervalError': 'Максимальный интервал: 10080 минут (7 дней)',
            'toast.intervalSet': 'Интервал установлен',
            'toast.publicationStarted': 'Публикация запущена',
            'toast.schedulerStarted': 'Планировщик запущен',
            'toast.schedulerStopped': 'Планировщик остановлен',
            'toast.schedulerNotInitialized': 'Планировщик не инициализирован',
            'toast.postHandlerNotInitialized': 'Обработчик постов не инициализирован',
            'toast.postReloaded': 'Пост перезагружен',
            'toast.statusReset': 'Статус публикации сброшен',
            'publication.completed': 'Завершено',
            'publication.cancelled': 'Прервано',
            'publication.completedSuccess': 'Публикация завершена успешно!',
            'publication.completedWithErrors': 'Публикация завершена с ошибками',
            'publication.criticalError': 'Критическая ошибка',
            'publication.initialization': 'Инициализация',
            'publication.gettingGroups': 'Получение списка групп...',
            'publication.publishing': 'Публикация в {total} групп',
            'publication.publishingGroup': 'Публикация в группу {current}/{total}: {group}',
            'publication.groupSuccess': 'Группа {current}/{total}: {group} - успешно',
            'publication.groupError': 'Группа {current}/{total}: {group} - ошибка',
            'publication.waiting': 'Ожидание {seconds} секунд...',
            'publication.stopped': 'Публикация остановлена на группе {current}/{total}',
            'groups.noTitle': 'Без названия',
            'groups.never': 'Никогда',
            'history.title': 'История публикаций',
            'history.loading': 'Загрузка...',
            'history.empty': 'История пуста',
            'history.filters.status': 'Статус',
            'history.filters.search': 'Поиск',
            'history.filters.dateFrom': 'С даты',
            'history.filters.dateTo': 'По дату',
            'history.filters.apply': 'Применить',
            'history.table.time': 'Время',
            'history.table.group': 'Группа',
            'history.table.status': 'Статус',
            'history.table.retries': 'Попытки',
            'history.table.error': 'Ошибка',
            'history.prev': 'Назад',
            'history.next': 'Вперед',
            'history.clear': 'Очистить историю',
            'history.clearConfirm': 'Вы уверены, что хотите очистить историю публикаций?',
            'history.status.success': 'Успешно',
            'history.status.error': 'Ошибка',
            'statistics.title': 'Статистика публикаций',
            'statistics.total': 'Всего публикаций',
            'statistics.successful': 'Успешных',
            'statistics.failed': 'Неудачных',
            'statistics.successRate': 'Процент успеха',
            'statistics.topGroups': 'Топ групп',
            'statistics.dailyActivity': 'Активность по дням',
            'statistics.hourlyActivity': 'Активность по часам',
            'statistics.publications': 'Публикации',
            'statistics.noData': 'Нет данных',
            'statistics.filterFrom': 'С даты',
            'statistics.filterTo': 'По дату',
            'statistics.filterApply': 'Применить',
            'templates.title': 'Шаблоны постов',
            'templates.create': 'Создать шаблон',
            'templates.loading': 'Загрузка...',
            'templates.empty': 'Нет шаблонов',
            'templates.table.name': 'Название',
            'templates.table.content': 'Содержимое',
            'templates.table.status': 'Статус',
            'templates.table.actions': 'Действия',
            'templates.status.active': 'Активен',
            'templates.status.inactive': 'Неактивен',
            'templates.actions.edit': 'Редактировать',
            'templates.actions.activate': 'Активировать',
            'templates.actions.delete': 'Удалить',
            'templates.deleteConfirm': 'Вы уверены, что хотите удалить этот шаблон?',
            'templates.variables.title': 'Доступные переменные:',
            'templates.variables.date': 'текущая дата',
            'templates.variables.time': 'текущее время',
            'templates.variables.datetime': 'дата и время',
            'templates.variables.chatId': 'ID чата',
            'templates.variables.chatTitle': 'название чата',
            'templates.variables.random': 'случайное число (1-1000)',
            'templates.variables.randomRange': 'случайное число от min до max',
            'templates.form.name': 'Название',
            'templates.form.content': 'Содержимое',
            'templates.form.variablesHint': 'Используйте переменные в фигурных скобках, например: {date}, {chat_title}',
            'templates.form.preview': 'Предпросмотр',
            'templates.form.previewTitle': 'Предпросмотр:',
            'common.cancel': 'Отмена',
            'common.save': 'Сохранить',
            'nav.dashboard': 'Главная',
            'nav.groups': 'Группы',
            'nav.schedule': 'Расписание',
            'nav.history': 'История',
            'nav.statistics': 'Статистика',
            'nav.templates': 'Шаблоны',
            'nav.preview': 'Предпросмотр',
            'preview.selectGroup': 'Выберите группу для предпросмотра:',
            'preview.testGroup': 'Тестовая группа',
            'preview.update': 'Обновить предпросмотр',
            'preview.author': 'Вы',
            'preview.loading': 'Загрузка...',
            'preview.info': 'Длина текста:',
            'preview.chars': 'символов',
            'preview.usingTemplate': 'Используется шаблон:',
            'schedule.title': 'Расписание публикаций',
            'schedule.create': 'Создать расписание',
            'schedule.loading': 'Загрузка...',
            'schedule.empty': 'Нет расписаний',
            'schedule.active': 'Активно',
            'schedule.inactive': 'Неактивно',
            'schedule.minutes': 'минут',
            'schedule.created': 'Расписание создано',
            'schedule.updated': 'Расписание обновлено',
            'schedule.activated': 'Расписание активировано',
            'schedule.deleted': 'Расписание удалено',
            'schedule.confirmActivate': 'Активировать это расписание? Текущее активное расписание будет деактивировано.',
            'schedule.confirmDelete': 'Удалить это расписание?',
            'schedule.table.type': 'Тип',
            'schedule.table.details': 'Детали',
            'schedule.table.status': 'Статус',
            'schedule.table.created': 'Создано',
            'schedule.table.actions': 'Действия',
            'schedule.types.interval': 'Интервал',
            'schedule.types.time': 'Конкретное время',
            'schedule.types.days': 'Дни недели',
            'schedule.types.hours': 'Часовое окно',
            'schedule.form.type': 'Тип расписания',
            'schedule.form.intervalMinutes': 'Интервал (минуты)',
            'schedule.form.hour': 'Час',
            'schedule.form.minute': 'Минута',
            'schedule.form.days': 'Дни недели',
            'schedule.form.startHour': 'Начальный час',
            'schedule.form.endHour': 'Конечный час',
            'schedule.form.activate': 'Активировать сразу',
            'schedule.days.mon': 'Пн',
            'schedule.days.tue': 'Вт',
            'schedule.days.wed': 'Ср',
            'schedule.days.thu': 'Чт',
            'schedule.days.fri': 'Пт',
            'schedule.days.sat': 'Сб',
            'schedule.days.sun': 'Вс',
            'schedule.actions.activate': 'Активировать',
            'schedule.actions.delete': 'Удалить',
            'schedule.errors.invalidInterval': 'Неверный интервал',
            'schedule.errors.invalidTime': 'Неверное время',
            'schedule.errors.noDays': 'Выберите хотя бы один день недели',
            'schedule.errors.invalidHours': 'Неверное часовое окно',
            'status.unknown': 'Неизвестно',
            'error.unknown': 'Неизвестная ошибка',
            'error.unknownGroup': 'Неизвестно',
            'loading': 'Загрузка...',
            'unit.minutes': 'мин',
            'unit.hours': 'часов'
        },
        en: {
            'app.title': 'Post Publishing System',
            'connection.checking': 'Checking connection...',
            'connection.connected': 'Connected',
            'connection.disconnected': 'Disconnected',
            'status.groups': 'Groups',
            'status.interval': 'Interval',
            'status.scheduler': 'Scheduler',
            'status.nextPublication': 'Next Publication',
            'status.publication': 'Publication Status',
            'status.running': 'Running',
            'status.stopped': 'Stopped',
            'status.notActive': 'Not Active',
            'status.publishing': 'Publishing',
            'status.waiting': 'Waiting',
            'publication.details': 'Detailed Publication Status',
            'publication.currentStep': 'Current Step:',
            'publication.progress': 'Progress:',
            'publication.startTime': 'Start Time:',
            'publication.lastUpdate': 'Last Update:',
            'publication.errors': 'Errors:',
            'actions.quick': 'Quick Actions',
            'actions.publishNow': 'Publish Now',
            'actions.startScheduler': 'Start Scheduler',
            'actions.stop': 'Stop',
            'actions.reloadPost': 'Reload Post',
            'settings.title': 'Settings',
            'settings.interval': 'Publication Interval',
            'settings.set': 'Set',
            'settings.maxMinutes': 'Max: 10080 minutes (7 days). Min: 1 minute.',
            'groups.add': 'Add Group/Channel',
            'groups.input': 'Link, @username or ID',
            'groups.addButton': 'Add Group',
            'groups.list': 'Groups/Channels List',
            'groups.empty': 'No groups added',
            'groups.emptyDesc': 'Add a group or channel to get started',
            'groups.loading': 'Loading groups...',
            'groups.lastPost': 'Last publication:',
            'groups.delete': 'Delete group',
            'groups.deleteConfirm': 'Delete this group?',
            'groups.active': 'Active',
            'groups.disabled': 'Disabled',
            'groups.enable': 'Enable group',
            'groups.disable': 'Disable group',
            'groups.disabledSuccess': 'Group disabled',
            'groups.enabledSuccess': 'Group enabled',
            'toast.notification': 'Notification',
            'toast.enterGroup': 'Enter link, @username or group ID',
            'toast.maxInterval': 'Maximum interval: 10080 minutes (7 days)',
            'toast.invalidInterval': 'Enter a valid interval (greater than 0)',
            'toast.unknownUnit': 'Unknown unit',
            'toast.errorPublishing': 'Publishing error',
            'toast.errorStartScheduler': 'Error starting scheduler',
            'toast.errorStopScheduler': 'Error stopping scheduler',
            'toast.errorReloadPost': 'Error reloading post',
            'toast.errorAddGroup': 'Error adding group',
            'toast.errorToggleGroup': 'Error changing group status',
            'toast.errorSetInterval': 'Error setting interval',
            'toast.groupNotFound': 'Could not find chat. Make sure the chat exists and your account has access to it.',
            'toast.groupNotSpecified': 'Group identifier not specified',
            'toast.groupAlreadyAdded': 'Chat already added or an error occurred',
            'toast.groupDeleted': 'Group deleted',
            'toast.groupAdded': 'Group added',
            'toast.intervalNotSpecified': 'Interval not specified',
            'toast.invalidInterval': 'Invalid interval',
            'toast.maxIntervalError': 'Maximum interval: 10080 minutes (7 days)',
            'toast.intervalSet': 'Interval set',
            'toast.publicationStarted': 'Publication started',
            'toast.schedulerStarted': 'Scheduler started',
            'toast.schedulerStopped': 'Scheduler stopped',
            'toast.schedulerNotInitialized': 'Scheduler not initialized',
            'toast.postHandlerNotInitialized': 'Post handler not initialized',
            'toast.postReloaded': 'Post reloaded',
            'toast.statusReset': 'Publication status reset',
            'publication.completed': 'Completed',
            'publication.cancelled': 'Cancelled',
            'publication.completedSuccess': 'Publication completed successfully!',
            'publication.completedWithErrors': 'Publication completed with errors',
            'publication.criticalError': 'Critical error',
            'publication.initialization': 'Initialization',
            'publication.gettingGroups': 'Getting groups list...',
            'publication.publishing': 'Publishing to {total} groups',
            'publication.publishingGroup': 'Publishing to group {current}/{total}: {group}',
            'publication.groupSuccess': 'Group {current}/{total}: {group} - success',
            'publication.groupError': 'Group {current}/{total}: {group} - error',
            'publication.waiting': 'Waiting {seconds} seconds...',
            'publication.stopped': 'Publication stopped at group {current}/{total}',
            'groups.noTitle': 'No title',
            'groups.never': 'Never',
            'history.title': 'Publication History',
            'history.loading': 'Loading...',
            'history.empty': 'History is empty',
            'history.filters.status': 'Status',
            'history.filters.search': 'Search',
            'history.filters.dateFrom': 'From date',
            'history.filters.dateTo': 'To date',
            'history.filters.apply': 'Apply',
            'history.table.time': 'Time',
            'history.table.group': 'Group',
            'history.table.status': 'Status',
            'history.table.retries': 'Retries',
            'history.table.error': 'Error',
            'history.prev': 'Previous',
            'history.next': 'Next',
            'history.clear': 'Clear History',
            'history.clearConfirm': 'Are you sure you want to clear publication history?',
            'history.status.success': 'Success',
            'history.status.error': 'Error',
            'statistics.title': 'Publication Statistics',
            'statistics.total': 'Total Publications',
            'statistics.successful': 'Successful',
            'statistics.failed': 'Failed',
            'statistics.successRate': 'Success Rate',
            'statistics.topGroups': 'Top Groups',
            'statistics.dailyActivity': 'Daily Activity',
            'statistics.hourlyActivity': 'Hourly Activity',
            'statistics.publications': 'Publications',
            'statistics.noData': 'No data',
            'statistics.filterFrom': 'From date',
            'statistics.filterTo': 'To date',
            'statistics.filterApply': 'Apply',
            'templates.title': 'Post Templates',
            'templates.create': 'Create Template',
            'templates.loading': 'Loading...',
            'templates.empty': 'No templates',
            'templates.table.name': 'Name',
            'templates.table.content': 'Content',
            'templates.table.status': 'Status',
            'templates.table.actions': 'Actions',
            'templates.status.active': 'Active',
            'templates.status.inactive': 'Inactive',
            'templates.actions.edit': 'Edit',
            'templates.actions.activate': 'Activate',
            'templates.actions.delete': 'Delete',
            'templates.deleteConfirm': 'Are you sure you want to delete this template?',
            'templates.variables.title': 'Available Variables:',
            'templates.variables.date': 'current date',
            'templates.variables.time': 'current time',
            'templates.variables.datetime': 'date and time',
            'templates.variables.chatId': 'chat ID',
            'templates.variables.chatTitle': 'chat title',
            'templates.variables.random': 'random number (1-1000)',
            'templates.variables.randomRange': 'random number from min to max',
            'templates.form.name': 'Name',
            'templates.form.content': 'Content',
            'templates.form.variablesHint': 'Use variables in curly braces, e.g.: {date}, {chat_title}',
            'templates.form.preview': 'Preview',
            'templates.form.previewTitle': 'Preview:',
            'nav.dashboard': 'Dashboard',
            'nav.groups': 'Groups',
            'nav.schedule': 'Schedule',
            'nav.history': 'History',
            'nav.statistics': 'Statistics',
            'nav.templates': 'Templates',
            'nav.preview': 'Preview',
            'preview.selectGroup': 'Select group for preview:',
            'preview.testGroup': 'Test Group',
            'preview.update': 'Update Preview',
            'preview.author': 'You',
            'preview.loading': 'Loading...',
            'preview.info': 'Text length:',
            'preview.chars': 'characters',
            'preview.usingTemplate': 'Using template:',
            'schedule.title': 'Publication Schedule',
            'schedule.create': 'Create Schedule',
            'schedule.loading': 'Loading...',
            'schedule.empty': 'No schedules',
            'schedule.active': 'Active',
            'schedule.inactive': 'Inactive',
            'schedule.minutes': 'minutes',
            'schedule.created': 'Schedule created',
            'schedule.updated': 'Schedule updated',
            'schedule.activated': 'Schedule activated',
            'schedule.deleted': 'Schedule deleted',
            'schedule.confirmActivate': 'Activate this schedule? The current active schedule will be deactivated.',
            'schedule.confirmDelete': 'Delete this schedule?',
            'schedule.table.type': 'Type',
            'schedule.table.details': 'Details',
            'schedule.table.status': 'Status',
            'schedule.table.created': 'Created',
            'schedule.table.actions': 'Actions',
            'schedule.types.interval': 'Interval',
            'schedule.types.time': 'Specific Time',
            'schedule.types.days': 'Days of Week',
            'schedule.types.hours': 'Time Window',
            'schedule.form.type': 'Schedule Type',
            'schedule.form.intervalMinutes': 'Interval (minutes)',
            'schedule.form.hour': 'Hour',
            'schedule.form.minute': 'Minute',
            'schedule.form.days': 'Days of Week',
            'schedule.form.startHour': 'Start Hour',
            'schedule.form.endHour': 'End Hour',
            'schedule.form.activate': 'Activate Immediately',
            'schedule.days.mon': 'Mon',
            'schedule.days.tue': 'Tue',
            'schedule.days.wed': 'Wed',
            'schedule.days.thu': 'Thu',
            'schedule.days.fri': 'Fri',
            'schedule.days.sat': 'Sat',
            'schedule.days.sun': 'Sun',
            'schedule.actions.activate': 'Activate',
            'schedule.actions.delete': 'Delete',
            'schedule.errors.invalidInterval': 'Invalid interval',
            'schedule.errors.invalidTime': 'Invalid time',
            'schedule.errors.noDays': 'Select at least one day of week',
            'schedule.errors.invalidHours': 'Invalid time window',
            'status.unknown': 'Unknown',
            'error.unknown': 'Unknown error',
            'error.unknownGroup': 'Unknown',
            'loading': 'Loading...',
            'unit.minutes': 'min',
            'unit.hours': 'hours'
        }
    };
    
    // Текущий язык
    window.currentLanguage = localStorage.getItem('language') || 'ru';
    
    // Функция перевода
    window.t = function(key) {
        return window.translations[window.currentLanguage][key] || key;
    };
    
    // Безопасный fetch с обработкой ошибок авторизации
    window.safeFetch = async function(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            credentials: 'include'
        });
        
        if (response.status === 401) {
            window.handleAuthError(response);
            throw new Error('Unauthorized');
        }
        
        return response;
    };
    
    // Обработка ошибки авторизации
    window.handleAuthError = function(response) {
        if (response.status === 401) {
            window.location.href = '/login';
        }
    };
    
    // Функция выхода
    window.logout = async function() {
        try {
            const response = await fetch('/logout', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                window.location.href = '/login';
            } else {
                window.showToast(data.error || window.t('error.unknown'), 'error');
            }
        } catch (error) {
            console.error('Ошибка выхода:', error);
            window.location.href = '/login';
        }
    };
    
    // Показать toast уведомление
    window.showToast = function(message, type = 'info') {
        let toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }
        
        const toastId = 'toast-' + Date.now();
        const bgClass = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-info';
        
        const toastHTML = `
            <div id="${toastId}" class="toast ${bgClass} text-white" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header ${bgClass} text-white border-0">
                    <strong class="me-auto">${window.t('toast.notification')}</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${window.translateApiMessage(message)}
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 5000
        });
        
        toast.show();
        
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    };
    
    // Перевод сообщений от API
    window.translateApiMessage = function(message) {
        if (!message) return message;
        
        const messageMap = {
            'Группа добавлена': 'toast.groupAdded',
            'Чат удален': 'toast.groupDeleted',
            'Чат {id} удален': 'toast.groupDeleted',
            'Интервал установлен': 'toast.intervalSet',
            'Публикация запущена': 'toast.publicationStarted',
            'Планировщик запущен': 'toast.schedulerStarted',
            'Планировщик остановлен': 'toast.schedulerStopped',
            'Пост перезагружен': 'toast.postReloaded',
            'Статус публикации сброшен': 'toast.statusReset',
            'Не указан идентификатор группы': 'toast.groupNotSpecified',
            'Не удалось найти чат': 'toast.groupNotFound',
            'Чат уже добавлен или произошла ошибка': 'toast.groupAlreadyAdded',
            'Чат не найден или произошла ошибка': 'toast.groupNotFound',
            'Не указан интервал': 'toast.intervalNotSpecified',
            'Неверный интервал': 'toast.invalidInterval',
            'Максимальный интервал: 10080 минут (7 дней)': 'toast.maxIntervalError',
            'Ошибка установки интервала': 'toast.errorSetInterval',
            'Планировщик не инициализирован': 'toast.schedulerNotInitialized',
            'Обработчик постов не инициализирован': 'toast.postHandlerNotInitialized'
        };
        
        for (const [key, translationKey] of Object.entries(messageMap)) {
            if (message.includes(key)) {
                if (window.currentLanguage === 'en') {
                    return window.t(translationKey);
                }
                return window.currentLanguage === 'ru' ? message : window.t(translationKey);
            }
        }
        
        return message;
    };
    
    // Форматирование текста для Telegram
    window.formatTelegramText = function(text) {
        if (!text) return '';
        
        let formatted = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/&lt;b&gt;(.*?)&lt;\/b&gt;/g, '<strong>$1</strong>')
            .replace(/&lt;i&gt;(.*?)&lt;\/i&gt;/g, '<em>$1</em>')
            .replace(/&lt;code&gt;(.*?)&lt;\/code&gt;/g, '<code>$1</code>')
            .replace(/&lt;a href="([^"]+)"&gt;(.*?)&lt;\/a&gt;/g, '<a href="$1" target="_blank">$2</a>')
            .replace(/\n/g, '<br>');
        
        return formatted;
    };
    
    // Установка состояния загрузки кнопки
    window.setButtonLoading = function(button, loading) {
        if (loading) {
            button.disabled = true;
            if (!button.getAttribute('data-original-text')) {
                button.setAttribute('data-original-text', button.innerHTML);
            }
            const loadingText = window.t('loading');
            button.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${loadingText}`;
        } else {
            button.disabled = false;
            const originalText = button.getAttribute('data-original-text');
            if (originalText) {
                button.innerHTML = originalText;
                button.removeAttribute('data-original-text');
                window.updateButtonTranslations(button);
            }
        }
    };
    
    // Обновление переводов в кнопке
    window.updateButtonTranslations = function(button) {
        const i18nElements = button.querySelectorAll('[data-i18n]');
        i18nElements.forEach(element => {
            const key = element.getAttribute('data-i18n');
            if (window.translations[window.currentLanguage] && window.translations[window.currentLanguage][key]) {
                element.textContent = window.translations[window.currentLanguage][key];
            }
        });
    };
})();
