// Global state
let schedulerState = {
    schedules: {},
    history: [],
    stats: {},
    debugLogs: [],
    debugLogsVisible: false
};

// Initialize scheduler page
function initScheduler() {
    loadSchedulerStats();
    loadSchedules();
    loadSyncHistory();
    setupEventListeners();
    
    // Auto-refresh every 10 seconds
    setInterval(() => {
        loadSchedulerStats();
        loadSchedules();
        loadSyncHistory();
    }, 10000);
}

// Load scheduler statistics
async function loadSchedulerStats() {
    try {
        const response = await fetch('/api/scheduler/stats');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const stats = await response.json();
        
        if (stats.status === 'error') {
            console.error('Error loading stats:', stats.message);
            showNotification('Error loading statistics: ' + stats.message, 'error');
            return;
        }
        
        schedulerState.stats = stats;
        updateStatsDisplay(stats);
    } catch (error) {
        console.error('Error loading scheduler stats:', error);
        showNotification('Failed to load statistics: ' + error.message, 'error');
    }
}

// Load schedules
async function loadSchedules() {
    try {
        const response = await fetch('/api/scheduler/schedules');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const schedules = await response.json();
        
        if (schedules.status === 'error') {
            console.error('Error loading schedules:', schedules.message);
            showNotification('Error loading schedules: ' + schedules.message, 'error');
            return;
        }
        
        schedulerState.schedules = schedules;
        updateSchedulesDisplay(schedules);
        updateHistoryFilter(schedules);
    } catch (error) {
        console.error('Error loading schedules:', error);
        showNotification('Failed to load schedules: ' + error.message, 'error');
    }
}

// Load sync history with filters
async function loadSyncHistory() {
    try {
        const filter = document.getElementById('historyFilter').value;
        const limit = document.getElementById('historyLimit').value;
        const period = document.getElementById('historyPeriod').value;
        
        let url = `/api/scheduler/history?limit=${limit}`;
        if (filter !== 'all') {
            url += `&schedule=${filter}`;
        }
        if (period !== 'all') {
            url += `&period=${period}`;
        }
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const history = await response.json();
        
        if (history.status === 'error') {
            console.error('Error loading history:', history.message);
            showNotification('Error loading history: ' + history.message, 'error');
            return;
        }
        
        schedulerState.history = history;
        updateHistoryDisplay(history);
    } catch (error) {
        console.error('Error loading history:', error);
        showNotification('Failed to load history: ' + error.message, 'error');
    }
}

