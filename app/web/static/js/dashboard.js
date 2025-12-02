// Dashboard JavaScript

async function apiCall(url, options = {}) {
    const config = {
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
        ...options
    };

    if (config.body && typeof config.body !== 'string') {
        config.body = JSON.stringify(config.body);
    }

    const response = await fetch(url, config);
    const data = await response.json();
    if (!response.ok || data.status === 'error') {
        throw new Error(data.message || `Request failed with status ${response.status}`);
    }
    return data;
}

async function loadUploadStatus() {
    try {
        const stats = await apiCall('/api/statistics');
        const statusCard = document.getElementById('uploadStatusCard');
        
        if (stats.is_running) {
            statusCard.innerHTML = `
                <div class="alert alert-info">
                    <h6><i class="fas fa-spinner fa-spin me-2"></i>Upload in Progress</h6>
                    <p class="mb-1"><strong>Status:</strong> Running</p>
                    <p class="mb-1"><strong>Progress:</strong> ${stats.overall_progress.toFixed(1)}%</p>
                    <p class="mb-1"><strong>Files:</strong> ${stats.successful}/${stats.total_files}</p>
                    <a href="/upload-manager" class="btn btn-sm btn-primary mt-2">View Details</a>
                </div>
            `;
        } else {
            statusCard.innerHTML = `
                <div class="alert alert-success">
                    <h6><i class="fas fa-check-circle me-2"></i>Ready</h6>
                    <p class="mb-1"><strong>Status:</strong> Idle</p>
                    <p class="mb-1"><strong>Last Run:</strong> ${stats.last_run || 'N/A'}</p>
                    <a href="/upload-manager" class="btn btn-sm btn-primary mt-2">Start Upload</a>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('uploadStatusCard').innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>Unable to load upload status
            </div>
        `;
    }
}

async function loadSchedulerStatus() {
    try {
        const stats = await apiCall('/api/scheduler/stats');
        const statusCard = document.getElementById('schedulerStatusCard');
        
        const successRate = stats.success_rate ? stats.success_rate.toFixed(1) : 0;
        const badgeClass = successRate >= 80 ? 'bg-success' : successRate >= 60 ? 'bg-warning' : 'bg-danger';
        
        statusCard.innerHTML = `
            <div>
                <h6><i class="fas fa-clock me-2"></i>Scheduler Active</h6>
                <div class="row mt-3">
                    <div class="col-6">
                        <div class="text-center">
                            <div class="h4 mb-0">${stats.enabled_schedules || 0}</div>
                            <small class="text-muted">Active Schedules</small>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="text-center">
                            <div class="h4 mb-0">${stats.total_schedules || 0}</div>
                            <small class="text-muted">Total Schedules</small>
                        </div>
                    </div>
                </div>
                <div class="mt-3">
                    <div class="d-flex justify-content-between mb-1">
                        <small>Success Rate</small>
                        <small><span class="badge ${badgeClass}">${successRate}%</span></small>
                    </div>
                    <div class="progress" style="height: 8px;">
                        <div class="progress-bar ${badgeClass.replace('bg-', 'bg-')}" 
                             style="width: ${successRate}%"></div>
                    </div>
                </div>
                <a href="/scheduler" class="btn btn-sm btn-info mt-3 w-100">Manage Schedules</a>
            </div>
        `;
    } catch (error) {
        document.getElementById('schedulerStatusCard').innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>Unable to load scheduler status
            </div>
        `;
    }
}

async function loadUploadStatsOverview() {
    try {
        const stats = await apiCall('/api/statistics');
        const overviewDiv = document.getElementById('uploadStatsOverview');
        
        overviewDiv.innerHTML = `
            <div class="row text-center">
                <div class="col-6 mb-3">
                    <div class="h3 mb-0 text-primary">${stats.total_files || 0}</div>
                    <small class="text-muted">Total Files</small>
                </div>
                <div class="col-6 mb-3">
                    <div class="h3 mb-0 text-success">${stats.successful || 0}</div>
                    <small class="text-muted">Successful</small>
                </div>
                <div class="col-6 mb-3">
                    <div class="h3 mb-0 text-danger">${stats.failed || 0}</div>
                    <small class="text-muted">Failed</small>
                </div>
                <div class="col-6 mb-3">
                    <div class="h3 mb-0 text-info">${stats.upload_speed || '0 B/s'}</div>
                    <small class="text-muted">Upload Speed</small>
                </div>
            </div>
        `;
    } catch (error) {
        document.getElementById('uploadStatsOverview').innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>Unable to load statistics
            </div>
        `;
    }
}

async function loadSchedulerStatsOverview() {
    try {
        const stats = await apiCall('/api/scheduler/stats');
        const overviewDiv = document.getElementById('schedulerStatsOverview');
        
        overviewDiv.innerHTML = `
            <div class="row text-center">
                <div class="col-6 mb-3">
                    <div class="h3 mb-0 text-primary">${stats.total_runs || 0}</div>
                    <small class="text-muted">Total Runs</small>
                </div>
                <div class="col-6 mb-3">
                    <div class="h3 mb-0 text-success">${stats.successful_runs || 0}</div>
                    <small class="text-muted">Successful</small>
                </div>
                <div class="col-6 mb-3">
                    <div class="h3 mb-0 text-danger">${stats.failed_runs || 0}</div>
                    <small class="text-muted">Failed</small>
                </div>
                <div class="col-6 mb-3">
                    <div class="h3 mb-0 text-info">${stats.total_files_uploaded || 0}</div>
                    <small class="text-muted">Files Uploaded</small>
                </div>
            </div>
        `;
    } catch (error) {
        document.getElementById('schedulerStatsOverview').innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>Unable to load statistics
            </div>
        `;
    }
}

async function loadRecentActivity() {
    try {
        const history = await apiCall('/api/scheduler/history?limit=5');
        const activityDiv = document.getElementById('recentActivity');
        
        // История возвращается как массив
        const historyArray = Array.isArray(history) ? history : (history.history || []);
        
        if (historyArray.length === 0) {
            activityDiv.innerHTML = '<p class="text-muted text-center">No recent activity</p>';
            return;
        }
        
        let html = '<div class="list-group">';
        historyArray.slice(0, 5).forEach(entry => {
            const statusBadge = entry.status === 'completed' 
                ? '<span class="badge bg-success">Completed</span>'
                : entry.status === 'failed'
                ? '<span class="badge bg-danger">Failed</span>'
                : '<span class="badge bg-secondary">Running</span>';
            
            html += `
                <div class="list-group-item">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">${entry.schedule_name || 'Manual Run'}</h6>
                            <small class="text-muted">${new Date(entry.start_time).toLocaleString()}</small>
                        </div>
                        <div>
                            ${statusBadge}
                            <small class="d-block text-muted mt-1">${entry.files_uploaded || 0} files</small>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        activityDiv.innerHTML = html;
    } catch (error) {
        document.getElementById('recentActivity').innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>Unable to load recent activity
            </div>
        `;
    }
}

async function refreshDashboard() {
    await Promise.all([
        loadUploadStatus(),
        loadSchedulerStatus(),
        loadUploadStatsOverview(),
        loadSchedulerStatsOverview(),
        loadRecentActivity()
    ]);
    
    // Load stats and update charts
    try {
        const [uploadStats, schedulerStats] = await Promise.all([
            apiCall('/api/statistics').catch(() => ({})),
            apiCall('/api/scheduler/stats').catch(() => ({}))
        ]);
        
        // Update status chart if function exists
        if (typeof window.updateFilesStatusChart === 'function') {
            window.updateFilesStatusChart(uploadStats, schedulerStats);
        }
        
        // Update history charts if function exists (не пересоздавая графики)
        if (typeof window.updateUploadHistoryChart === 'function') {
            fetch('/api/scheduler/history?limit=30')
                .then(response => response.json())
                .then(data => {
                    const history = data.history || data || [];
                    window.updateUploadHistoryChart(history);
                    if (typeof window.updateDataVolumeChart === 'function') {
                        window.updateDataVolumeChart(history);
                    }
                })
                .catch(error => {
                    console.error('Error loading history for charts:', error);
                });
        }
    } catch (error) {
        console.error('Error updating charts:', error);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    await refreshDashboard();
    
    // Auto-refresh every 30 seconds
    setInterval(refreshDashboard, 30000);
    
    // Refresh button
    const refreshBtn = document.getElementById('refreshDashboard');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Refreshing...';
            await refreshDashboard();
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="fas fa-sync me-1"></i>Refresh';
        });
    }
});

