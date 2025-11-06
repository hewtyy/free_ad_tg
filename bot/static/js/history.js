// History module - функции для работы с историей публикаций

// Загрузка истории публикаций
async function loadHistory() {
    console.log('loadHistory() called');
    const tbody = document.getElementById('historyTableBody');
    const historyTab = document.getElementById('history');
    if (!tbody) {
        console.error('historyTableBody element not found');
        return;
    }
    
    if (tbody.dataset.loading === 'true') {
        console.log('History: Already loading, skipping...');
        return;
    }
    tbody.dataset.loading = 'true';
    
    tbody.innerHTML = '<tr><td colspan="5" class="text-center"><i class="fas fa-spinner fa-spin"></i> ' + window.t('history.loading') + '</td></tr>';
    
    try {
        const params = new URLSearchParams({
            limit: window.historyPageSize,
            offset: (window.historyPage - 1) * window.historyPageSize
        });
        
        if (window.historyFilters.status) params.append('status', window.historyFilters.status);
        if (window.historyFilters.search) params.append('search', window.historyFilters.search);
        if (window.historyFilters.start_date) params.append('start_date', window.historyFilters.start_date + ' 00:00:00');
        if (window.historyFilters.end_date) params.append('end_date', window.historyFilters.end_date + ' 23:59:59');
        
        const response = await window.safeFetch(`/api/publication_history?${params.toString()}`);
        const data = await response.json();
        
        if (response.ok && data.success) {
            console.log('History: Data received, records count:', data.history.length);
            if (data.history.length === 0) {
                console.log('History: Empty list, showing empty message');
                tbody.innerHTML = '<tr><td colspan="5" class="text-center">' + window.t('history.empty') + '</td></tr>';
                
                // Убеждаемся, что таблица видима даже для пустого списка
                const historyTable = tbody.closest('table');
                if (historyTable) {
                    historyTable.style.display = 'table';
                    historyTable.style.visibility = 'visible';
                }
                tbody.style.display = 'table-row-group';
                tbody.style.visibility = 'visible';
            } else {
                console.log('History: Building HTML for', data.history.length, 'records');
                const html = data.history.map(record => {
                    const statusBadge = record.status === 'success' 
                        ? '<span class="badge bg-success">' + window.t('history.status.success') + '</span>'
                        : '<span class="badge bg-danger">' + window.t('history.status.error') + '</span>';
                    
                    return `
                        <tr>
                            <td>${record.published_at}</td>
                            <td>${record.chat_title || record.chat_username || record.chat_id}</td>
                            <td>${statusBadge}</td>
                            <td>${record.retry_count}</td>
                            <td>${record.error_message || '-'}</td>
                        </tr>
                    `;
                }).join('');
                
                console.log('History: Inserting HTML into tbody, length:', html.length);
                tbody.innerHTML = html;
                console.log('History: HTML inserted, tbody.innerHTML length:', tbody.innerHTML.length);
                
                // Проверяем видимость таблицы
                const historyTable = tbody.closest('table');
                const historyTab = tbody.closest('.tab-pane');
                console.log('History: Table visibility:', {
                    tableExists: !!historyTable,
                    tabExists: !!historyTab,
                    tabHasShow: historyTab?.classList.contains('show'),
                    tabHasActive: historyTab?.classList.contains('active'),
                    tabDisplay: historyTab ? window.getComputedStyle(historyTab).display : 'N/A',
                    tabOpacity: historyTab ? window.getComputedStyle(historyTab).opacity : 'N/A',
                    tableDisplay: historyTable ? window.getComputedStyle(historyTable).display : 'N/A'
                });
                
                // Убеждаемся, что таблица видима
                if (historyTable) {
                    historyTable.style.display = 'table';
                    historyTable.style.visibility = 'visible';
                }
                tbody.style.display = 'table-row-group';
                tbody.style.visibility = 'visible';
                
                // Обновляем пагинацию
                const hasMore = data.history.length === window.historyPageSize;
                const prevBtn = document.getElementById('historyPrevBtn');
                const nextBtn = document.getElementById('historyNextBtn');
                const pageInfo = document.getElementById('historyPageInfo');
                if (prevBtn) prevBtn.disabled = window.historyPage === 1;
                if (nextBtn) nextBtn.disabled = !hasMore;
                if (pageInfo) pageInfo.textContent = `${window.historyPage} / ${hasMore ? window.historyPage + 1 : window.historyPage}`;
            }
        } else {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">' + (data.error || window.t('error.unknown')) + '</td></tr>';
            tbody.dataset.loading = 'false';
        }
    } catch (error) {
        console.error('Error loading history:', error);
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">' + window.t('error.unknown') + '</td></tr>';
        tbody.dataset.loading = 'false';
    }
}

// Очистка истории публикаций
function clearHistory() {
    if (!confirm(window.t('history.clearConfirm'))) {
        return;
    }
    
    window.safeFetch('/api/publication_history/clear', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.showToast(data.message, 'success');
            window.historyPage = 1;
            loadHistory();
        } else {
            window.showToast(data.error || window.t('error.unknown'), 'error');
        }
    })
    .catch(error => {
        window.showToast(window.t('error.unknown'), 'error');
    });
}

// Экспортируем функции в глобальную область видимости
window.loadHistory = loadHistory;
window.clearHistory = clearHistory;

