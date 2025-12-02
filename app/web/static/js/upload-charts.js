// Upload Charts JavaScript - Real-time charts for upload manager

let uploadSpeedChart = null;
let filesProgressChart = null;
let speedDataPoints = [];
let progressDataPoints = [];
let chartsInitialized = false;
const MAX_DATA_POINTS = 60; // Keep last 60 data points (1 minute at 1 second intervals)

function initUploadCharts() {
    // Предотвращаем повторную инициализацию
    if (chartsInitialized) {
        console.log('Upload charts already initialized, skipping...');
        return;
    }
    
    // Initialize Upload Speed Chart
    const speedCtx = document.getElementById('uploadSpeedChart');
    if (speedCtx) {
        // Уничтожаем существующий график, если он есть
        if (uploadSpeedChart) {
            uploadSpeedChart.destroy();
        }
        uploadSpeedChart = new Chart(speedCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Upload Speed (MB/s)',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
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
                            text: 'Speed (MB/s)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                },
                animation: {
                    duration: 0 // Disable animation for real-time updates
                }
            }
        });
    }

    // Initialize Files Progress Chart
    const progressCtx = document.getElementById('filesProgressChart');
    if (progressCtx) {
        // Уничтожаем существующий график, если он есть
        if (filesProgressChart) {
            filesProgressChart.destroy();
        }
        filesProgressChart = new Chart(progressCtx, {
            type: 'bar',
            data: {
                labels: ['Successful', 'Failed', 'Remaining'],
                datasets: [{
                    label: 'Files',
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
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.parsed.y + ' files';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Files'
                        }
                    }
                },
                animation: {
                    duration: 0
                }
            }
        });
    }
    
    // Помечаем графики как инициализированные
    chartsInitialized = true;
}

function updateUploadSpeedChart(uploadSpeed, timestamp = null) {
    if (!uploadSpeedChart) return;
    
    // Parse speed string like "1.5 MB/s" to number
    let speedMB = 0;
    if (uploadSpeed && uploadSpeed !== '0 B/s') {
        const match = uploadSpeed.match(/([\d.]+)\s*(KB|MB|GB)\/s/i);
        if (match) {
            const value = parseFloat(match[1]);
            const unit = match[2].toUpperCase();
            speedMB = unit === 'GB' ? value * 1024 : (unit === 'KB' ? value / 1024 : value);
        }
    }
    
    const now = timestamp || new Date().toLocaleTimeString();
    const chart = uploadSpeedChart.data;
    
    chart.labels.push(now);
    chart.datasets[0].data.push(speedMB);
    
    // Keep only last MAX_DATA_POINTS
    if (chart.labels.length > MAX_DATA_POINTS) {
        chart.labels.shift();
        chart.datasets[0].data.shift();
    }
    
    uploadSpeedChart.update('none');
}

function updateFilesProgressChart(successful, failed, totalFiles) {
    if (!filesProgressChart) return;
    
    const remaining = Math.max(0, totalFiles - successful - failed);
    
    filesProgressChart.data.datasets[0].data = [successful, failed, remaining];
    filesProgressChart.update('none');
}

function resetUploadCharts() {
    if (uploadSpeedChart) {
        uploadSpeedChart.data.labels = [];
        uploadSpeedChart.data.datasets[0].data = [];
        uploadSpeedChart.update();
    }
    
    if (filesProgressChart) {
        filesProgressChart.data.datasets[0].data = [0, 0, 0];
        filesProgressChart.update();
    }
}

// Make functions globally accessible
window.updateUploadSpeedChart = updateUploadSpeedChart;
window.updateFilesProgressChart = updateFilesProgressChart;
window.resetUploadCharts = resetUploadCharts;

// Initialize charts when DOM is ready (only once)
let uploadChartsInitAttempted = false;

function initializeUploadChartsOnce() {
    if (uploadChartsInitAttempted) return;
    uploadChartsInitAttempted = true;
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            if (!chartsInitialized) {
                initUploadCharts();
            }
        });
    } else {
        if (!chartsInitialized) {
            initUploadCharts();
        }
    }
}

// Инициализируем графики только один раз
initializeUploadChartsOnce();

