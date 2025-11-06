// Scheduler module - функции для работы с планировщиком

// Установка интервала
async function setIntervalValue() {
    const intervalInput = document.getElementById('intervalInput');
    const intervalUnit = document.getElementById('intervalUnit');
    const setIntervalBtn = document.getElementById('setIntervalBtn');
    
    if (!intervalInput.value.trim()) {
        window.showToast(window.t('toast.intervalNotSpecified'), 'warning');
        return;
    }
    
    let minutes = parseInt(intervalInput.value.trim());
    const unit = intervalUnit.value;

    if (unit === 'hours') {
        minutes *= 60;
    }

    if (isNaN(minutes) || minutes <= 0) {
        window.showToast(window.t('toast.invalidInterval'), 'warning');
        return;
    }

    if (minutes > 10080) {
        window.showToast(window.t('toast.maxInterval'), 'warning');
        return;
    }
    
    window.setButtonLoading(setIntervalBtn, true);

    try {
        const response = await window.safeFetch('/api/set_interval', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                interval_minutes: minutes
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            window.showToast(data.message, 'success');
            window.loadStatus();
        } else {
            window.showToast(data.error, 'error');
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            window.showToast(window.t('toast.errorSetInterval'), 'error');
        }
    } finally {
        window.setButtonLoading(setIntervalBtn, false);
    }
}

// Публикация сейчас
async function postNow() {
    const postNowBtn = document.getElementById('postNowBtn');
    window.setButtonLoading(postNowBtn, true);
    try {
        const response = await window.safeFetch('/api/post_now', {
            method: 'POST'
        });
        const data = await response.json();
        if (response.ok) {
            window.showToast(data.message, 'success');
            window.loadStatus();
        } else {
            window.showToast(data.error, 'error');
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            window.showToast(window.t('toast.errorPublishing'), 'error');
        }
    } finally {
        window.setButtonLoading(postNowBtn, false);
    }
}

// Запуск планировщика
async function startScheduler() {
    const startSchedulerBtn = document.getElementById('startSchedulerBtn');
    window.setButtonLoading(startSchedulerBtn, true);
    try {
        const response = await window.safeFetch('/api/start_scheduler', {
            method: 'POST'
        });
        const data = await response.json();
        if (response.ok) {
            window.showToast(data.message, 'success');
            window.loadStatus();
        } else {
            window.showToast(data.error, 'error');
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            window.showToast(window.t('toast.errorStartScheduler'), 'error');
        }
    } finally {
        window.setButtonLoading(startSchedulerBtn, false);
    }
}

// Остановка планировщика
async function stopScheduler() {
    const stopSchedulerBtn = document.getElementById('stopSchedulerBtn');
    window.setButtonLoading(stopSchedulerBtn, true);
    try {
        const response = await window.safeFetch('/api/stop_scheduler', {
            method: 'POST'
        });
        const data = await response.json();
        if (response.ok) {
            window.showToast(data.message, 'success');
            window.loadStatus();
        } else {
            window.showToast(data.error, 'error');
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            window.showToast(window.t('toast.errorStopScheduler'), 'error');
        }
    } finally {
        window.setButtonLoading(stopSchedulerBtn, false);
    }
}

// Перезагрузка поста
async function reloadPost() {
    const reloadPostBtn = document.getElementById('reloadPostBtn');
    window.setButtonLoading(reloadPostBtn, true);
    try {
        const response = await window.safeFetch('/api/reload_post', {
            method: 'POST'
        });
        const data = await response.json();
        if (response.ok) {
            window.showToast(data.message, 'success');
        } else {
            window.showToast(data.error, 'error');
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            window.showToast(window.t('toast.errorReloadPost'), 'error');
        }
    } finally {
        window.setButtonLoading(reloadPostBtn, false);
    }
}

