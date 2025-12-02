// Socket.IO connection
const socket = io();

// Global state
let appState = {
    isConnected: false,
    uploadInProgress: false,
    currentStats: null,
    autoRefresh: true
};

// Connection status
socket.on('connect', function() {
    appState.isConnected = true;
    updateConnectionStatus(true);
    console.log('Connected to server');
});

socket.on('disconnect', function() {
    appState.isConnected = false;
    updateConnectionStatus(false);
    console.log('Disconnected from server');
});

socket.on('connected', function(data) {
    addLogEntry({ message: data.message, level: 'info' });
});

// Statistics updates
socket.on('stats_update', function(data) {
    appState.currentStats = data;
    updateStatistics(data);
});

// Log messages
socket.on('log_message', function(data) {
    addLogEntry(data);
});

// Update connection status in UI
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connectionStatus');
    const textElement = document.getElementById('connectionText');
    
    if (connected) {
        statusElement.className = 'connection-status connected';
        textElement.textContent = 'Connected';
        textElement.className = 'text-success';
    } else {
        statusElement.className = 'connection-status disconnected';
        textElement.textContent = 'Disconnected';
        textElement.className = 'text-danger';
    }
}

// Update statistics from data
function updateStatistics(data) {
    // Progress bars
    const overallProgress = document.getElementById('overallProgress');
    overallProgress.style.width = `${data.overall_progress}%`;
    overallProgress.textContent = `${data.overall_progress.toFixed(1)}%`;

    // Update progress bar color based on progress
    updateProgressBarColor(data.overall_progress);

    // Statistics values
    updateStatValue('totalFiles', data.total_files);
    updateStatValue('filesToUpload', data.files_to_upload);
    updateStatValue('successfulUploads', data.successful);
    updateStatValue('failedUploads', data.failed);
    updateStatValue('skippedExisting', data.skipped_existing);
    updateStatValue('skippedTime', data.skipped_time);
    updateStatValue('uploadSpeed', data.upload_speed);
    updateStatValue('elapsedTime', data.elapsed_time);
    
    document.getElementById('detailedStats').textContent = data.detailed_stats;

    // Update button states
    appState.uploadInProgress = data.is_running;
    document.getElementById('startUpload').disabled = data.is_running;
    document.getElementById('stopUpload').disabled = !data.is_running;
    const abortBtn = document.getElementById('abortUpload');
    if (abortBtn) {
        abortBtn.disabled = !data.is_running;
    }
    
    // Update charts if they exist
    if (typeof updateUploadSpeedChart === 'function') {
        updateUploadSpeedChart(data.upload_speed);
    }
    if (typeof updateFilesProgressChart === 'function') {
        updateFilesProgressChart(data.successful, data.failed, data.files_to_upload);
    }
    
    // Update UI based on upload state
    updateUploadStateUI(data.is_running);
    
    // Reset charts when upload stops
    if (!data.is_running && typeof resetUploadCharts === 'function') {
        // Don't reset immediately, wait a bit to see final state
        setTimeout(() => {
            if (!appState.uploadInProgress) {
                resetUploadCharts();
            }
        }, 5000);
    }
}

function updateProgressBarColor(progress) {
    const progressBar = document.getElementById('overallProgress');
    progressBar.classList.remove('bg-danger', 'bg-warning', 'bg-success', 'bg-info');
    
    if (progress === 0) {
        progressBar.classList.add('bg-info');
    } else if (progress < 30) {
        progressBar.classList.add('bg-warning');
    } else if (progress < 70) {
        progressBar.classList.add('bg-info');
    } else {
        progressBar.classList.add('bg-success');
    }
}

