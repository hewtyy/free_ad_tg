// Dashboard module - функции для работы с главной панелью

// Загрузка статуса
async function loadStatus() {
    try {
        console.log('Loading status...');
        const response = await window.safeFetch('/api/status');
        const data = await response.json();
        
        console.log('Status response:', response.ok, data);
        
        if (response.ok) {
            updateStatus(data);
        } else {
            console.error('Ошибка загрузки статуса:', data.error);
            // Показываем ошибку пользователю
            const statusElements = ['groupsCount', 'interval', 'schedulerStatus', 'nextRun', 'publicationStatus'];
            statusElements.forEach(id => {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = '-';
                }
            });
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error('Ошибка загрузки статуса:', error);
            // Показываем ошибку пользователю
            const statusElements = ['groupsCount', 'interval', 'schedulerStatus', 'nextRun', 'publicationStatus'];
            statusElements.forEach(id => {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = '-';
                }
            });
        }
    }
}

// Обновление статуса на странице
function updateStatus(data) {
    // Telegram статус
    const telegramStatus = document.getElementById('telegramStatus');
    const telegramStatusText = document.getElementById('telegramStatusText');
    
    if (data.telegram_connected) {
        telegramStatus.className = 'telegram-status telegram-connected';
        telegramStatusText.textContent = window.t('connection.connected');
    } else {
        telegramStatus.className = 'telegram-status telegram-disconnected';
        telegramStatusText.textContent = window.t('connection.disconnected');
    }
    
    // Статистика
    document.getElementById('groupsCount').textContent = data.groups_count;
    
    // Форматируем интервал на клиенте с учетом языка
    const intervalElement = document.getElementById('interval');
    if (data.interval_minutes !== undefined) {
        const intervalMinutes = data.interval_minutes;
        let intervalText;
        if (window.currentLanguage === 'en') {
            if (intervalMinutes < 60) {
                intervalText = `${intervalMinutes} min`;
            } else if (intervalMinutes === 60) {
                intervalText = "1 hour";
            } else {
                const hours = Math.floor(intervalMinutes / 60);
                const minutes = intervalMinutes % 60;
                if (minutes > 0) {
                    intervalText = `${hours}h ${minutes}m`;
                } else {
                    intervalText = `${hours} hours`;
                }
            }
        } else {
            if (intervalMinutes < 60) {
                intervalText = `${intervalMinutes} мин`;
            } else if (intervalMinutes === 60) {
                intervalText = "1 час";
            } else {
                const hours = Math.floor(intervalMinutes / 60);
                const minutes = intervalMinutes % 60;
                if (minutes > 0) {
                    intervalText = `${hours}ч ${minutes}м`;
                } else {
                    intervalText = `${hours}ч`;
                }
            }
        }
        intervalElement.textContent = intervalText;
    } else {
        intervalElement.textContent = data.interval;
    }
    
    // Обновляем поля ввода интервала только если они пустые
    const intervalInput = document.getElementById('intervalInput');
    const intervalUnit = document.getElementById('intervalUnit');
    if (intervalInput && (!intervalInput.value || intervalInput.value === '24')) {
        const intervalMinutes = data.interval_minutes || 1440;
        if (intervalMinutes < 60) {
            intervalInput.value = intervalMinutes;
            intervalUnit.value = 'minutes';
        } else {
            const hours = Math.floor(intervalMinutes / 60);
            intervalInput.value = hours;
            intervalUnit.value = 'hours';
        }
    }
    
    // Планировщик
    const schedulerStatus = document.getElementById('schedulerStatus');
    // Используем текущий язык для перевода статуса
    schedulerStatus.textContent = data.scheduler_status === 'Запущен' ? window.t('status.running') : window.t('status.stopped');
    schedulerStatus.className = 'badge ' + (data.scheduler_status === 'Запущен' ? 'bg-success' : 'bg-secondary');
    
    // Следующая публикация
    const nextRunElement = document.getElementById('nextRun');
    if (data.next_run) {
        nextRunElement.textContent = data.next_run;
    } else {
        nextRunElement.textContent = window.t('status.unknown');
    }
    
    // Статус публикации
    if (data.publication_status) {
        console.log('Publication status received:', data.publication_status);
        updatePublicationStatus(data.publication_status);
    } else {
        console.log('No publication status in data');
        updatePublicationStatus(null);
    }
}

