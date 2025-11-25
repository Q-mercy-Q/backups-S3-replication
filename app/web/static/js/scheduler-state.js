// scheduler-state.js
export class SchedulerState {
    constructor() {
        this.schedules = {};
        this.history = [];
        this.stats = {};
        this.debugLogs = [];
        this.debugLogsVisible = false;
        this.debugLogsInterval = null;
    }

    updateSchedules(schedules) {
        this.schedules = schedules || {};
    }

    updateHistory(history) {
        this.history = history || [];
    }

    updateStats(stats) {
        this.stats = stats || {};
    }

    updateDebugLogs(logs) {
        this.debugLogs = logs || [];
    }

    getSchedule(scheduleId) {
        return this.schedules[scheduleId];
    }

    getFilteredHistory(filter = 'all', limit = 50, period = 'all') {
        let filtered = [...this.history];
        
        // Фильтрация по расписанию
        if (filter && filter !== 'all') {
            filtered = filtered.filter(item => item.schedule_id === filter);
        }
        
        // Фильтрация по периоду
        if (period && period !== 'all') {
            const now = new Date();
            let startDate;
            
            switch (period) {
                case 'today':
                    startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                    break;
                case 'week':
                    startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                    break;
                case 'month':
                    startDate = new Date(now.getFullYear(), now.getMonth(), 1);
                    break;
                default:
                    startDate = new Date(0); // Все время
            }
            
            filtered = filtered.filter(item => {
                const itemDate = new Date(item.start_time);
                return itemDate >= startDate;
            });
        }
        
        return filtered.slice(-limit);
    }

    toggleDebugLogs() {
        this.debugLogsVisible = !this.debugLogsVisible;
        return this.debugLogsVisible;
    }

    clearDebugLogs() {
        this.debugLogs = [];
    }

    getScheduleStats(scheduleId) {
        const schedule = this.getSchedule(scheduleId);
        return schedule?.stats || {};
    }
}