function updateStatValue(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

function updateUploadStateUI(isRunning) {
    const statusIndicator = document.getElementById('uploadStatusIndicator');
    if (isRunning) {
        statusIndicator.className = 'status-indicator status-active';
        statusIndicator.innerHTML = '<i class="fas fa-sync fa-spin me-1"></i> Uploading...';
    } else {
        statusIndicator.className = 'status-indicator status-inactive';
        statusIndicator.innerHTML = '<i class="fas fa-pause me-1"></i> Ready';
    }
}

// Add log entry
function addLogEntry(entry) {
    const logContainer = document.getElementById('logContainer');
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${entry.level}`;
    
    // Create timestamp and message
    const timestamp = document.createElement('span');
    timestamp.className = 'text-muted me-2';
    timestamp.textContent = `[${entry.timestamp}]`;
    
    const message = document.createElement('span');
    message.textContent = entry.message;
    
    logEntry.appendChild(timestamp);
    logEntry.appendChild(message);
    logContainer.appendChild(logEntry);
    
    // Auto-scroll to bottom
    logContainer.scrollTop = logContainer.scrollHeight;
    
    // Limit log entries to prevent memory issues
    const maxLogEntries = 500;
    const logEntries = logContainer.getElementsByClassName('log-entry');
    if (logEntries.length > maxLogEntries) {
        logContainer.removeChild(logEntries[0]);
    }
}

// API calls
async function apiCall(url, options = {}) {
    try {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        const mergedOptions = { ...defaultOptions, ...options };
        
        if (mergedOptions.body) {
            mergedOptions.body = JSON.stringify(mergedOptions.body);
        }
        
        showLoadingState();
        
        const response = await fetch(url, mergedOptions);
        const result = await response.json();
        
        hideLoadingState();
        return result;
    } catch (error) {
        console.error('API call failed:', error);
        hideLoadingState();
        return { status: 'error', message: 'Network error: ' + error.message };
    }
}

// Show/hide loading states
function showLoadingState() {
    document.body.style.cursor = 'wait';
}

function hideLoadingState() {
    document.body.style.cursor = 'default';
}

// Event handlers
function setupEventListeners() {
    // Start Upload
    document.getElementById('startUpload').addEventListener('click', async () => {
        try {
            // Проверяем режим загрузки
            const uploadMode = (typeof window.getCurrentUploadMode === 'function') 
                ? window.getCurrentUploadMode() 
                : 'auto';
            const payload = { upload_mode: uploadMode };
            
            // Добавляем выбранный storage_class
            const storageClassSelect = document.getElementById('uploadStorageClass');
            if (storageClassSelect) {
                payload.STORAGE_CLASS = storageClassSelect.value;
            }
            
            // Добавляем config_id если выбран
            const configSelector = document.getElementById('uploadConfigSelector');
            if (configSelector && configSelector.value) {
                payload.CONFIG_ID = parseInt(configSelector.value);
            }
            
            // Если режим manual, добавляем выбранные файлы
            if (uploadMode === 'manual') {
                const selected = (typeof window.selectedFiles === 'function') 
                    ? window.selectedFiles() 
                    : [];
                if (selected.length === 0) {
                    showNotification('Please select files first', 'warning');
                    return;
                }
                payload.files_to_upload = selected;
            }
            
            const result = await apiCall('/api/start_upload', { 
                method: 'POST',
                body: payload
            });
            handleApiResult(result, 'Upload');
        } catch (error) {
            console.error('Error starting upload:', error);
            showNotification(`Error starting upload: ${error.message}`, 'error');
        }
    });

    // Stop Upload (graceful)
    document.getElementById('stopUpload').addEventListener('click', async () => {
        const result = await apiCall('/api/stop_upload', { 
            method: 'POST',
            body: { mode: 'graceful' }
        });
        handleApiResult(result, 'Остановка загрузки');
    });
    
    // Abort Upload (force)
    document.getElementById('abortUpload').addEventListener('click', async () => {
        const confirmed = await showConfirmModal(
            'Прервать загрузку',
            'Вы уверены, что хотите немедленно прервать загрузку? Все активные загрузки будут остановлены, оставшиеся файлы будут отменены.',
            'Прервать',
            'Отмена',
            'danger'
        );
        if (!confirmed) {
            return;
        }
        const result = await apiCall('/api/stop_upload', { 
            method: 'POST',
            body: { mode: 'force' }
        });
        handleApiResult(result, 'Прерывание загрузки');
    });

    // Test Connection
    document.getElementById('testConnection').addEventListener('click', async () => {
        const result = await apiCall('/api/test_connection', { method: 'POST' });
            handleApiResult(result, 'Connection test');
    });

    // Scan Files
    document.getElementById('scanFiles').addEventListener('click', async () => {
        const result = await apiCall('/api/scan_files', { method: 'POST' });
            handleScanResult(result);
    });

    // Refresh Stats
    document.getElementById('refreshStats').addEventListener('click', async () => {
        const result = await apiCall('/api/statistics');
        updateStatistics(result);
        addLogEntry({ level: 'info', message: 'Statistics refreshed', timestamp: new Date().toLocaleTimeString() });
    });

    // Clear Logs
    document.getElementById('clearLogs').addEventListener('click', () => {
        document.getElementById('logContainer').innerHTML = '';
        addLogEntry({ level: 'info', message: 'Logs cleared', timestamp: new Date().toLocaleTimeString() });
    });

    // Auto-refresh toggle
    document.getElementById('autoRefreshToggle').addEventListener('change', (e) => {
        appState.autoRefresh = e.target.checked;
        addLogEntry({ 
            level: 'info', 
            message: `Auto-refresh ${appState.autoRefresh ? 'enabled' : 'disabled'}`, 
            timestamp: new Date().toLocaleTimeString() 
        });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            document.getElementById('startUpload').click();
        }
        if (e.key === 'Escape' && appState.uploadInProgress) {
            document.getElementById('stopUpload').click();
        }
    });
}

// Handle API results
function handleApiResult(result, action) {
    console.log(`API result for ${action}:`, result);
    
    if (result.status === 'success') {
        showNotification(result.message, 'success');
        addLogEntry({ level: 'info', message: result.message, timestamp: new Date().toLocaleTimeString() });
        
    } else {
        showNotification(result.message, 'error');
        addLogEntry({ level: 'error', message: result.message, timestamp: new Date().toLocaleTimeString() });
    }
}

// Экспортируем showNotification глобально
window.showNotification = showNotification;

// Handle scan results
function handleScanResult(result) {
    if (result.status === 'success') {
        showNotification(result.message, 'success');
        addLogEntry({ level: 'info', message: result.message, timestamp: new Date().toLocaleTimeString() });
        
        if (result.skipped_existing > 0 || result.skipped_time > 0) {
            addLogEntry({ 
                level: 'info', 
                message: `Skipped ${result.skipped_existing} existing files and ${result.skipped_time} files by time filter`, 
                timestamp: new Date().toLocaleTimeString() 
            });
        }
        if (result.total_size && result.total_size !== '0 Bytes') {
            addLogEntry({ 
                level: 'info', 
                message: `Total size to upload: ${result.total_size}`, 
                timestamp: new Date().toLocaleTimeString() 
            });
        }
    } else if (result.status === 'warning') {
        showNotification(result.message, 'warning');
        addLogEntry({ level: 'warning', message: result.message, timestamp: new Date().toLocaleTimeString() });
        
        if (result.skipped_existing > 0 || result.skipped_time > 0) {
            addLogEntry({ 
                level: 'info', 
                message: `Skipped ${result.skipped_existing} existing files and ${result.skipped_time} files by time filter`, 
                timestamp: new Date().toLocaleTimeString() 
            });
        }
    } else {
        showNotification(result.message, 'error');
        addLogEntry({ level: 'error', message: result.message, timestamp: new Date().toLocaleTimeString() });
    }
}

// Show notification
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.alert-notification');
    existingNotifications.forEach(notification => notification.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} alert-notification alert-dismissible fade show`;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '1000';
    notification.style.minWidth = '300px';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Initialize the application
function initApp() {
    setupEventListeners();
    
    // Initial statistics load
    apiCall('/api/statistics').then(updateStatistics);
    
    // Auto-refresh statistics every 3 seconds
    setInterval(() => {
        if (appState.isConnected && appState.autoRefresh) {
            apiCall('/api/statistics').then(updateStatistics);
        }
    }, 3000);
    
    // Add welcome message
    addLogEntry({ 
        level: 'info', 
        message: 'S3 Backup Upload Manager initialized. Use Ctrl+Enter to start upload, Escape to stop.', 
        timestamp: new Date().toLocaleTimeString() 
    });
}

// Start the application when DOM is loaded
document.addEventListener('DOMContentLoaded', initApp);