// Обновление статуса публикации
function updatePublicationStatus(publicationStatus) {
    console.log('updatePublicationStatus called with:', publicationStatus);
    
    if (!publicationStatus) {
        const statusElement = document.getElementById('publicationStatus');
        const panel = document.getElementById('publicationStatusPanel');
        
        if (statusElement) {
            statusElement.textContent = window.t('status.notActive');
            statusElement.className = 'badge bg-secondary';
        }
        if (panel) {
            panel.style.display = 'none';
        }
        return;
    }
    
    const statusElement = document.getElementById('publicationStatus');
    const panel = document.getElementById('publicationStatusPanel');
    
    console.log('Status element found:', !!statusElement);
    console.log('Panel element found:', !!panel);
    
    if (!statusElement || !panel) {
        console.error('Publication status elements not found');
        return;
    }
    
    if (publicationStatus.is_publishing) {
        console.log('Setting publishing status');
        statusElement.textContent = window.t('status.publishing');
        statusElement.className = 'badge bg-warning';
        panel.style.display = 'block';
        
        // Обновляем детальную информацию
        const currentStepElement = document.getElementById('currentStep');
        if (currentStepElement) {
            // Переводим текущий этап публикации
            let stepText = publicationStatus.current_step || '-';
            
            // Переводим известные статусы
            if (stepText === 'Завершено' || stepText === 'Completed') {
                stepText = window.t('publication.completed');
            } else if (stepText === 'Прервано' || stepText === 'Cancelled') {
                stepText = window.t('publication.cancelled');
            } else if (stepText === 'Публикация завершена успешно!' || stepText.includes('completed successfully')) {
                stepText = window.t('publication.completedSuccess');
            } else if (stepText.includes('завершена с ошибками') || stepText.includes('completed with errors')) {
                stepText = window.t('publication.completedWithErrors');
            } else if (stepText.includes('Критическая ошибка') || stepText.includes('Critical error')) {
                stepText = window.t('publication.criticalError');
            } else if (stepText === 'Инициализация' || stepText === 'Initialization') {
                stepText = window.t('publication.initialization');
            } else if (stepText.includes('Получение списка групп') || stepText.includes('Getting groups')) {
                stepText = window.t('publication.gettingGroups');
            } else if (stepText.includes('Публикация в') && stepText.includes('групп')) {
                // Парсим "Публикация в 3 групп" или "Publishing to 3 groups"
                const match = stepText.match(/(\d+)/);
                if (match) {
                    stepText = window.t('publication.publishing').replace('{total}', match[1]);
                }
            } else if (stepText.includes('Ожидание') || stepText.includes('Waiting')) {
                // Парсим "Ожидание 49 секунд..." или "Waiting 49 seconds..."
                const match = stepText.match(/(\d+)/);
                if (match) {
                    stepText = window.t('publication.waiting').replace('{seconds}', match[1]);
                }
            }
            
            currentStepElement.textContent = stepText;
        }
        
        // Прогресс
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        if (progressBar && progressText) {
            const progressPercent = publicationStatus.progress_percent || 0;
            
            progressBar.style.width = progressPercent + '%';
            progressBar.className = 'progress-bar ' + (progressPercent === 100 ? 'bg-success' : 'bg-primary');
            progressBar.setAttribute('aria-valuenow', progressPercent);
            progressBar.setAttribute('aria-valuemin', 0);
            progressBar.setAttribute('aria-valuemax', 100);
            
            const completed = publicationStatus.completed_groups || 0;
            const total = publicationStatus.total_groups || 0;
            progressText.textContent = `${progressPercent.toFixed(1)}% (${completed}/${total})`;
            
            console.log(`Progress updated: ${progressPercent}% (${completed}/${total})`);
        } else {
            console.error('Progress elements not found');
        }
        
        // Время
        const startTimeElement = document.getElementById('startTime');
        const lastUpdateElement = document.getElementById('lastUpdate');
        
        if (startTimeElement) {
            startTimeElement.textContent = publicationStatus.start_time_str || '-';
        }
        if (lastUpdateElement) {
            lastUpdateElement.textContent = publicationStatus.last_update_str || '-';
        }
        
        // Ошибки
        const errorsSection = document.getElementById('errorsSection');
        const errorsList = document.getElementById('errorsList');
        
        if (errorsSection && errorsList) {
            if (publicationStatus.errors && publicationStatus.errors.length > 0) {
                errorsSection.style.display = 'block';
                errorsList.innerHTML = '';
                
                publicationStatus.errors.forEach(error => {
                    const errorItem = document.createElement('div');
                    errorItem.className = 'list-group-item list-group-item-danger';
                    errorItem.innerHTML = `
                        <div class="d-flex w-100 justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1"><i class="fas fa-exclamation-circle me-2"></i>${error.group || window.t('error.unknownGroup')}</h6>
                                <p class="mb-1">${error.error || window.t('error.unknown')}</p>
                            </div>
                            <small class="text-muted">${error.time ? new Date(error.time).toLocaleTimeString() : ''}</small>
                        </div>
                    `;
                    errorsList.appendChild(errorItem);
                });
            } else {
                errorsSection.style.display = 'none';
            }
        }
        
    } else {
        console.log('Setting non-publishing status');
        statusElement.textContent = window.t('status.waiting');
        statusElement.className = 'badge bg-success';
        panel.style.display = 'none';
    }
}

// Экспортируем функции в глобальную область видимости
window.loadStatus = loadStatus;
window.updateStatus = updateStatus;
window.updatePublicationStatus = updatePublicationStatus;