// Загрузка расписаний
async function loadSchedules() {
    console.log('loadSchedules: Function called');
    
    const tbody = document.getElementById('schedulesList');
    console.log('loadSchedules: tbody element:', tbody);
    
    if (!tbody) {
        console.error('schedulesList element not found');
        return;
    }
    
    console.log('loadSchedules: Starting to load schedules...');
    tbody.innerHTML = '<tr><td colspan="5" class="text-center"><i class="fas fa-spinner fa-spin"></i> ' + window.t('schedule.loading') + '</td></tr>';
    
    try {
        console.log('loadSchedules: Fetching /api/schedules...');
        const response = await window.safeFetch('/api/schedules');
        console.log('loadSchedules: Response status:', response.status, response.ok);
        
        const data = await response.json();
        console.log('loadSchedules: Response data:', data);
        
        if (response.ok && data.success) {
            console.log('loadSchedules: Success, schedules count:', data.schedules ? data.schedules.length : 0);
            if (data.schedules.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center">' + window.t('schedule.empty') + '</td></tr>';
            } else {
                const html = data.schedules.map(schedule => {
                    let details = '';
                    const scheduleData = schedule.schedule_data;
                    
                    if (schedule.schedule_type === 'interval') {
                        const minutes = scheduleData.minutes || 1440;
                        if (minutes < 60) {
                            details = `${minutes} ${window.t('schedule.minutes')}`;
                        } else {
                            const hours = Math.floor(minutes / 60);
                            const mins = minutes % 60;
                            details = mins > 0 ? `${hours}ч ${mins}м` : `${hours}ч`;
                        }
                    } else if (schedule.schedule_type === 'time') {
                        const hour = String(scheduleData.hour || 12).padStart(2, '0');
                        const minute = String(scheduleData.minute || 0).padStart(2, '0');
                        details = `${hour}:${minute}`;
                    } else if (schedule.schedule_type === 'days') {
                        const dayNames = [window.t('schedule.days.mon'), window.t('schedule.days.tue'), window.t('schedule.days.wed'), window.t('schedule.days.thu'), window.t('schedule.days.fri'), window.t('schedule.days.sat'), window.t('schedule.days.sun')];
                        const days = scheduleData.days || [];
                        const dayList = days.map(d => dayNames[d]).join(', ');
                        const hour = String(scheduleData.hour || 12).padStart(2, '0');
                        const minute = String(scheduleData.minute || 0).padStart(2, '0');
                        details = `${dayList} в ${hour}:${minute}`;
                    } else if (schedule.schedule_type === 'hours') {
                        const startHour = String(scheduleData.start_hour || 9).padStart(2, '0');
                        const endHour = String(scheduleData.end_hour || 18).padStart(2, '0');
                        const interval = scheduleData.interval_minutes || 60;
                        details = `${startHour}:00 - ${endHour}:00 (${interval} ${window.t('schedule.minutes')})`;
                    }
                
                const typeNames = {
                    'interval': window.t('schedule.types.interval'),
                    'time': window.t('schedule.types.time'),
                    'days': window.t('schedule.types.days'),
                    'hours': window.t('schedule.types.hours')
                };
                
                return `
                    <tr>
                        <td>${typeNames[schedule.schedule_type] || schedule.schedule_type}</td>
                        <td>${details}</td>
                        <td>
                            ${schedule.is_active 
                                ? '<span class="badge bg-success">' + window.t('schedule.active') + '</span>' 
                                : '<span class="badge bg-secondary">' + window.t('schedule.inactive') + '</span>'}
                        </td>
                        <td>${schedule.created_at}</td>
                        <td>
                            ${!schedule.is_active 
                                ? `<button class="btn btn-sm btn-success" onclick="activateSchedule(${schedule.id})">
                                    <i class="fas fa-check"></i> <span data-i18n="schedule.actions.activate">Активировать</span>
                                   </button>` 
                                : ''}
                            <button class="btn btn-sm btn-danger" onclick="deleteSchedule(${schedule.id})">
                                <i class="fas fa-trash"></i> <span data-i18n="schedule.actions.delete">Удалить</span>
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
            
            tbody.innerHTML = html;
            console.log('loadSchedules: HTML updated, schedules rendered');
            
            // Обновляем переводы
            if (typeof updateDynamicTexts === 'function') {
                updateDynamicTexts();
            }
            }
        } else {
            console.error('loadSchedules: Response not OK or missing success flag', {
                ok: response.ok,
                success: data.success,
                error: data.error
            });
            const schedulesList = document.getElementById('schedulesList');
            if (schedulesList) {
                schedulesList.innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center text-danger">
                            ${data.error || window.t('error.unknown')}
                        </td>
                    </tr>
                `;
            }
        }
    } catch (error) {
        console.error('Error loading schedules:', error);
        const schedulesList = document.getElementById('schedulesList');
        if (schedulesList) {
            schedulesList.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-danger">
                        ${window.t('error.unknown')}: ${error.message}
                    </td>
                </tr>
            `;
        }
    }
};

// Сброс формы расписания
function resetScheduleForm() {
    document.getElementById('scheduleId').value = '';
    document.getElementById('scheduleType').value = 'interval';
    document.getElementById('intervalMinutes').value = '1440';
    document.getElementById('timeHour').value = '12';
    document.getElementById('timeMinute').value = '0';
    document.getElementById('daysHour').value = '12';
    document.getElementById('daysMinute').value = '0';
    document.getElementById('hoursStart').value = '9';
    document.getElementById('hoursEnd').value = '18';
    document.getElementById('hoursInterval').value = '60';
    document.getElementById('scheduleActive').checked = false;
    
    // Сбрасываем чекбоксы дней недели
    document.querySelectorAll('.schedule-day-checkbox').forEach(cb => cb.checked = false);
    
    // Показываем правильные поля
    updateScheduleTypeFields();
}

// Обновление полей формы в зависимости от типа расписания
function updateScheduleTypeFields() {
    const type = document.getElementById('scheduleType').value;
    
    // Скрываем все поля
    document.querySelectorAll('.schedule-type-fields').forEach(field => {
        field.style.display = 'none';
    });
    
    // Показываем нужные поля
    if (type === 'interval') {
        document.getElementById('scheduleIntervalFields').style.display = 'block';
    } else if (type === 'time') {
        document.getElementById('scheduleTimeFields').style.display = 'block';
    } else if (type === 'days') {
        document.getElementById('scheduleDaysFields').style.display = 'block';
    } else if (type === 'hours') {
        document.getElementById('scheduleHoursFields').style.display = 'block';
    }
}

// Сохранение расписания
async function saveSchedule() {
    const id = document.getElementById('scheduleId').value;
    const type = document.getElementById('scheduleType').value;
    const isActive = document.getElementById('scheduleActive').checked;
    
    let scheduleData = {};
    
    if (type === 'interval') {
        const minutes = parseInt(document.getElementById('intervalMinutes').value);
        if (!minutes || minutes < 1) {
            window.showToast(window.t('schedule.errors.invalidInterval'), 'error');
            return;
        }
        scheduleData = { minutes };
    } else if (type === 'time') {
        const hour = parseInt(document.getElementById('timeHour').value);
        const minute = parseInt(document.getElementById('timeMinute').value);
        if (hour < 0 || hour > 23 || minute < 0 || minute > 59) {
            window.showToast(window.t('schedule.errors.invalidTime'), 'error');
            return;
        }
        scheduleData = { hour, minute };
    } else if (type === 'days') {
        const days = Array.from(document.querySelectorAll('.schedule-day-checkbox:checked')).map(cb => parseInt(cb.value));
        if (days.length === 0) {
            window.showToast(window.t('schedule.errors.noDays'), 'error');
            return;
        }
        const hour = parseInt(document.getElementById('daysHour').value);
        const minute = parseInt(document.getElementById('daysMinute').value);
        if (hour < 0 || hour > 23 || minute < 0 || minute > 59) {
            window.showToast(window.t('schedule.errors.invalidTime'), 'error');
            return;
        }
        scheduleData = { days, hour, minute };
    } else if (type === 'hours') {
        const startHour = parseInt(document.getElementById('hoursStart').value);
        const endHour = parseInt(document.getElementById('hoursEnd').value);
        const intervalMinutes = parseInt(document.getElementById('hoursInterval').value);
        if (startHour < 0 || startHour > 23 || endHour < 0 || endHour > 23 || startHour >= endHour) {
            window.showToast(window.t('schedule.errors.invalidHours'), 'error');
            return;
        }
        if (intervalMinutes < 1 || intervalMinutes > 1440) {
            window.showToast(window.t('schedule.errors.invalidInterval'), 'error');
            return;
        }
        scheduleData = { start_hour: startHour, end_hour: endHour, interval_minutes: intervalMinutes };
    }
    
    try {
        let response;
        if (id) {
            // Обновление
            response = await window.safeFetch(`/api/schedules/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    schedule_type: type,
                    schedule_data: scheduleData,
                    is_active: isActive
                })
            });
        } else {
            // Создание
            response = await window.safeFetch('/api/schedules', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    schedule_type: type,
                    schedule_data: scheduleData,
                    is_active: isActive
                })
            });
        }
        
        const data = await response.json();
        
        if (response.ok) {
            window.showToast(data.message, 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('scheduleModal'));
            modal.hide();
            loadSchedules();
        } else {
            window.showToast(data.error || window.t('error.unknown'), 'error');
        }
    } catch (error) {
        window.showToast(window.t('error.unknown'), 'error');
    }
}

