// format-utils.js
export class FormatUtils {
    static formatFileSize(bytes) {
        if (!bytes || bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    static formatDuration(seconds) {
        if (!seconds) return '0s';
        if (seconds < 60) {
            return seconds.toFixed(1) + 's';
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return minutes + 'm ' + secs + 's';
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return hours + 'h ' + minutes + 'm';
        }
    }

    static convertToMinutes(value, unit) {
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

    static formatIntervalForDisplay(schedule) {
        if (!schedule) return 'Unknown';
        
        if (schedule.schedule_type === 'cron' || schedule.type === 'cron') {
            return `Cron: ${schedule.interval}`;
        }
        
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
}