// Load debug logs
async function loadDebugLogs() {
    try {
        const level = document.getElementById('debugLogLevel').value;
        const response = await fetch(`/api/scheduler/debug_logs?level=${level}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        
        if (result.status === 'success') {
            schedulerState.debugLogs = result.logs;
            updateDebugLogsDisplay(result.logs);
        } else {
            console.error('Error loading debug logs:', result.message);
            showNotification('Error loading debug logs: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('Error loading debug logs:', error);
        showNotification('Failed to load debug logs: ' + error.message, 'error');
    }
}

// Update statistics display
function updateStatsDisplay(stats) {
    const statsContainer = document.getElementById('schedulerStats');
    
    const successRate = stats.success_rate || 0;
    const successRateClass = successRate >= 80 ? 'text-success' : 
                            successRate >= 60 ? 'text-warning' : 'text-danger';
    
    statsContainer.innerHTML = `
        <div class="col-md-2 stat-card">
            <div class="card bg-light">
                <div class="card-body text-center">
                    <div class="stat-value">${stats.total_schedules || 0}</div>
                    <div class="text-muted">Total Schedules</div>
                </div>
            </div>
        </div>
        <div class="col-md-2 stat-card">
            <div class="card bg-light">
                <div class="card-body text-center">
                    <div class="stat-value">${stats.enabled_schedules || 0}</div>
                    <div class="text-muted">Active Schedules</div>
                </div>
            </div>
        </div>
        <div class="col-md-2 stat-card">
            <div class="card bg-light">
                <div class="card-body text-center">
                    <div class="stat-value">${stats.total_runs || 0}</div>
                    <div class="text-muted">Total Runs</div>
                </div>
            </div>
        </div>
        <div class="col-md-2 stat-card">
            <div class="card bg-light">
                <div class="card-body text-center">
                    <div class="stat-value ${successRateClass}">${successRate.toFixed(1)}%</div>
                    <div class="text-muted">Success Rate</div>
                </div>
            </div>
        </div>
        <div class="col-md-2 stat-card">
            <div class="card bg-light">
                <div class="card-body text-center">
                    <div class="stat-value">${stats.total_files_uploaded || 0}</div>
                    <div class="text-muted">Files Uploaded</div>
                </div>
            </div>
        </div>
        <div class="col-md-2 stat-card">
            <div class="card bg-light">
                <div class="card-body text-center">
                    <div class="stat-value">${stats.total_data_uploaded || '0 B'}</div>
                    <div class="text-muted">Data Uploaded</div>
                </div>
            </div>
        </div>
    `;
}

// Update schedules display
function updateSchedulesDisplay(schedules) {
    const container = document.getElementById('schedulesList');
    
    if (Object.keys(schedules).length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-4">No schedules configured</div>';
        return;
    }
    
    let html = '<div class="row">';
    
    for (const [id, schedule] of Object.entries(schedules)) {
        const stats = schedule.stats || {};
        const successRate = stats.success_rate || 0;
        const successRateClass = successRate >= 80 ? 'bg-success' : successRate >= 60 ? 'bg-warning' : 'bg-danger';
        
        // Format interval for display
        const intervalDisplay = formatIntervalForDisplay(schedule);
        
        html += `
            <div class="col-md-6 mb-3">
                <div class="card schedule-card h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h5 class="card-title mb-1">${schedule.name}</h5>
                            <span class="badge ${schedule.enabled ? 'bg-success' : 'bg-secondary'}">
                                <i class="fas ${schedule.enabled ? 'fa-play' : 'fa-pause'} me-1"></i>
                                ${schedule.enabled ? 'Active' : 'Disabled'}
                            </span>
                        </div>
                        
                        <div class="mb-3">
                            <small class="text-muted">
                                <i class="fas fa-clock me-1"></i>
                                ${intervalDisplay}
                            </small>
                        </div>
                        
                        ${stats.total_runs ? `
                        <div class="mb-3">
                            <div class="d-flex justify-content-between small mb-1">
                                <span>Success Rate:</span>
                                <span>${successRate.toFixed(1)}%</span>
                            </div>
                            <div class="progress" style="height: 8px;">
                                <div class="progress-bar ${successRateClass}" style="width: ${Math.min(successRate, 100)}%"></div>
                            </div>
                        </div>
                        ` : ''}
                        
                        <div class="row text-center small mb-3">
                            <div class="col-4">
                                <div class="fw-bold text-primary">${stats.total_runs || 0}</div>
                                <div class="text-muted">Runs</div>
                            </div>
                            <div class="col-4">
                                <div class="fw-bold text-success">${stats.successful_runs || 0}</div>
                                <div class="text-muted">Success</div>
                            </div>
                            <div class="col-4">
                                <div class="fw-bold text-danger">${stats.failed_runs || 0}</div>
                                <div class="text-muted">Failed</div>
                            </div>
                        </div>
                        
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <button class="btn btn-outline-primary btn-sm me-1" onclick="runSchedule('${id}')" title="Run Now">
                                    <i class="fas fa-play"></i>
                                </button>
                                <button class="btn btn-outline-info btn-sm me-1" onclick="showScheduleStats('${id}')" title="View Statistics">
                                    <i class="fas fa-chart-bar"></i>
                                </button>
                            </div>
                            <div>
                                <button class="btn btn-outline-warning btn-sm me-1" onclick="toggleSchedule('${id}', ${!schedule.enabled})" title="${schedule.enabled ? 'Disable' : 'Enable'}">
                                    <i class="fas ${schedule.enabled ? 'fa-pause' : 'fa-play'}"></i>
                                </button>
                                <button class="btn btn-outline-danger btn-sm" onclick="deleteSchedule('${id}')" title="Delete">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                        
                        ${schedule.last_run ? `
                        <div class="mt-2 small text-muted">
                            <i class="fas fa-history me-1"></i>Last run: ${new Date(schedule.last_run).toLocaleString()}
                        </div>
                        ` : ''}
                        
                        ${schedule.next_run ? `
                        <div class="small text-muted">
                            <i class="fas fa-calendar me-1"></i>Next run: ${new Date(schedule.next_run).toLocaleString()}
                        </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }
    
    html += '</div>';
    container.innerHTML = html;
}

// Update history display
function updateHistoryDisplay(history) {
    const container = document.getElementById('syncHistory');
    
    if (history.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-4">No sync history available</div>';
        return;
    }
    
    let html = '';
    
    history.slice().reverse().forEach(item => {
        const statusClass = item.status === 'completed' ? 'border-success' : 
                           item.status === 'failed' ? 'border-danger' : 'border-warning';
        const statusIcon = item.status === 'completed' ? 'fa-check-circle text-success' : 
                          item.status === 'failed' ? 'fa-times-circle text-danger' : 'fa-sync-alt text-warning';
        
        html += `
            <div class="card mb-2 ${statusClass}" style="border-left-width: 4px;">
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="d-flex align-items-center">
                            <i class="fas ${statusIcon} me-2"></i>
                            <div>
                                <strong>${item.schedule_name}</strong>
                                <small class="text-muted ms-2">${new Date(item.start_time).toLocaleString()}</small>
                            </div>
                        </div>
                        <div class="text-end">
                            ${item.duration ? `
                            <small class="text-muted">Duration: ${formatDuration(item.duration)}</small>
                            ` : ''}
                        </div>
                    </div>
                    
                    ${item.files_processed !== undefined ? `
                    <div class="mt-1">
                        <small>
                            Files: ${item.files_uploaded || 0}/${item.files_processed} uploaded
                            ${item.files_failed ? ` (${item.files_failed} failed)` : ''}
                        </small>
                    </div>
                    ` : ''}
                    
                    ${item.uploaded_size ? `
                    <div class="mt-1">
                        <small>Data: ${formatFileSize(item.uploaded_size)}</small>
                    </div>
                    ` : ''}
                    
                    ${item.error ? `
                    <div class="mt-1">
                        <small class="text-danger"><i class="fas fa-exclamation-triangle me-1"></i>${item.error}</small>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Update debug logs display
function updateDebugLogsDisplay(logs) {
    const container = document.getElementById('debugLogsContainer');
    container.innerHTML = '';
    
    if (logs.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-4">No debug logs available</div>';
        return;
    }
    
    logs.forEach(log => {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${log.level.toLowerCase()}`;
        
        const timestamp = document.createElement('span');
        timestamp.className = 'text-muted me-2';
        timestamp.textContent = `[${log.timestamp}]`;
        
        const message = document.createElement('span');
        message.textContent = log.message;
        
        logEntry.appendChild(timestamp);
        logEntry.appendChild(message);
        container.appendChild(logEntry);
    });
    
    // Auto-scroll to bottom
    container.scrollTop = container.scrollHeight;
}

// Update history filter
function updateHistoryFilter(schedules) {
    const filter = document.getElementById('historyFilter');
    const currentValue = filter.value;
    
    // Clear existing options except "All"
    while (filter.options.length > 1) {
        filter.remove(1);
    }
    
    // Add schedule options
    Object.entries(schedules).forEach(([id, schedule]) => {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = schedule.name;
        filter.appendChild(option);
    });
    
    // Restore previous selection
    filter.value = currentValue;
}

// Event listeners
function setupEventListeners() {
    // Schedule type change
    document.getElementById('scheduleType').addEventListener('change', function() {
        const isCron = this.value === 'cron';
        document.getElementById('cronSection').style.display = isCron ? 'block' : 'none';
        document.getElementById('intervalLabel').textContent = isCron ? 'Cron Expression' : 'Interval';
        
        if (isCron) {
            document.getElementById('scheduleIntervalValue').value = '0';
            document.getElementById('scheduleIntervalUnit').value = 'hours';
        }
    });
    
    // Add schedule form
    document.getElementById('addScheduleForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const scheduleType = document.getElementById('scheduleType').value;
        let interval;
        
        if (scheduleType === 'interval') {
            const value = parseInt(document.getElementById('scheduleIntervalValue').value);
            const unit = document.getElementById('scheduleIntervalUnit').value;
            
            // Convert to minutes for storage
            interval = convertToMinutes(value, unit);
            if (interval === null) {
                showNotification('Please enter a valid interval value', 'error');
                return;
            }
        } else {
            interval = document.getElementById('cronExpression').value;
            if (!interval) {
                showNotification('Please enter a cron expression', 'error');
                return;
            }
        }
        
        const formData = {
            name: document.getElementById('scheduleName').value.trim(),
            type: scheduleType,
            interval: interval,
            enabled: document.getElementById('scheduleEnabled').checked
        };
        
        // Validation
        if (!formData.name) {
            showNotification('Please enter a schedule name', 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/scheduler/schedules', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                showNotification('Schedule added successfully!', 'success');
                this.reset();
                // Reset to default values
                document.getElementById('scheduleType').value = 'interval';
                document.getElementById('cronSection').style.display = 'none';
                document.getElementById('intervalLabel').textContent = 'Interval';
                document.getElementById('scheduleIntervalValue').value = '1';
                document.getElementById('scheduleIntervalUnit').value = 'hours';
                document.getElementById('scheduleEnabled').checked = true;
                
                loadSchedules();
            } else {
                showNotification('Error: ' + result.message, 'error');
            }
        } catch (error) {
            showNotification('Error adding schedule: ' + error.message, 'error');
        }
    });
    
    // History filter change
    document.getElementById('historyFilter').addEventListener('change', loadSyncHistory);
    document.getElementById('historyLimit').addEventListener('change', loadSyncHistory);
    document.getElementById('historyPeriod').addEventListener('change', loadSyncHistory);
    
    // Refresh button
    document.getElementById('refreshScheduler').addEventListener('click', function() {
        loadSchedulerStats();
        loadSchedules();
        loadSyncHistory();
        showNotification('Scheduler data refreshed', 'info');
    });
    
    // Debug logs toggle
    document.getElementById('toggleDebugLogs').addEventListener('click', function() {
        const debugPanel = document.getElementById('debugLogsPanel');
        if (debugPanel.style.display === 'none') {
            debugPanel.style.display = 'block';
            this.innerHTML = '<i class="fas fa-terminal me-1"></i> Hide Debug Logs';
            loadDebugLogs();
            // Auto-refresh debug logs every 5 seconds when visible
            schedulerState.debugLogsInterval = setInterval(loadDebugLogs, 5000);
        } else {
            debugPanel.style.display = 'none';
            this.innerHTML = '<i class="fas fa-terminal me-1"></i> Debug Logs';
            // Clear auto-refresh interval
            if (schedulerState.debugLogsInterval) {
                clearInterval(schedulerState.debugLogsInterval);
            }
        }
    });
    
    // Debug log level change
    document.getElementById('debugLogLevel').addEventListener('change', loadDebugLogs);
    
    // Clear debug logs
    document.getElementById('clearDebugLogs').addEventListener('click', async function() {
        try {
            const response = await fetch('/api/scheduler/debug_logs', {
                method: 'DELETE'
            });
            const result = await response.json();
            
            if (result.status === 'success') {
                showNotification('Debug logs cleared', 'success');
                loadDebugLogs();
            } else {
                showNotification('Error clearing logs: ' + result.message, 'error');
            }
        } catch (error) {
            showNotification('Error clearing logs: ' + error.message, 'error');
        }
    });
}

// Schedule actions
async function runSchedule(scheduleId) {
    try {
        const response = await fetch(`/api/scheduler/run/${scheduleId}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showNotification('Schedule started manually', 'success');
        } else {
            showNotification('Error: ' + result.message, 'error');
        }
    } catch (error) {
        showNotification('Error running schedule: ' + error.message, 'error');
    }
}

async function toggleSchedule(scheduleId, enabled) {
    try {
        const response = await fetch(`/api/scheduler/schedules/${scheduleId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ enabled })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showNotification(`Schedule ${enabled ? 'enabled' : 'disabled'}`, 'success');
            loadSchedules();
        } else {
            showNotification('Error: ' + result.message, 'error');
        }
    } catch (error) {
        showNotification('Error toggling schedule: ' + error.message, 'error');
    }
}

