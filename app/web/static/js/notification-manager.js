// notification-manager.js
export class NotificationManager {
    show(message, type = 'info') {
        // Удаляем существующие уведомления
        const existingNotifications = document.querySelectorAll('.alert-notification');
        existingNotifications.forEach(notification => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        });
        
        // Создаем новое уведомление
        const notification = document.createElement('div');
        notification.className = `alert alert-${this.getAlertClass(type)} alert-notification alert-dismissible fade show`;
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            zIndex: '1000',
            minWidth: '300px'
        });
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Авто-скрытие через 5 секунд
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
        
        return notification;
    }

    getAlertClass(type) {
        switch (type) {
            case 'error': return 'danger';
            case 'success': return 'success';
            case 'warning': return 'warning';
            default: return 'info';
        }
    }

    showToast(message, type = 'info', duration = 3000) {
        const toast = this.show(message, type);
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, duration);
        return toast;
    }
}