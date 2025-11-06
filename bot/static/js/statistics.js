// Statistics module - функции для работы со статистикой

// Переменные для графиков
window.dailyChart = null;
window.successRateChart = null;
window.hourlyChart = null;
window.topGroupsChart = null;

// Загрузка статистики
async function loadStatistics() {
    console.log('loadStatistics() called');
    try {
        const dateFromEl = document.getElementById('statDateFrom');
        const dateToEl = document.getElementById('statDateTo');
        console.log('Statistics elements found:', !!dateFromEl, !!dateToEl);
        
        const params = new URLSearchParams();
        if (dateFromEl && dateFromEl.value) params.append('start_date', dateFromEl.value + ' 00:00:00');
        if (dateToEl && dateToEl.value) params.append('end_date', dateToEl.value + ' 23:59:59');
        
        console.log('Fetching statistics from:', `/api/publication_statistics?${params.toString()}`);
        const response = await window.safeFetch(`/api/publication_statistics?${params.toString()}`);
        const data = await response.json();
        console.log('Statistics response:', response.ok, data);
        console.log('Statistics data structure:', {
            success: data.success,
            statistics: data.statistics
        });
        
        if (response.ok && data.success) {
            const stats = data.statistics;
            console.log('Statistics: Processing data, stats:', stats);
            
            // Обновляем карточки статистики
            const statTotalEl = document.getElementById('statTotal');
            const statSuccessfulEl = document.getElementById('statSuccessful');
            const statFailedEl = document.getElementById('statFailed');
            const statSuccessRateEl = document.getElementById('statSuccessRate');
            
            console.log('Statistics: Card elements found:', {
                statTotal: !!statTotalEl,
                statSuccessful: !!statSuccessfulEl,
                statFailed: !!statFailedEl,
                statSuccessRate: !!statSuccessRateEl
            });
            
            if (statTotalEl) {
                statTotalEl.textContent = stats.total || 0;
                console.log('Statistics: Updated statTotal to', stats.total || 0);
            }
            if (statSuccessfulEl) {
                statSuccessfulEl.textContent = stats.successful || 0;
                console.log('Statistics: Updated statSuccessful to', stats.successful || 0);
            }
            if (statFailedEl) {
                statFailedEl.textContent = stats.failed || 0;
                console.log('Statistics: Updated statFailed to', stats.failed || 0);
            }
            if (statSuccessRateEl) {
                statSuccessRateEl.textContent = (stats.success_rate || 0) + '%';
                console.log('Statistics: Updated statSuccessRate to', (stats.success_rate || 0) + '%');
            }
            
            // Обновляем графики только если элементы существуют
            const dailyChartEl = document.getElementById('dailyChart');
            const successRateChartEl = document.getElementById('successRateChart');
            const hourlyChartEl = document.getElementById('hourlyChart');
            const topGroupsChartEl = document.getElementById('topGroupsChart');
            
            console.log('Statistics: Chart elements found:', {
                dailyChart: !!dailyChartEl,
                successRateChart: !!successRateChartEl,
                hourlyChart: !!hourlyChartEl,
                topGroupsChart: !!topGroupsChartEl
            });
            
            // Проверяем видимость вкладки статистики
            const statisticsTab = statTotalEl?.closest('.tab-pane');
            console.log('Statistics: Tab visibility:', {
                tabExists: !!statisticsTab,
                tabHasShow: statisticsTab?.classList.contains('show'),
                tabHasActive: statisticsTab?.classList.contains('active'),
                tabDisplay: statisticsTab ? window.getComputedStyle(statisticsTab).display : 'N/A',
                tabOpacity: statisticsTab ? window.getComputedStyle(statisticsTab).opacity : 'N/A'
            });
            
            if (dailyChartEl) {
                console.log('Statistics: Updating daily chart');
                updateDailyChart(stats.daily_stats || []);
            } else {
                console.warn('Statistics: dailyChart element not found');
            }
            if (successRateChartEl) {
                console.log('Statistics: Updating success rate chart');
                updateSuccessRateChart(stats.successful || 0, stats.failed || 0);
            } else {
                console.warn('Statistics: successRateChart element not found');
            }
            if (hourlyChartEl) {
                console.log('Statistics: Updating hourly chart');
                updateHourlyChart(stats.hourly_stats || []);
            } else {
                console.warn('Statistics: hourlyChart element not found');
            }
            if (topGroupsChartEl) {
                console.log('Statistics: Updating top groups chart');
                updateTopGroupsChart(stats.top_groups || []);
            } else {
                console.warn('Statistics: topGroupsChart element not found');
            }
        } else {
            console.error('Error loading statistics:', data.error);
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Обновление графика ежедневной активности
function updateDailyChart(dailyStats) {
    const chartEl = document.getElementById('dailyChart');
    if (!chartEl) return;
    
    const ctx = chartEl.getContext('2d');
    
    // Подготавливаем данные (переворачиваем для показа от старых к новым)
    const reversed = [...dailyStats].reverse();
    const labels = reversed.map(d => {
        const date = new Date(d.date + 'T00:00:00');
        return date.toLocaleDateString(window.currentLanguage === 'ru' ? 'ru-RU' : 'en-US', { 
            month: 'short', 
            day: 'numeric' 
        });
    });
    const successfulData = reversed.map(d => d.successful || 0);
    const failedData = reversed.map(d => d.failed || 0);
    
    if (window.dailyChart) {
        window.dailyChart.destroy();
    }
    
    window.dailyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: window.t('statistics.successful'),
                data: successfulData,
                borderColor: 'rgb(40, 167, 69)',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                tension: 0.4
            }, {
                label: window.t('statistics.failed'),
                data: failedData,
                borderColor: 'rgb(220, 53, 69)',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Обновление графика успешности
function updateSuccessRateChart(successful, failed) {
    const chartEl = document.getElementById('successRateChart');
    if (!chartEl) return;
    
    const ctx = chartEl.getContext('2d');
    
    if (window.successRateChart) {
        window.successRateChart.destroy();
    }
    
    window.successRateChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: [window.t('statistics.successful'), window.t('statistics.failed')],
            datasets: [{
                data: [successful, failed],
                backgroundColor: [
                    'rgb(40, 167, 69)',
                    'rgb(220, 53, 69)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                }
            }
        }
    });
}

// Обновление графика почасовой активности
function updateHourlyChart(hourlyStats) {
    const chartEl = document.getElementById('hourlyChart');
    if (!chartEl) return;
    
    const ctx = chartEl.getContext('2d');
    
    // Создаем массив для всех 24 часов
    const hourlyData = Array(24).fill(0);
    hourlyStats.forEach(h => {
        hourlyData[h.hour] = h.count || 0;
    });
    
    const labels = Array.from({length: 24}, (_, i) => i.toString().padStart(2, '0') + ':00');
    
    if (window.hourlyChart) {
        window.hourlyChart.destroy();
    }
    
    window.hourlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: window.t('statistics.publications'),
                data: hourlyData,
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Обновление графика топ групп
function updateTopGroupsChart(topGroups) {
    const chartEl = document.getElementById('topGroupsChart');
    if (!chartEl) return;
    
    const ctx = chartEl.getContext('2d');
    
    const labels = topGroups.map(g => g.title || g.chat_id || 'Unknown').slice(0, 10);
    const data = topGroups.map(g => g.count || 0).slice(0, 10);
    
    if (window.topGroupsChart) {
        window.topGroupsChart.destroy();
    }
    
    if (topGroups.length === 0) {
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.font = '16px Arial';
        ctx.fillStyle = '#666';
        ctx.textAlign = 'center';
        ctx.fillText(window.t('statistics.noData'), ctx.canvas.width / 2, ctx.canvas.height / 2);
        return;
    }
    
    window.topGroupsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: window.t('statistics.publications'),
                data: data,
                backgroundColor: 'rgba(153, 102, 255, 0.5)',
                borderColor: 'rgba(153, 102, 255, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Экспортируем функции в глобальную область видимости
window.loadStatistics = loadStatistics;
window.updateDailyChart = updateDailyChart;
window.updateSuccessRateChart = updateSuccessRateChart;
window.updateHourlyChart = updateHourlyChart;
window.updateTopGroupsChart = updateTopGroupsChart;

