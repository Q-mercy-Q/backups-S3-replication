// Dashboard Charts JavaScript - Charts for dashboard page

let uploadHistoryChart = null;
let filesStatusChart = null;
let dataVolumeChart = null;
let chartsInitialized = false;

function initDashboardCharts() {
    // Предотвращаем повторную инициализацию
    if (chartsInitialized) {
        console.log('Charts already initialized, skipping...');
        return;
    }
    
    // Initialize Upload History Chart
    const historyCtx = document.getElementById('uploadHistoryChart');
    if (historyCtx) {
        // Уничтожаем существующий график, если он есть
        if (uploadHistoryChart) {
            uploadHistoryChart.destroy();
        }
        uploadHistoryChart = new Chart(historyCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Successful Uploads',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1,
                        fill: true
                    },
                    {
                        label: 'Failed Uploads',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.1,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Files'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    }
                },
                animation: {
                    duration: 0 // Отключаем анимацию для плавных обновлений
                }
            }
        });
    }

    // Initialize Files Status Distribution Chart
    const statusCtx = document.getElementById('filesStatusChart');
    if (statusCtx) {
        // Уничтожаем существующий график, если он есть
        if (filesStatusChart) {
            filesStatusChart.destroy();
        }
        filesStatusChart = new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['Successful', 'Failed', 'Skipped'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(255, 206, 86, 0.8)'
                    ],
                    borderColor: [
                        'rgba(75, 192, 192, 1)',
                        'rgba(255, 99, 132, 1)',
                        'rgba(255, 206, 86, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                animation: {
                    duration: 0 // Отключаем анимацию для плавных обновлений
                }
            }
        });
    }

    // Initialize Data Volume Over Time Chart
    const volumeCtx = document.getElementById('dataVolumeChart');
    if (volumeCtx) {
        // Уничтожаем существующий график, если он есть
        if (dataVolumeChart) {
            dataVolumeChart.destroy();
        }
        dataVolumeChart = new Chart(volumeCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Data Uploaded (GB)',
                    data: [],
                    backgroundColor: 'rgba(54, 162, 235, 0.8)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Data: ${context.parsed.y.toFixed(2)} GB`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Volume (GB)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    }
                }
            }
        });
    }
    
    // Помечаем графики как инициализированные
    chartsInitialized = true;
}

function updateUploadHistoryChart(historyData) {
    if (!uploadHistoryChart || !historyData || historyData.length === 0) return;
    
    // Sort by date (oldest first)
    const sorted = [...historyData].sort((a, b) => 
        new Date(a.start_time) - new Date(b.start_time)
    );
    
    // Get last 30 entries
    const recent = sorted.slice(-30);
    
    const labels = recent.map(h => {
        const date = new Date(h.start_time);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    });
    
    uploadHistoryChart.data.labels = labels;
    uploadHistoryChart.data.datasets[0].data = recent.map(h => h.files_uploaded || 0);
    uploadHistoryChart.data.datasets[1].data = recent.map(h => h.files_failed || 0);
    uploadHistoryChart.update('none'); // Обновляем без анимации для плавности
}

function updateFilesStatusChart(uploadStats, schedulerStats) {
    if (!filesStatusChart) return;
    
    const successful = uploadStats?.successful || 0;
    const failed = uploadStats?.failed || 0;
    const skipped = (uploadStats?.skipped_existing || 0) + (uploadStats?.skipped_time || 0);
    
    filesStatusChart.data.datasets[0].data = [successful, failed, skipped];
    filesStatusChart.update('none'); // Обновляем без анимации для плавности
}

function updateDataVolumeChart(historyData) {
    if (!dataVolumeChart || !historyData || historyData.length === 0) return;
    
    // Sort by date (oldest first)
    const sorted = [...historyData].sort((a, b) => 
        new Date(a.start_time) - new Date(b.start_time)
    );
    
    // Get last 20 entries
    const recent = sorted.slice(-20);
    
    const labels = recent.map(h => {
        const date = new Date(h.start_time);
        return date.toLocaleDateString();
    });
    
    // Convert bytes to GB
    const dataGB = recent.map(h => {
        const bytes = h.uploaded_size || 0;
        return bytes / (1024 * 1024 * 1024); // Convert to GB
    });
    
    dataVolumeChart.data.labels = labels;
    dataVolumeChart.data.datasets[0].data = dataGB;
    dataVolumeChart.update('none'); // Обновляем без анимации для плавности
}

function loadDashboardCharts() {
    // Убеждаемся, что графики инициализированы
    if (!chartsInitialized) {
        initDashboardCharts();
    }
    
    // Load history data and update charts
    fetch('/api/scheduler/history?limit=30')
        .then(response => response.json())
        .then(data => {
            const history = data.history || data || [];
            updateUploadHistoryChart(history);
            updateDataVolumeChart(history);
        })
        .catch(error => {
            console.error('Error loading history for charts:', error);
        });
    
    // Load current stats and update status chart
    Promise.all([
        fetch('/api/statistics').then(r => r.json()),
        fetch('/api/scheduler/stats').then(r => r.json())
    ])
        .then(([uploadStats, schedulerStats]) => {
            updateFilesStatusChart(uploadStats, schedulerStats);
        })
        .catch(error => {
            console.error('Error loading stats for charts:', error);
        });
}

// Make functions globally accessible
window.loadDashboardCharts = loadDashboardCharts;
window.updateFilesStatusChart = updateFilesStatusChart;
window.updateUploadHistoryChart = updateUploadHistoryChart;
window.updateDataVolumeChart = updateDataVolumeChart;

// Initialize charts when DOM is ready (only once)
let chartsInitAttempted = false;

function initializeChartsOnce() {
    if (chartsInitAttempted) return;
    chartsInitAttempted = true;
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            if (!chartsInitialized) {
                initDashboardCharts();
            }
            loadDashboardCharts();
        });
    } else {
        if (!chartsInitialized) {
            initDashboardCharts();
        }
        loadDashboardCharts();
    }
}

// Инициализируем графики только один раз
initializeChartsOnce();

