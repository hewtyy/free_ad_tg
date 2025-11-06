// Groups module - функции для работы с группами

// Загрузка списка групп
async function loadGroups() {
    try {
        const response = await window.safeFetch('/api/groups');
        const data = await response.json();
        
        if (response.ok) {
            // API возвращает объект с ключом 'groups' или массив напрямую
            const groups = data.groups || (Array.isArray(data) ? data : []);
            updateGroupsList(groups);
        } else {
            console.error('Ошибка загрузки групп:', data.error);
            const groupsList = document.getElementById('groupsList');
            if (groupsList) {
                groupsList.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-exclamation-triangle text-warning"></i>
                        <p>${window.t('groups.error') || 'Ошибка загрузки групп'}</p>
                        <small>${data.error || ''}</small>
                    </div>
                `;
            }
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error('Ошибка загрузки групп:', error);
            const groupsList = document.getElementById('groupsList');
            if (groupsList) {
                groupsList.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-exclamation-triangle text-danger"></i>
                        <p>${window.t('groups.error') || 'Ошибка загрузки групп'}</p>
                    </div>
                `;
            }
        }
    }
}

// Обновление списка групп
function updateGroupsList(groups) {
    const groupsList = document.getElementById('groupsList');
    
    // Проверяем, изменились ли данные
    const groupsString = JSON.stringify(groups.map(g => ({
        id: g.id,
        title: g.title,
        username: g.username,
        last_post: g.last_post,
        is_disabled: g.is_disabled
    })));
    
    if (window.lastGroupsData === groupsString) {
        // Данные не изменились, не обновляем DOM
        return;
    }
    
    // Сохраняем новые данные
    window.lastGroupsData = groupsString;
    
    if (groups.length === 0) {
        groupsList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>${window.t('groups.empty')}</p>
                <small>${window.t('groups.emptyDesc')}</small>
            </div>
        `;
        return;
    }
    
    let html = '';
    groups.forEach((group, index) => {
        const isDisabled = group.is_disabled === true || group.is_disabled === 1;
        const statusBadge = isDisabled 
            ? `<span class="badge bg-danger ms-2"><i class="fas fa-ban me-1"></i>${window.t('groups.disabled')}</span>`
            : `<span class="badge bg-success ms-2"><i class="fas fa-check me-1"></i>${window.t('groups.active')}</span>`;
        
        html += `
            <div class="group-item fade-in ${isDisabled ? 'disabled-group' : ''}" style="animation-delay: ${index * 0.1}s">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                            <h6 class="mb-2">
                            <i class="fas fa-users me-2 text-primary"></i>${group.title || window.t('groups.noTitle')}${statusBadge}
                        </h6>
                        <div class="d-flex flex-wrap gap-3 mb-2">
                            <small class="text-muted">
                                <i class="fas fa-hashtag me-1"></i>ID: ${group.id}
                            </small>
                            ${group.username ? `<small class="text-muted"><i class="fas fa-at me-1"></i>${group.username}</small>` : ''}
                        </div>
                        <small class="text-muted d-block">
                            <i class="fas fa-clock me-1"></i><span data-i18n-key="groups.lastPost">${window.t('groups.lastPost')}</span> <strong>${group.last_post || window.t('groups.never')}</strong>
                        </small>
                    </div>
                    <div class="d-flex gap-2">
                        <button class="btn btn-sm ${isDisabled ? 'btn-success' : 'btn-warning'}" 
                                onclick="toggleGroupDisabled('${group.id}', ${!isDisabled})" 
                                title="${isDisabled ? window.t('groups.enable') : window.t('groups.disable')}">
                            <i class="fas ${isDisabled ? 'fa-check' : 'fa-ban'}"></i>
                        </button>
                        <button class="btn btn-outline-danger btn-sm" onclick="removeGroup('${group.id}')" title="${window.t('groups.delete')}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    
    groupsList.innerHTML = html;
}

// Добавление группы
async function addGroup() {
    const groupInput = document.getElementById('groupInput');
    const addBtn = document.getElementById('addGroupBtn');
    
    if (!groupInput.value.trim()) {
        window.showToast(window.t('toast.enterGroup'), 'warning');
        return;
    }
    
    window.setButtonLoading(addBtn, true);
    
    try {
        const response = await window.safeFetch('/api/groups', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                group_input: groupInput.value.trim()
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            window.showToast(data.message, 'success');
            groupInput.value = '';
            // Сбрасываем кэш, чтобы принудительно обновить список
            window.lastGroupsData = null;
            loadGroups();
            window.loadStatus();
        } else {
            window.showToast(data.error, 'error');
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            window.showToast(window.t('toast.errorAddGroup'), 'error');
        }
    } finally {
        window.setButtonLoading(addBtn, false);
    }
}

// Удаление группы
async function removeGroup(chatId) {
    if (!confirm(window.t('groups.deleteConfirm'))) {
        return;
    }
    try {
        const response = await window.safeFetch(`/api/groups/${chatId}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (response.ok) {
            window.showToast(data.message, 'success');
            window.lastGroupsData = null;
            loadGroups();
            window.loadStatus();
        } else {
            window.showToast(data.error, 'error');
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            window.showToast(window.t('toast.errorAddGroup'), 'error');
        }
    }
}

// Переключение статуса группы
async function toggleGroupDisabled(chatId, isDisabled) {
    try {
        const response = await window.safeFetch(`/api/groups/${chatId}/toggle-disabled`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                is_disabled: !isDisabled
            })
        });
        const data = await response.json();
        if (response.ok) {
            window.showToast(data.message, 'success');
            window.lastGroupsData = null;
            loadGroups();
        } else {
            window.showToast(data.error, 'error');
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            window.showToast(window.t('toast.errorToggleGroup'), 'error');
        }
    }
}

// Экспортируем функции в глобальную область видимости
window.loadGroups = loadGroups;
window.updateGroupsList = updateGroupsList;
window.addGroup = addGroup;
window.removeGroup = removeGroup;
window.toggleGroupDisabled = toggleGroupDisabled;

