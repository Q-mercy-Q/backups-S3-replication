// scheduler-ui.js
import { FormatUtils } from './format-utils.js';

export class SchedulerUI {
    constructor(state) {
        this.state = state;
    }

    updateStatsDisplay(stats) {
        const container = document.getElementById('schedulerStats');
        if (!container) return;

        const successRate = stats.success_rate || 0;
        const successRateClass = successRate >= 80 ? 'text-success' : 
                                successRate >= 60 ? 'text-warning' : 'text-danger';

        container.innerHTML = this._createStatsHTML(stats, successRate, successRateClass);
    }

    _createStatsHTML(stats, successRate, successRateClass) {
        return `
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

    updateSchedulesDisplay(schedules) {
        const container = document.getElementById('schedulesList');
        if (!container) return;

        if (!schedules || Object.keys(schedules).length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-4">No schedules configured</div>';
            return;
        }

        container.innerHTML = this._createSchedulesHTML(schedules);
    }

    _createSchedulesHTML(schedules) {
        let html = '<div class="row">';
        
        for (const [id, schedule] of Object.entries(schedules)) {
            html += this._createScheduleCardHTML(id, schedule);
        }
        
        html += '</div>';
        return html;
    }

    _createScheduleCardHTML(id, schedule) {
        const stats = schedule.stats || {};
        const successRate = stats.success_rate || 0;
        const successRateClass = successRate >= 80 ? 'bg-success' : 
                                successRate >= 60 ? 'bg-warning' : 'bg-danger';
        const intervalDisplay = FormatUtils.formatIntervalForDisplay(schedule);

        return `
            <div class="col-md-6 mb-3">
                <div class="card schedule-card h-100">
                    <div class="card-body">
                        ${this._createScheduleCardHeaderHTML(schedule)}
                        ${this._createScheduleCategoriesHTML(schedule)}
                        ${this._createScheduleIntervalHTML(intervalDisplay)}
                        ${this._createScheduleStatsHTML(stats, successRate, successRateClass)}
                        ${this._createScheduleActionsHTML(id, schedule)}
                        ${this._createScheduleTimestampsHTML(schedule)}
                    </div>
                </div>
            </div>
        `;
    }

    _createScheduleCardHeaderHTML(schedule) {
        return `
            <div class="d-flex justify-content-between align-items-start mb-2">
                <h5 class="card-title mb-1">${schedule.name || 'Unnamed Schedule'}</h5>
                <span class="badge ${schedule.enabled ? 'bg-success' : 'bg-secondary'}">
                    <i class="fas ${schedule.enabled ? 'fa-play' : 'fa-pause'} me-1"></i>
                    ${schedule.enabled ? 'Active' : 'Disabled'}
                </span>
            </div>
        `;
    }

    _createScheduleCategoriesHTML(schedule) {
        let html = '';
        
        // Показываем расширения файлов, если они используются
        if (schedule.file_extensions && schedule.file_extensions.length > 0) {
            const extensionBadges = schedule.file_extensions.map(ext => 
                `<span class="badge bg-info text-white me-1 mb-1"><i class="fas fa-file-code me-1"></i>${ext}</span>`
            ).join('');
            html += `
                <div class="mb-2">
                    <small class="text-muted d-block mb-1">File Extensions:</small>
                    ${extensionBadges}
                </div>
            `;
        }
        
        // Показываем категории, если они используются (и нет расширений)
        if (schedule.categories && schedule.categories.length > 0 && (!schedule.file_extensions || schedule.file_extensions.length === 0)) {
            const badges = schedule.categories.map(category => 
                `<span class="badge bg-light text-dark border me-1 mb-1">${category}</span>`
            ).join('');
            html += `
                <div class="mb-2">
                    <small class="text-muted d-block mb-1">Categories:</small>
                    ${badges}
                </div>
            `;
        }
        
        return html;
    }

    _createScheduleIntervalHTML(intervalDisplay) {
        return `
            <div class="mb-3">
                <small class="text-muted">
                    <i class="fas fa-clock me-1"></i>
                    ${intervalDisplay}
                </small>
            </div>
        `;
    }

    _createScheduleStatsHTML(stats, successRate, successRateClass) {
        if (!stats.total_runs) return '';

        return `
            <div class="mb-3">
                <div class="d-flex justify-content-between small mb-1">
                    <span>Success Rate:</span>
                    <span>${successRate.toFixed(1)}%</span>
                </div>
                <div class="progress" style="height: 8px;">
                    <div class="progress-bar ${successRateClass}" style="width: ${Math.min(successRate, 100)}%"></div>
                </div>
            </div>
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
        `;
    }

    _createScheduleActionsHTML(id, schedule) {
        return `
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
        `;
    }

    _createScheduleTimestampsHTML(schedule) {
        let html = '';
        if (schedule.last_run) {
            html += `
                <div class="mt-2 small text-muted">
                    <i class="fas fa-history me-1"></i>Last run: ${new Date(schedule.last_run).toLocaleString()}
                </div>
            `;
        }
        if (schedule.next_run) {
            html += `
                <div class="small text-muted">
                    <i class="fas fa-calendar me-1"></i>Next run: ${new Date(schedule.next_run).toLocaleString()}
                </div>
            `;
        }
        return html;
    }

    updateHistoryDisplay(history) {
        const container = document.getElementById('syncHistory');
        if (!container) return;

        if (!history || history.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-4">No sync history available</div>';
            return;
        }

        container.innerHTML = this._createHistoryHTML(history);
    }

    _createHistoryHTML(history) {
        let html = '';
        
        // Show most recent first
        history.slice().reverse().forEach(item => {
            html += this._createHistoryItemHTML(item);
        });
        
        return html;
    }

    _createHistoryItemHTML(item) {
        const statusClass = item.status === 'completed' ? 'border-success' : 
                           item.status === 'failed' ? 'border-danger' : 'border-warning';
        const statusIcon = item.status === 'completed' ? 'fa-check-circle text-success' : 
                          item.status === 'failed' ? 'fa-times-circle text-danger' : 'fa-sync-alt text-warning';
        
        return `
            <div class="card mb-2 ${statusClass}" style="border-left-width: 4px;">
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="d-flex align-items-center">
                            <i class="fas ${statusIcon} me-2"></i>
                            <div>
                                <strong>${item.schedule_name || 'Unknown Schedule'}</strong>
                                <small class="text-muted ms-2">${new Date(item.start_time).toLocaleString()}</small>
                            </div>
                        </div>
                        <div class="text-end">
                            ${item.duration ? `
                            <small class="text-muted">Duration: ${FormatUtils.formatDuration(item.duration)}</small>
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
                        <small>Data: ${FormatUtils.formatFileSize(item.uploaded_size)}</small>
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
    }

    updateDebugLogsDisplay(logs) {
        const container = document.getElementById('debugLogsContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (!logs || logs.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-4">No debug logs available</div>';
            return;
        }
        
        logs.forEach(log => {
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry log-${log.level ? log.level.toLowerCase() : 'info'}`;
            
            const timestamp = document.createElement('span');
            timestamp.className = 'text-muted me-2';
            timestamp.textContent = `[${log.timestamp || new Date().toLocaleTimeString()}]`;
            
            const message = document.createElement('span');
            message.textContent = log.message || JSON.stringify(log);
            
            logEntry.appendChild(timestamp);
            logEntry.appendChild(message);
            container.appendChild(logEntry);
        });
        
