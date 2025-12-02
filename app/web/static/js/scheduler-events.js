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
        
        // Обработчики для переключения режима фильтрации
        const filterModeRadios = document.querySelectorAll('input[name="scheduleFilterMode"]');
        filterModeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => this.handleFilterModeChange(e));
        });
        
        // Обработчик для кнопки Browse директории
        const browseSourceDirectory = document.getElementById('browseSourceDirectory');
        if (browseSourceDirectory) {
            browseSourceDirectory.addEventListener('click', (e) => this.handleBrowseSourceDirectory(e));
        }
    }
    
    async handleBrowseSourceDirectory(event) {
        event.preventDefault();
        // Открываем простой модальный диалог для просмотра директорий
        const currentPath = document.getElementById('scheduleSourceDirectory')?.value || '';
        const selectedPath = await this.showDirectoryBrowser(currentPath);
        if (selectedPath !== null && selectedPath !== undefined) {
            document.getElementById('scheduleSourceDirectory').value = selectedPath;
        }
    }
    
    async showDirectoryBrowser(initialPath = '') {
        // Используем стилизованное модальное окно для ввода пути
        const result = await showPromptModal(
            'Выбор директории',
            'Введите относительный путь к директории (например, "backups/vm1" или "folder1/subfolder2").<br><small class="text-muted">Оставьте пустым для сканирования всей NFS директории.</small>',
            'Относительный путь',
            initialPath || '',
            'text',
            'Выбрать',
            'Отмена'
        );
        return result || null;
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
            if (isCron) {
                cronSection.classList.remove('d-none');
            } else {
                cronSection.classList.add('d-none');
            }
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
        
        // Добавляем config_id если выбран
        const configSelector = document.getElementById('schedulerConfigSelector');
        if (configSelector && configSelector.value) {
            formData.config_id = parseInt(configSelector.value);
        }

        // Определяем режим фильтрации
        const filterMode = document.querySelector('input[name="scheduleFilterMode"]:checked')?.value || 'categories';
        
        if (filterMode === 'extensions') {
            const extensionsInput = document.getElementById('scheduleFileExtensions')?.value.trim();
            if (extensionsInput) {
                const extensions = extensionsInput.split(',').map(ext => ext.trim()).filter(ext => ext);
                if (extensions.length > 0) {
                    formData.file_extensions = extensions;
                }
            }
        } else {
            const categories = this.getSelectedCategories();
            if (categories.length > 0) {
                formData.categories = categories;
            }
        }
        
        // Добавляем source_directory если указан
        const sourceDirectory = document.getElementById('scheduleSourceDirectory')?.value.trim();
        if (sourceDirectory) {
            formData.source_directory = sourceDirectory;
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
                document.getElementById('cronSection').classList.add('d-none');
                document.getElementById('intervalLabel').textContent = 'Interval';
                document.getElementById('scheduleIntervalValue').value = '1';
                document.getElementById('scheduleIntervalUnit').value = 'hours';
                document.getElementById('scheduleEnabled').checked = true;
                this.resetCategorySelection();
                
                // Сбрасываем поле расширений
                const extensionsInput = document.getElementById('scheduleFileExtensions');
                if (extensionsInput) {
                    extensionsInput.value = '';
                }
                
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
        // Сбрасываем режим фильтрации
        const categoriesRadio = document.getElementById('filterModeCategories');
        if (categoriesRadio) {
            categoriesRadio.checked = true;
        }
        this.handleFilterModeChange({ target: categoriesRadio });
    }
    
    handleFilterModeChange(event) {
        const mode = event.target.value;
        const categoriesRow = document.getElementById('categoriesRow');
        const extensionsRow = document.getElementById('extensionsRow');
        
        if (mode === 'extensions') {
            if (categoriesRow) categoriesRow.classList.add('d-none');
            if (extensionsRow) extensionsRow.classList.remove('d-none');
        } else {
            if (categoriesRow) categoriesRow.classList.remove('d-none');
            if (extensionsRow) extensionsRow.classList.add('d-none');
        }
    }
}