async function deleteSchedule(scheduleId) {
    if (!confirm('Are you sure you want to delete this schedule? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/scheduler/schedules/${scheduleId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showNotification('Schedule deleted successfully', 'success');
            loadSchedules();
        } else {
            showNotification('Error: ' + result.message, 'error');
        }
    } catch (error) {
        showNotification('Error deleting schedule: ' + error.message, 'error');
    }
}

async function showScheduleStats(scheduleId) {
    const schedule = schedulerState.schedules[scheduleId];
    if (!schedule) return;
    
    const stats = schedule.stats || {};
    const successRate = stats.success_rate || 0;
    const successRateClass = successRate >= 80 ? 'text-success' : 
                            successRate >= 60 ? 'text-warning' : 'text-danger';
    
    const modalContent = document.getElementById('scheduleStatsContent');
    modalContent.innerHTML = `
        <div class="row mb-4">
            <div class="col-12">
                <h6>${schedule.name}</h6>
                <p class="text-muted mb-0">
                    <i class="fas fa-clock me-1"></i>
                    ${formatIntervalForDisplay(schedule)}
                </p>
                <p class="text-muted">
                    <i class="fas fa-power-off me-1"></i>
                    Status: <span class="badge ${schedule.enabled ? 'bg-success' : 'bg-secondary'}">${schedule.enabled ? 'Active' : 'Disabled'}</span>
                </p>
            </div>
        </div>
        
        <div class="row text-center mb-4">
            <div class="col-3">
                <div class="h4 text-primary">${stats.total_runs || 0}</div>
                <div class="small text-muted">Total Runs</div>
            </div>
            <div class="col-3">
                <div class="h4 text-success">${stats.successful_runs || 0}</div>
                <div class="small text-muted">Successful</div>
            </div>
            <div class="col-3">
                <div class="h4 text-danger">${stats.failed_runs || 0}</div>
                <div class="small text-muted">Failed</div>
            </div>
            <div class="col-3">
                <div class="h4 ${successRateClass}">${successRate.toFixed(1)}%</div>
                <div class="small text-muted">Success Rate</div>
            </div>
        </div>
        
        ${stats.total_files_uploaded ? `
        <div class="row mb-3">
            <div class="col-6">
                <strong>Total Files Uploaded:</strong> ${stats.total_files_uploaded}
            </div>
            <div class="col-6">
                <strong>Total Data Uploaded:</strong> ${stats.total_data_uploaded || formatFileSize(stats.total_data_uploaded_bytes || 0)}
            </div>
        </div>
        ` : ''}
        
        ${stats.average_duration ? `
        <div class="row mb-3">
            <div class="col-6">
                <strong>Average Duration:</strong> ${formatDuration(stats.average_duration)}
            </div>
            <div class="col-6">
                <strong>Last Duration:</strong> ${stats.last_run?.duration ? formatDuration(stats.last_run.duration) : 'N/A'}
            </div>
        </div>
        ` : ''}
        
        ${stats.last_run ? `
        <div class="mt-4">
            <h6>Last Run Details</h6>
            <div class="card bg-light">
                <div class="card-body">
                    <div class="row">
                        <div class="col-6">
                            <strong>Time:</strong> ${new Date(stats.last_run.start_time).toLocaleString()}
                        </div>
                        <div class="col-6">
                            <strong>Status:</strong> 
                            <span class="badge bg-${stats.last_run.status === 'completed' ? 'success' : 'danger'}">
                                ${stats.last_run.status}
                            </span>
                        </div>
                    </div>
                    ${stats.last_run.files_uploaded !== undefined ? `
                    <div class="row mt-2">
                        <div class="col-6">
                            <strong>Files:</strong> ${stats.last_run.files_uploaded} uploaded
                        </div>
                        <div class="col-6">
                            <strong>Data:</strong> ${formatFileSize(stats.last_run.uploaded_size || 0)}
                        </div>
                    </div>
                    ` : ''}
                    ${stats.last_run.duration ? `
                    <div class="row mt-2">
                        <div class="col-6">
                            <strong>Duration:</strong> ${formatDuration(stats.last_run.duration)}
                        </div>
                    </div>
                    ` : ''}
                </div>
            </div>
        </div>
        ` : ''}
    `;
    
    new bootstrap.Modal(document.getElementById('scheduleStatsModal')).show();
}