        // Auto-scroll to bottom
        container.scrollTop = container.scrollHeight;
    }

    updateHistoryFilter(schedules) {
        const filter = document.getElementById('historyFilter');
        if (!filter) return;
        
        const currentValue = filter.value;
        
        // Clear existing options except "All"
        while (filter.options.length > 1) {
            filter.remove(1);
        }
        
        // Add schedule options
        if (schedules && typeof schedules === 'object') {
            Object.entries(schedules).forEach(([id, schedule]) => {
                const option = document.createElement('option');
                option.value = id;
                option.textContent = schedule.name || `Schedule ${id}`;
                filter.appendChild(option);
            });
        }
        
        // Restore previous selection if it still exists
        if (Array.from(filter.options).some(opt => opt.value === currentValue)) {
            filter.value = currentValue;
        }
    }

    showScheduleStatsModal(schedule) {
        const stats = schedule.stats || {};
        const successRate = stats.success_rate || 0;
        const successRateClass = successRate >= 80 ? 'text-success' : 
                                successRate >= 60 ? 'text-warning' : 'text-danger';
        
        const modalContent = document.getElementById('scheduleStatsContent');
        if (!modalContent) return;
        
        modalContent.innerHTML = this._createScheduleStatsModalHTML(schedule, stats, successRate, successRateClass);
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('scheduleStatsModal'));
        modal.show();
    }

    _createScheduleStatsModalHTML(schedule, stats, successRate, successRateClass) {
        return `
            <div class="row mb-4">
                <div class="col-12">
                    <h6>${schedule.name || 'Unnamed Schedule'}</h6>
                    <p class="text-muted mb-0">
                        <i class="fas fa-clock me-1"></i>
                        ${FormatUtils.formatIntervalForDisplay(schedule)}
                    </p>
                    <p class="text-muted">
                        <i class="fas fa-power-off me-1"></i>
                        Status: <span class="badge ${schedule.enabled ? 'bg-success' : 'bg-secondary'}">${schedule.enabled ? 'Active' : 'Disabled'}</span>
                    </p>
                ${schedule.file_extensions && schedule.file_extensions.length ? `
                <p class="text-muted">
                    <i class="fas fa-file-code me-1"></i>
                    File Extensions: ${schedule.file_extensions.join(', ')}
                </p>
                ` : ''}
                ${schedule.categories && schedule.categories.length && (!schedule.file_extensions || schedule.file_extensions.length === 0) ? `
                <p class="text-muted">
                    <i class="fas fa-tags me-1"></i>
                    Categories: ${schedule.categories.join(', ')}
                </p>
                ` : ''}
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
                    <strong>Total Data Uploaded:</strong> ${stats.total_data_uploaded || FormatUtils.formatFileSize(stats.total_data_uploaded_bytes || 0)}
                </div>
            </div>
            ` : ''}
            
            ${stats.average_duration ? `
            <div class="row mb-3">
                <div class="col-6">
                    <strong>Average Duration:</strong> ${FormatUtils.formatDuration(stats.average_duration)}
                </div>
                <div class="col-6">
                    <strong>Last Duration:</strong> ${stats.last_run?.duration ? FormatUtils.formatDuration(stats.last_run.duration) : 'N/A'}
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
                                <strong>Data:</strong> ${FormatUtils.formatFileSize(stats.last_run.uploaded_size || 0)}
                            </div>
                        </div>
                        ` : ''}
                        ${stats.last_run.duration ? `
                        <div class="row mt-2">
                            <div class="col-6">
                                <strong>Duration:</strong> ${FormatUtils.formatDuration(stats.last_run.duration)}
                            </div>
                        </div>
                        ` : ''}
                    </div>
                </div>
            </div>
            ` : ''}
        `;
    }
}