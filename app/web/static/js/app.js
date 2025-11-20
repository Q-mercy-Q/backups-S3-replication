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
    
    // Update UI based on upload state
    updateUploadStateUI(data.is_running);
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

// Get current configuration from form
function getCurrentConfig() {
    const config = {
        NFS_PATH: document.getElementById('nfsPath').value.trim(),
        S3_ENDPOINT: document.getElementById('s3Endpoint').value.trim(),
        S3_BUCKET: document.getElementById('s3Bucket').value.trim(),
        S3_ACCESS_KEY: document.getElementById('S3_ACCESS_KEY').value.trim(),
        S3_SECRET_KEY: document.getElementById('S3_SECRET_KEY').value.trim(),
        BACKUP_DAYS: parseInt(document.getElementById('backupDays').value) || 7,
        MAX_THREADS: parseInt(document.getElementById('maxThreads').value) || 4,
        STORAGE_CLASS: document.getElementById('storageClass').value,
        ENABLE_TAPE_STORAGE: document.getElementById('enableTapeStorage').checked
    };
    
    // Validation
    if (!config.NFS_PATH) {
        showNotification('NFS Path is required', 'error');
        throw new Error('NFS Path is required');
    }
    if (!config.S3_ENDPOINT) {
        showNotification('S3 Endpoint is required', 'error');
        throw new Error('S3 Endpoint is required');
    }
    if (!config.S3_BUCKET) {
        showNotification('S3 Bucket is required', 'error');
        throw new Error('S3 Bucket is required');
    }
    
    return config;
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
            const config = getCurrentConfig();
            const result = await apiCall('/api/start_upload', { 
                method: 'POST',
                body: config
            });
            
            handleApiResult(result, 'Upload');
        } catch (error) {
            showNotification(error.message, 'error');
        }
    });

    // Stop Upload
    document.getElementById('stopUpload').addEventListener('click', async () => {
        const result = await apiCall('/api/stop_upload', { method: 'POST' });
        handleApiResult(result, 'Stop upload');
    });

    // Test Connection
    document.getElementById('testConnection').addEventListener('click', async () => {
        try {
            const config = getCurrentConfig();
            const result = await apiCall('/api/test_connection', { 
                method: 'POST',
                body: config
            });
            
            handleApiResult(result, 'Connection test');
        } catch (error) {
            showNotification(error.message, 'error');
        }
    });

    // Scan Files
    document.getElementById('scanFiles').addEventListener('click', async () => {
        try {
            const config = getCurrentConfig();
            const result = await apiCall('/api/scan_files', { 
                method: 'POST',
                body: config
            });
            
            handleScanResult(result);
        } catch (error) {
            showNotification(error.message, 'error');
        }
    });

    // Refresh Stats
    document.getElementById('refreshStats').addEventListener('click', async () => {
        const result = await apiCall('/api/statistics');
        updateStatistics(result);
        addLogEntry({ level: 'info', message: 'Statistics refreshed', timestamp: new Date().toLocaleTimeString() });
    });

    // Save Configuration
    document.getElementById('saveConfig').addEventListener('click', async () => {
        try {
            const config = getCurrentConfig();
            const result = await apiCall('/api/config', {
                method: 'POST',
                body: config
            });

            handleApiResult(result, 'Save config');
        } catch (error) {
            showNotification(error.message, 'error');
        }
    });

    // Reset Configuration
    document.getElementById('resetConfig').addEventListener('click', () => {
        if (confirm('Are you sure you want to reset configuration to defaults? This will reload the page.')) {
            // Reset form values to initial state (from server)
            loadInitialConfiguration();
            showNotification('Configuration form reset to initial values', 'info');
        }
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
        // Ctrl+Enter to start upload
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            document.getElementById('startUpload').click();
        }
        // Escape to stop upload
        if (e.key === 'Escape' && appState.uploadInProgress) {
            document.getElementById('stopUpload').click();
        }
    });
}

// Handle API results
function handleApiResult(result, action) {
    if (result.status === 'success') {
        showNotification(result.message, 'success');
        addLogEntry({ level: 'info', message: result.message, timestamp: new Date().toLocaleTimeString() });
        
        // If saving config was successful, update the form with the returned config
        if (action === 'Save config' && result.config) {
            updateFormWithConfig(result.config);
        }
    } else {
        showNotification(result.message, 'error');
        addLogEntry({ level: 'error', message: result.message, timestamp: new Date().toLocaleTimeString() });
    }
}

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

// Load initial configuration from server
async function loadInitialConfiguration() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        updateFormWithConfig(config);
    } catch (error) {
        console.error('Error loading configuration:', error);
        showNotification('Error loading configuration', 'error');
    }
}

// Update form with configuration data
function updateFormWithConfig(config) {
    document.getElementById('nfsPath').value = config.NFS_PATH || '';
    document.getElementById('s3Endpoint').value = config.S3_ENDPOINT || '';
    document.getElementById('s3Bucket').value = config.S3_BUCKET || '';
    document.getElementById('S3_ACCESS_KEY').value = config.S3_ACCESS_KEY || '';
    document.getElementById('S3_SECRET_KEY').value = config.S3_SECRET_KEY || '';
    document.getElementById('backupDays').value = config.BACKUP_DAYS || '7';
    document.getElementById('maxThreads').value = config.MAX_THREADS || '4';
    document.getElementById('storageClass').value = config.STORAGE_CLASS || 'GLACIER';
    document.getElementById('enableTapeStorage').checked = config.ENABLE_TAPE_STORAGE === 'true';
}

// Initialize the application
function initApp() {
    setupEventListeners();
    
    // Load initial configuration
    loadInitialConfiguration();
    
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