// Utility functions
function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDuration(seconds) {
    if (!seconds) return '0s';
    if (seconds < 60) {
        return seconds.toFixed(1) + 's';
    } else if (seconds < 3600) {
        return Math.floor(seconds / 60) + 'm ' + (seconds % 60).toFixed(0) + 's';
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return hours + 'h ' + minutes + 'm';
    }
}

function convertToMinutes(value, unit) {
    if (!value || value < 1) return null;
    
    switch (unit) {
        case 'minutes':
            return value;
        case 'hours':
            return value * 60;
        case 'days':
            return value * 24 * 60;
        case 'weeks':
            return value * 7 * 24 * 60;
        default:
            return value;
    }
}

function formatIntervalForDisplay(schedule) {
    if (schedule.type === 'cron') {
        return `Cron: ${schedule.interval}`;
    }
    
    // For interval schedules, convert minutes back to readable format
    const minutes = parseInt(schedule.interval);
    
    if (minutes % (7 * 24 * 60) === 0) {
        const weeks = minutes / (7 * 24 * 60);
        return `Every ${weeks} week${weeks > 1 ? 's' : ''}`;
    } else if (minutes % (24 * 60) === 0) {
        const days = minutes / (24 * 60);
        return `Every ${days} day${days > 1 ? 's' : ''}`;
    } else if (minutes % 60 === 0) {
        const hours = minutes / 60;
        return `Every ${hours} hour${hours > 1 ? 's' : ''}`;
    } else {
        return `Every ${minutes} minute${minutes > 1 ? 's' : ''}`;
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} alert-dismissible fade show`;
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

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initScheduler);