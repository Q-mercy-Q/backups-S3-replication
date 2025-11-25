// scheduler-main.js
import { SchedulerState } from './scheduler-state.js';
import { SchedulerUI } from './scheduler-ui.js';
import { SchedulerAPI } from './scheduler-api.js';
import { SchedulerEvents } from './scheduler-events.js';
import { NotificationManager } from './notification-manager.js';

class SchedulerApp {
    constructor() {
        this.state = new SchedulerState();
        this.ui = new SchedulerUI(this.state);
        this.api = new SchedulerAPI();
        this.events = new SchedulerEvents(this.state, this.ui, this.api, this);
        this.notifications = new NotificationManager();
        this.initialized = false;
    }

    async init() {
        console.log('Initializing scheduler application...');
        
        try {
            // Инициализация компонентов
            this.events.setupEventListeners();
            
            // Загрузка начальных данных
            await this.loadInitialData();
            
            // Настройка авто-обновления
            this.setupAutoRefresh();
            
            this.initialized = true;
            console.log('Scheduler application initialized');
        } catch (error) {
            console.error('Failed to initialize scheduler app:', error);
            this.notifications.show('Failed to initialize scheduler: ' + error.message, 'error');
        }
    }

    async loadInitialData() {
        try {
            await Promise.all([
                this.loadSchedulerStats(),
                this.loadSchedules(), 
                this.loadSyncHistory()
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.notifications.show('Failed to load initial data', 'error');
        }
    }

    async loadSchedulerStats() {
        try {
            const stats = await this.api.loadSchedulerStats();
            this.state.updateStats(stats);
            this.ui.updateStatsDisplay(stats);
        } catch (error) {
            console.error('Error loading scheduler stats:', error);
            this.notifications.show('Failed to load statistics', 'error');
        }
    }

    async loadSchedules() {
        try {
            const schedules = await this.api.loadSchedules();
            this.state.updateSchedules(schedules);
            this.ui.updateSchedulesDisplay(schedules);
            this.ui.updateHistoryFilter(schedules);
        } catch (error) {
            console.error('Error loading schedules:', error);
            this.notifications.show('Failed to load schedules', 'error');
        }
    }

    async loadSyncHistory() {
        try {
            const filter = document.getElementById('historyFilter')?.value || 'all';
            const limit = document.getElementById('historyLimit')?.value || 50;
            const period = document.getElementById('historyPeriod')?.value || 'all';
            
            const history = await this.api.loadSyncHistory(filter, limit, period);
            this.state.updateHistory(history);
            this.ui.updateHistoryDisplay(history);
        } catch (error) {
            console.error('Error loading sync history:', error);
            this.notifications.show('Failed to load sync history', 'error');
        }
    }

    async loadDebugLogs() {
        try {
            const level = document.getElementById('debugLogLevel')?.value || 'INFO';
            const logs = await this.api.loadDebugLogs(level);
            this.state.updateDebugLogs(logs);
            this.ui.updateDebugLogsDisplay(logs);
        } catch (error) {
            console.error('Error loading debug logs:', error);
            this.notifications.show('Failed to load debug logs', 'error');
        }
    }

    setupAutoRefresh() {
        // Авто-обновление каждые 10 секунд
        setInterval(() => {
            if (!this.state.debugLogsVisible) {
                this.loadSchedulerStats();
                this.loadSchedules();
                this.loadSyncHistory();
            }
        }, 10000);
    }

    // Public methods for global access
    async runSchedule(scheduleId) {
        if (!this.initialized) {
            this.notifications.show('Scheduler not initialized yet', 'error');
            return;
        }

        try {
            const result = await this.api.runSchedule(scheduleId);
            if (result.status === 'success') {
                this.notifications.show('Schedule started manually', 'success');
            } else {
                this.notifications.show('Error: ' + result.message, 'error');
            }
        } catch (error) {
            console.error('Error running schedule:', error);
            this.notifications.show('Error running schedule: ' + error.message, 'error');
        }
    }

    async toggleSchedule(scheduleId, enabled) {
        if (!this.initialized) {
            this.notifications.show('Scheduler not initialized yet', 'error');
            return;
        }

        try {
            const result = await this.api.toggleSchedule(scheduleId, enabled);
            if (result.status === 'success') {
                this.notifications.show(`Schedule ${enabled ? 'enabled' : 'disabled'}`, 'success');
                await this.loadSchedules();
            } else {
                this.notifications.show('Error: ' + result.message, 'error');
            }
        } catch (error) {
            console.error('Error toggling schedule:', error);
            this.notifications.show('Error toggling schedule: ' + error.message, 'error');
        }
    }

    async deleteSchedule(scheduleId) {
        if (!this.initialized) {
            this.notifications.show('Scheduler not initialized yet', 'error');
            return;
        }

        if (!confirm('Are you sure you want to delete this schedule? This action cannot be undone.')) {
            return;
        }
        
        try {
            const result = await this.api.deleteSchedule(scheduleId);
            if (result.status === 'success') {
                this.notifications.show('Schedule deleted successfully', 'success');
                await this.loadSchedules();
            } else {
                this.notifications.show('Error: ' + result.message, 'error');
            }
        } catch (error) {
            console.error('Error deleting schedule:', error);
            this.notifications.show('Error deleting schedule: ' + error.message, 'error');
        }
    }

    async showScheduleStats(scheduleId) {
        if (!this.initialized) {
            this.notifications.show('Scheduler not initialized yet', 'error');
            return;
        }

        const schedule = this.state.getSchedule(scheduleId);
        if (!schedule) {
            this.notifications.show('Schedule not found', 'error');
            return;
        }
        
        this.ui.showScheduleStatsModal(schedule);
    }

    toggleDebugLogs() {
        const debugPanel = document.getElementById('debugLogsPanel');
        const toggleButton = document.getElementById('toggleDebugLogs');
        
        if (!debugPanel || !toggleButton) {
            console.error('Debug logs elements not found');
            return;
        }

        if (this.state.toggleDebugLogs()) {
            debugPanel.style.display = 'block';
            toggleButton.innerHTML = '<i class="fas fa-terminal me-1"></i> Hide Debug Logs';
            this.loadDebugLogs();
            // Auto-refresh debug logs every 5 seconds when visible
            this.state.debugLogsInterval = setInterval(() => this.loadDebugLogs(), 5000);
        } else {
            debugPanel.style.display = 'none';
            toggleButton.innerHTML = '<i class="fas fa-terminal me-1"></i> Debug Logs';
            // Clear auto-refresh interval
            if (this.state.debugLogsInterval) {
                clearInterval(this.state.debugLogsInterval);
                this.state.debugLogsInterval = null;
            }
        }
    }

    async clearDebugLogs() {
        try {
            const result = await this.api.clearDebugLogs();
            if (result.status === 'success') {
                this.notifications.show('Debug logs cleared', 'success');
                await this.loadDebugLogs();
            } else {
                this.notifications.show('Error clearing logs: ' + result.message, 'error');
            }
        } catch (error) {
            this.notifications.show('Error clearing logs: ' + error.message, 'error');
        }
    }

    async refreshAll() {
        await Promise.all([
            this.loadSchedulerStats(),
            this.loadSchedules(),
            this.loadSyncHistory()
        ]);
        this.notifications.show('Scheduler data refreshed', 'info');
    }
}

// Глобальный объект приложения
let schedulerApp = null;

// Инициализация приложения
document.addEventListener('DOMContentLoaded', async () => {
    try {
        schedulerApp = new SchedulerApp();
        await schedulerApp.init();
        
        // Экспортируем для глобального доступа
        window.schedulerApp = schedulerApp;
        
        console.log('Scheduler app initialized successfully');
    } catch (error) {
        console.error('Failed to initialize scheduler app:', error);
        // Показываем ошибку пользователю
        const notification = document.createElement('div');
        notification.className = 'alert alert-danger m-3';
        notification.innerHTML = `
            <h4>Failed to initialize scheduler</h4>
            <p>${error.message}</p>
            <p>Please check console for details and refresh the page.</p>
        `;
        document.body.prepend(notification);
    }
});

// Глобальные функции для вызова из HTML
window.runSchedule = (scheduleId) => {
    if (window.schedulerApp) {
        window.schedulerApp.runSchedule(scheduleId);
    } else {
        console.error('Scheduler app not initialized');
    }
};

window.toggleSchedule = (scheduleId, enabled) => {
    if (window.schedulerApp) {
        window.schedulerApp.toggleSchedule(scheduleId, enabled);
    } else {
        console.error('Scheduler app not initialized');
    }
};

window.deleteSchedule = (scheduleId) => {
    if (window.schedulerApp) {
        window.schedulerApp.deleteSchedule(scheduleId);
    } else {
        console.error('Scheduler app not initialized');
    }
};

window.showScheduleStats = (scheduleId) => {
    if (window.schedulerApp) {
        window.schedulerApp.showScheduleStats(scheduleId);
    } else {
        console.error('Scheduler app not initialized');
    }
};