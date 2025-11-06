// Templates module - функции для работы с шаблонами постов

// Загрузка шаблонов
async function loadTemplates() {
    console.log('loadTemplates() called');
    const tbody = document.getElementById('templatesTableBody');
    if (!tbody) {
        console.error('templatesTableBody element not found');
        return;
    }
    console.log('templatesTableBody found');
    
    tbody.innerHTML = '<tr><td colspan="4" class="text-center"><i class="fas fa-spinner fa-spin"></i> ' + window.t('templates.loading') + '</td></tr>';
    
    try {
        console.log('Fetching templates from: /api/templates');
        const response = await window.safeFetch('/api/templates');
        const data = await response.json();
        console.log('Templates response:', response.ok, data);
        console.log('Templates data structure:', {
            success: data.success,
            templatesLength: data.templates?.length,
            templates: data.templates
        });
        
        if (response.ok && data.success) {
            if (data.templates.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center">' + window.t('templates.empty') + '</td></tr>';
                console.log('Templates: Empty list, showing empty message');
                
                // Убеждаемся, что таблица видима даже для пустого списка
                const templatesTable = tbody.closest('table');
                if (templatesTable) {
                    templatesTable.style.display = 'table';
                    templatesTable.style.visibility = 'visible';
                }
                tbody.style.display = 'table-row-group';
                tbody.style.visibility = 'visible';
            } else {
                const html = data.templates.map(template => {
                    const statusBadge = template.is_active 
                        ? '<span class="badge bg-success">' + window.t('templates.status.active') + '</span>'
                        : '<span class="badge bg-secondary">' + window.t('templates.status.inactive') + '</span>';
                    
                    const contentPreview = template.content.length > 50 
                        ? template.content.substring(0, 50) + '...' 
                        : template.content;
                    
                    return `
                        <tr>
                            <td><strong>${template.name}</strong></td>
                            <td><code>${contentPreview}</code></td>
                            <td>${statusBadge}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-primary me-1" onclick="editTemplate(${template.id}, '${template.name.replace(/'/g, "\\'")}', '${template.content.replace(/'/g, "\\'").replace(/\n/g, '\\n')}')">
                                    <i class="fas fa-edit"></i> ${window.t('templates.actions.edit')}
                                </button>
                                ${!template.is_active ? `
                                    <button class="btn btn-sm btn-outline-success me-1" onclick="activateTemplate(${template.id})">
                                        <i class="fas fa-check"></i> ${window.t('templates.actions.activate')}
                                    </button>
                                ` : ''}
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteTemplate(${template.id})">
                                    <i class="fas fa-trash"></i> ${window.t('templates.actions.delete')}
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
                console.log('Templates: Inserting HTML into tbody, length:', html.length);
                tbody.innerHTML = html;
                console.log('Templates: HTML inserted, tbody.innerHTML length:', tbody.innerHTML.length);
                
                // Проверяем видимость таблицы
                const templatesTable = tbody.closest('table');
                const templatesTab = tbody.closest('.tab-pane');
                console.log('Templates: Table visibility:', {
                    tableExists: !!templatesTable,
                    tabExists: !!templatesTab,
                    tabHasShow: templatesTab?.classList.contains('show'),
                    tabHasActive: templatesTab?.classList.contains('active'),
                    tabDisplay: templatesTab ? window.getComputedStyle(templatesTab).display : 'N/A',
                    tabOpacity: templatesTab ? window.getComputedStyle(templatesTab).opacity : 'N/A',
                    tableDisplay: templatesTable ? window.getComputedStyle(templatesTable).display : 'N/A'
                });
                
                // Убеждаемся, что таблица видима
                if (templatesTable) {
                    templatesTable.style.display = 'table';
                    templatesTable.style.visibility = 'visible';
                }
                tbody.style.display = 'table-row-group';
                tbody.style.visibility = 'visible';
            }
        } else {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">' + (data.error || window.t('error.unknown')) + '</td></tr>';
        }
    } catch (error) {
        console.error('Error loading templates:', error);
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">' + window.t('error.unknown') + '</td></tr>';
        }
    }
}

// Сброс формы шаблона
function resetTemplateForm() {
    document.getElementById('templateId').value = '';
    document.getElementById('templateName').value = '';
    document.getElementById('templateContent').value = '';
    document.getElementById('templatePreview').style.display = 'none';
    document.getElementById('templateModalTitle').textContent = window.t('templates.create');
}

// Редактирование шаблона
function editTemplate(id, name, content) {
    document.getElementById('templateId').value = id;
    document.getElementById('templateName').value = name;
    document.getElementById('templateContent').value = content.replace(/\\n/g, '\n');
    document.getElementById('templateModalTitle').textContent = window.t('templates.actions.edit');
    const modal = new bootstrap.Modal(document.getElementById('templateModal'));
    modal.show();
}

// Сохранение шаблона
async function saveTemplate() {
    const id = document.getElementById('templateId').value;
    const name = document.getElementById('templateName').value;
    const content = document.getElementById('templateContent').value;
    
    if (!name || !content) {
        window.showToast(window.t('templates.form.name') + ' и ' + window.t('templates.form.content') + ' обязательны', 'error');
        return;
    }
    
    try {
        let response;
        if (id) {
            // Обновление
            response = await window.safeFetch(`/api/templates/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, content })
            });
        } else {
            // Создание
            response = await window.safeFetch('/api/templates', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, content })
            });
        }
        
        const data = await response.json();
        
        if (response.ok) {
            window.showToast(data.message, 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('templateModal'));
            modal.hide();
            loadTemplates();
        } else {
            window.showToast(data.error || window.t('error.unknown'), 'error');
        }
    } catch (error) {
        window.showToast(window.t('error.unknown'), 'error');
    }
}

// Активация шаблона
async function activateTemplate(id) {
    if (!confirm(window.t('templates.confirmActivate'))) {
        return;
    }
    try {
        const response = await window.safeFetch(`/api/templates/${id}/activate`, {
            method: 'POST'
        });
        const data = await response.json();
        if (response.ok) {
            window.showToast(data.message, 'success');
            loadTemplates();
            window.loadPostPreview();
        } else {
            window.showToast(data.error, 'error');
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            window.showToast(window.t('error.unknown'), 'error');
        }
    }
}

// Удаление шаблона
async function deleteTemplate(id) {
    if (!confirm(window.t('templates.deleteConfirm'))) {
        return;
    }
    try {
        const response = await window.safeFetch(`/api/templates/${id}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (response.ok) {
            window.showToast(data.message, 'success');
            loadTemplates();
            window.loadPostPreview();
        } else {
            window.showToast(data.error, 'error');
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            window.showToast(window.t('error.unknown'), 'error');
        }
    }
}

// Предпросмотр шаблона
function previewTemplate() {
    const templateContent = document.getElementById('templateContent').value;
    const previewContentEl = document.getElementById('templatePreviewContent');
    const previewInfoEl = document.getElementById('templatePreview');
    const previewLengthEl = document.getElementById('templatePreviewLength');

    if (previewContentEl) {
        previewContentEl.innerHTML = window.formatTelegramText(templateContent);
    }
    if (previewInfoEl) {
        previewInfoEl.style.display = 'block';
    }
    if (previewLengthEl) {
        previewLengthEl.textContent = templateContent.length;
    }
}

// Экспортируем функции в глобальную область видимости
window.loadTemplates = loadTemplates;
window.resetTemplateForm = resetTemplateForm;
window.editTemplate = editTemplate;
window.saveTemplate = saveTemplate;
window.activateTemplate = activateTemplate;
window.deleteTemplate = deleteTemplate;
window.previewTemplate = previewTemplate;