// Активация расписания
async function activateSchedule(id) {
    if (!confirm(window.t('schedule.confirmActivate'))) {
        return;
    }
    try {
        const response = await window.safeFetch(`/api/schedules/${id}/activate`, {
            method: 'POST'
        });
        const data = await response.json();
        if (response.ok) {
            window.showToast(data.message, 'success');
            loadSchedules();
            window.loadStatus();
        } else {
            window.showToast(data.error, 'error');
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            window.showToast(window.t('error.unknown'), 'error');
        }
    }
}

// Удаление расписания
async function deleteSchedule(id) {
    if (!confirm(window.t('schedule.confirmDelete'))) {
        return;
    }
    try {
        const response = await window.safeFetch(`/api/schedules/${id}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (response.ok) {
            window.showToast(data.message, 'success');
            loadSchedules();
            window.loadStatus();
        } else {
            window.showToast(data.error, 'error');
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            window.showToast(window.t('error.unknown'), 'error');
        }
    }
}

// Экспортируем функции в глобальную область видимости
window.setIntervalValue = setIntervalValue;
window.postNow = postNow;
window.startScheduler = startScheduler;
window.stopScheduler = stopScheduler;
window.reloadPost = reloadPost;
window.loadSchedules = loadSchedules;
window.saveSchedule = saveSchedule;
window.activateSchedule = activateSchedule;
window.deleteSchedule = deleteSchedule;
window.resetScheduleForm = resetScheduleForm;
window.updateScheduleTypeFields = updateScheduleTypeFields;

