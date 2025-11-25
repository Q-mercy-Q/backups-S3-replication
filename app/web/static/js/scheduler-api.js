// scheduler-api.js
export class SchedulerAPI {
    constructor() {
        this.baseURL = '';
    }

    async request(endpoint, options = {}) {
        try {
            const config = {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            };

            if (config.body && typeof config.body !== 'string') {
                config.body = JSON.stringify(config.body);
            }

            const response = await fetch(endpoint, config);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (result.status === 'error') {
                throw new Error(result.message);
            }

            return result;
        } catch (error) {
            console.error(`API request failed for ${endpoint}:`, error);
            throw error;
        }
    }

    async loadSchedulerStats() {
        return await this.request('/api/scheduler/stats');
    }

    async loadSchedules() {
        return await this.request('/api/scheduler/schedules');
    }

    async loadSyncHistory(filter = 'all', limit = 50, period = 'all') {
        let url = `/api/scheduler/history?limit=${limit}`;
        if (filter && filter !== 'all') {
            url += `&schedule=${encodeURIComponent(filter)}`;
        }
        if (period && period !== 'all') {
            url += `&period=${period}`;
        }
        
        return await this.request(url);
    }

    async loadDebugLogs(level = 'INFO', limit = 100) {
        const result = await this.request(`/api/scheduler/debug_logs?level=${level}&limit=${limit}`);
        return result.logs || [];
    }

    async clearDebugLogs() {
        return await this.request('/api/scheduler/debug_logs', { method: 'DELETE' });
    }

    async addSchedule(scheduleData) {
        return await this.request('/api/scheduler/schedules', {
            method: 'POST',
            body: scheduleData
        });
    }

    async runSchedule(scheduleId) {
        return await this.request(`/api/scheduler/run/${scheduleId}`, {
            method: 'POST'
        });
    }

    async toggleSchedule(scheduleId, enabled) {
        return await this.request(`/api/scheduler/schedules/${scheduleId}`, {
            method: 'PUT',
            body: { enabled }
        });
    }

    async deleteSchedule(scheduleId) {
        return await this.request(`/api/scheduler/schedules/${scheduleId}`, {
            method: 'DELETE'
        });
    }
}