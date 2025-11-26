// scheduler-events.js
import { FormatUtils } from './format-utils.js';

export class SchedulerEvents {
    constructor(state, ui, api, app) {
        this.state = state;
        this.ui = ui;
        this.api = api;
        this.app = app;
    }

    setupEventListeners() {
        this.setupScheduleFormEvents();
        this.setupFilterEvents();
        this.setupActionEvents();
        this.setupDebugLogsEvents();
    }

    setupScheduleFormEvents() {
        const scheduleType = document.getElementById('scheduleType');
        if (scheduleType) {
            scheduleType.addEventListener('change', (e) => this.handleScheduleTypeChange(e));
        }

        const addScheduleForm = document.getElementById('addScheduleForm');
        if (addScheduleForm) {
            addScheduleForm.addEventListener('submit', (e) => this.handleAddSchedule(e));
        }
    }

    setupFilterEvents() {
        const historyFilter = document.getElementById('historyFilter');
        const historyLimit = document.getElementById('historyLimit');
        const historyPeriod = document.getElementById('historyPeriod');

        if (historyFilter) historyFilter.addEventListener('change', () => this.onHistoryFilterChange());
        if (historyLimit) historyLimit.addEventListener('change', () => this.onHistoryFilterChange());
        if (historyPeriod) historyPeriod.addEventListener('change', () => this.onHistoryFilterChange());
    }

    setupActionEvents() {
        const refreshScheduler = document.getElementById('refreshScheduler');
        if (refreshScheduler) {
            refreshScheduler.addEventListener('click', () => this.handleRefresh());
        }
    }

    setupDebugLogsEvents() {
        const toggleDebugLogs = document.getElementById('toggleDebugLogs');
        if (toggleDebugLogs) {
            toggleDebugLogs.addEventListener('click', () => this.toggleDebugLogs());
        }

        const debugLogLevel = document.getElementById('debugLogLevel');
        if (debugLogLevel) {
            debugLogLevel.addEventListener('change', () => this.loadDebugLogs());
        }

        const clearDebugLogs = document.getElementById('clearDebugLogs');
        if (clearDebugLogs) {
            clearDebugLogs.addEventListener('click', () => this.clearDebugLogs());
        }
    }

    handleScheduleTypeChange(event) {
        const isCron = event.target.value === 'cron';
        const cronSection = document.getElementById('cronSection');
        const intervalLabel = document.getElementById('intervalLabel');
        
        if (cronSection) {
            cronSection.style.display = isCron ? 'block' : 'none';
        }
        if (intervalLabel) {
            intervalLabel.textContent = isCron ? 'Cron Expression' : 'Interval';
        }
        
        if (isCron) {
            const intervalValue = document.getElementById('scheduleIntervalValue');
            const intervalUnit = document.getElementById('scheduleIntervalUnit');
            if (intervalValue) intervalValue.value = '0';
            if (intervalUnit) intervalUnit.value = 'hours';
        }
    }

    async handleAddSchedule(event) {
        event.preventDefault();
        
        const scheduleType = document.getElementById('scheduleType')?.value;
        if (!scheduleType) {
            this.app.notifications.show('Schedule type is required', 'error');
            return;
        }

        let interval;
        
        if (scheduleType === 'interval') {
            const value = parseInt(document.getElementById('scheduleIntervalValue')?.value || 0);
            const unit = document.getElementById('scheduleIntervalUnit')?.value || 'hours';
            
            // Convert to minutes for storage
            interval = FormatUtils.convertToMinutes(value, unit);
            if (interval === null || interval <= 0) {
                this.app.notifications.show('Please enter a valid interval value', 'error');
                return;
            }
        } else {
            interval = document.getElementById('cronExpression')?.value;
            if (!interval) {
                this.app.notifications.show('Please enter a cron expression', 'error');
                return;
            }
        }
        
        const scheduleName = document.getElementById('scheduleName')?.value.trim();
        if (!scheduleName) {
            this.app.notifications.show('Please enter a schedule name', 'error');
            return;
        }
        
        const formData = {
            name: scheduleName,
            type: scheduleType,
            interval: interval.toString(),
            enabled: document.getElementById('scheduleEnabled')?.checked || true
        };

        const categories = this.getSelectedCategories();
        if (categories.length > 0) {
            formData.categories = categories;
        }
        
        try {
            const result = await this.api.addSchedule(formData);
            
            if (result.status === 'success') {
                this.app.notifications.show('Schedule added successfully!', 'success');
                
                // Reset form
                const form = document.getElementById('addScheduleForm');
                if (form) form.reset();
                
                // Reset to default values
                document.getElementById('scheduleType').value = 'interval';
                document.getElementById('cronSection').style.display = 'none';
                document.getElementById('intervalLabel').textContent = 'Interval';
                document.getElementById('scheduleIntervalValue').value = '1';
                document.getElementById('scheduleIntervalUnit').value = 'hours';
                document.getElementById('scheduleEnabled').checked = true;
                this.resetCategorySelection();
                
                await this.app.loadSchedules();
            } else {
                this.app.notifications.show('Error: ' + (result.message || 'Unknown error'), 'error');
            }
        } catch (error) {
            console.error('Error adding schedule:', error);
            this.app.notifications.show('Error adding schedule: ' + error.message, 'error');
        }
    }

    onHistoryFilterChange() {
        this.app.loadSyncHistory();
    }

    handleRefresh() {
        this.app.refreshAll();
    }

    toggleDebugLogs() {
        this.app.toggleDebugLogs();
    }

    async loadDebugLogs() {
        await this.app.loadDebugLogs();
    }

    async clearDebugLogs() {
        await this.app.clearDebugLogs();
    }

    getSelectedCategories() {
        return Array.from(document.querySelectorAll('.schedule-category:checked')).map(input => input.value);
    }

    resetCategorySelection() {
        document.querySelectorAll('.schedule-category').forEach(input => {
            input.checked = true;
        });
    }
}