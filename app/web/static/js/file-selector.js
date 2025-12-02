/**
 * JavaScript для расширенного выбора файлов и фильтрации
 */

// Состояние выбранных файлов
let selectedFiles = [];
let currentUploadMode = 'auto';

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    // Обработчики переключения режима
    const modeRadios = document.querySelectorAll('input[name="uploadMode"]');
    modeRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            currentUploadMode = e.target.value;
            updateModePanels();
        });
    });
    
    // Кнопка открытия файлового браузера
    const openFileBrowserBtn = document.getElementById('openFileBrowser');
    if (openFileBrowserBtn) {
        openFileBrowserBtn.addEventListener('click', () => {
            // Открываем файловый браузер в модальном окне
            showFileBrowserModal();
        });
    }
    
    // Кнопка сканирования с фильтрами
    const scanWithFiltersBtn = document.getElementById('scanWithFilters');
    if (scanWithFiltersBtn) {
        scanWithFiltersBtn.addEventListener('click', () => {
            scanWithFilters();
        });
    }
    
    updateModePanels();
});

function updateModePanels() {
    const filterPanel = document.getElementById('filterPanel');
    const manualPanel = document.getElementById('manualPanel');
    
    if (filterPanel) {
        if (currentUploadMode === 'filter') {
            filterPanel.classList.remove('d-none');
        } else {
            filterPanel.classList.add('d-none');
        }
    }
    
    if (manualPanel) {
        if (currentUploadMode === 'manual') {
            manualPanel.classList.remove('d-none');
        } else {
            manualPanel.classList.add('d-none');
        }
    }
}

async function scanWithFilters() {
    const extensions = document.getElementById('fileExtensions').value;
    const minSize = document.getElementById('minSize').value;
    const maxSize = document.getElementById('maxSize').value;
    const backupDays = document.getElementById('backupDaysFilter').value;
    const skipTimeFilter = document.getElementById('skipTimeFilter').checked;
    
    try {
        const params = new URLSearchParams();
        
        if (extensions) {
            extensions.split(',').forEach(ext => {
                params.append('extensions', ext.trim());
            });
        }
        
        if (minSize) {
            params.append('min_size', parseInt(minSize) * 1024 * 1024); // Convert MB to bytes
        }
        
        if (maxSize) {
            params.append('max_size', parseInt(maxSize) * 1024 * 1024); // Convert MB to bytes
        }
        
        if (backupDays) {
            params.append('backup_days', parseInt(backupDays));
        }
        
        if (skipTimeFilter) {
            params.append('skip_time', 'true');
        }
        
        const response = await fetch(`/api/files/scan?${params.toString()}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            // Показываем найденные файлы для выбора
            showFilesForSelection(data.files);
            showAlert(`Found ${data.count} files (${data.total_size_human})`, 'success');
        } else {
            showAlert(data.message || 'Error scanning files', 'danger');
        }
    } catch (error) {
        showAlert(`Error: ${error.message}`, 'danger');
        console.error('Scan with filters error:', error);
    }
}

function showFileBrowserModal() {
    // Создаем модальное окно для выбора файлов
    const modalHtml = `
        <div class="modal fade" id="fileBrowserModal" tabindex="-1" aria-labelledby="fileBrowserModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="fileBrowserModalLabel">
                            <i class="fas fa-folder-open me-2"></i>Select Files
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <div class="d-flex justify-content-between align-items-center">
                                <span id="fileBrowserPath"></span>
                                <button class="btn btn-sm btn-outline-secondary" id="fileBrowserUpBtn">
                                    <i class="fas fa-level-up-alt me-1"></i>Up
                                </button>
                            </div>
                        </div>
                        <div class="table-responsive" style="max-height: 500px; overflow-y: auto;">
                            <table class="table table-sm table-hover">
                                <thead class="table-light sticky-top">
                                    <tr>
                                        <th style="width: 40px;">
                                            <input type="checkbox" id="selectAllFiles">
                                        </th>
                                        <th>Name</th>
                                        <th style="width: 120px;">Size</th>
                                        <th style="width: 180px;">Modified</th>
                                    </tr>
                                </thead>
                                <tbody id="fileBrowserTableBody">
                                    <tr>
                                        <td colspan="4" class="text-center text-muted py-3">Loading...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="confirmFileSelection">
                            <i class="fas fa-check me-1"></i>Select Files
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Удаляем предыдущее модальное окно если есть
    const existingModal = document.getElementById('fileBrowserModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Добавляем модальное окно
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Ждем, пока элементы будут в DOM
    setTimeout(() => {
        const modal = new bootstrap.Modal(document.getElementById('fileBrowserModal'));
        
        // Загружаем файлы
        loadFilesForSelection('.');
        
        // Обработчики событий
        const upBtn = document.getElementById('fileBrowserUpBtn');
        if (upBtn) {
            upBtn.addEventListener('click', () => {
                navigateFilesUp();
            });
        }
        
        const selectAllCheckbox = document.getElementById('selectAllFiles');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                const checkboxes = document.querySelectorAll('#fileBrowserTableBody input[type="checkbox"]');
                checkboxes.forEach(cb => cb.checked = e.target.checked);
            });
        }
        
        const confirmBtn = document.getElementById('confirmFileSelection');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                confirmFileSelection(modal);
            });
        }
        
        // Обработчик закрытия модального окна
        const modalElement = document.getElementById('fileBrowserModal');
        if (modalElement) {
            modalElement.addEventListener('hidden.bs.modal', () => {
                // Очищаем модальное окно при закрытии
                modalElement.remove();
            });
        }
        
        modal.show();
    }, 10);
}

async function loadFilesForSelection(path = '.') {
    try {
        const params = new URLSearchParams({ path });
        const response = await fetch(`/api/files?${params.toString()}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            renderFilesForSelection(data);
        } else {
            showAlert(data.message || 'Error loading files', 'danger');
        }
    } catch (error) {
        showAlert(`Error: ${error.message}`, 'danger');
        console.error('Load files error:', error);
    }
}

function renderFilesForSelection(data) {
    const tbody = document.getElementById('fileBrowserTableBody');
    const pathDisplay = document.getElementById('fileBrowserPath');
    
    if (!tbody) return;
    
    if (pathDisplay) {
        pathDisplay.textContent = data.path === '.' ? '/' : data.path;
    }
    
    if (!data.entries || data.entries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">Directory is empty</td></tr>';
        return;
    }
    
    let html = '';
    data.entries.forEach(entry => {
        // Экранируем путь для безопасности
        const safePath = entry.relative_path.replace(/'/g, "\\'");
        
        if (entry.type === 'directory') {
            html += `
                <tr class="table-active" style="cursor: pointer;" data-path="${safePath}">
                    <td></td>
                    <td>
                        <i class="fas fa-folder text-warning me-2"></i>${entry.name}
                    </td>
                    <td>-</td>
                    <td>-</td>
                </tr>
            `;
        } else {
            html += `
                <tr>
                    <td>
                        <input type="checkbox" class="file-checkbox" data-path="${safePath}" 
                               data-size="${entry.size || 0}">
                    </td>
                    <td>
                        <i class="fas fa-file text-secondary me-2"></i>${entry.name}
                    </td>
                    <td>${entry.size_human || '-'}</td>
                    <td>${entry.modified ? new Date(entry.modified).toLocaleString() : '-'}</td>
                </tr>
            `;
        }
    });
    
    tbody.innerHTML = html;
    
    // Добавляем обработчики кликов для папок
    tbody.querySelectorAll('tr.table-active').forEach(row => {
        row.addEventListener('click', (e) => {
            if (e.target.type !== 'checkbox') {
                const path = row.dataset.path;
                if (path) {
                    navigateToFile(path);
                }
            }
        });
    });
    
    // Сохраняем текущий путь для навигации
    window.currentSelectionPath = data.path;
    window.currentSelectionParent = data.parent;
}

function navigateToFile(relativePath) {
    loadFilesForSelection(relativePath);
}

// Делаем функцию глобальной для использования в onclick
window.navigateToFile = navigateToFile;

function navigateFilesUp() {
    if (window.currentSelectionParent !== null) {
        loadFilesForSelection(window.currentSelectionParent || '.');
    }
}

function confirmFileSelection(modal) {
    const checkboxes = document.querySelectorAll('#fileBrowserTableBody input[type="checkbox"]:checked');
    const selected = [];
    
    checkboxes.forEach(cb => {
        selected.push({
            path: cb.dataset.path,
            size: parseInt(cb.dataset.size || 0)
        });
    });
    
    if (selected.length === 0) {
        showAlert('Please select at least one file', 'warning');
        return;
    }
    
    // Добавляем выбранные файлы
    selectedFiles = selectedFiles.concat(selected);
    
    // Обновляем отображение
    updateSelectedFilesList();
    
    modal.hide();
    showAlert(`Added ${selected.length} file(s) to selection`, 'success');
}

function showFilesForSelection(files) {
    selectedFiles = files.map(f => ({
        path: f.path,
        size: f.size || 0
    }));
    updateSelectedFilesList();
}

function updateSelectedFilesList() {
    const listDiv = document.getElementById('selectedFilesList');
    const summaryDiv = document.getElementById('selectedFilesSummary');
    const countSpan = document.getElementById('selectedCount');
    const sizeSpan = document.getElementById('selectedSize');
    
    if (!listDiv) return;
    
    if (selectedFiles.length === 0) {
        listDiv.innerHTML = '<p class="text-muted">No files selected. Use "Browse Files" to select files.</p>';
        if (summaryDiv) summaryDiv.classList.add('d-none');
        return;
    }
    
    // Отображаем список файлов
    let html = '<div class="list-group">';
    selectedFiles.forEach((file, index) => {
        const fileName = file.path.split('/').pop();
        html += `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <i class="fas fa-file text-secondary me-2"></i>
                    <small>${file.path}</small>
                </div>
                <div>
                    <small class="text-muted me-2">${formatSize(file.size)}</small>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeSelectedFile(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    listDiv.innerHTML = html;
    
    // Обновляем сводку
    if (summaryDiv) {
        const totalSize = selectedFiles.reduce((sum, f) => sum + (f.size || 0), 0);
        if (countSpan) countSpan.textContent = selectedFiles.length;
        if (sizeSpan) sizeSpan.textContent = formatSize(totalSize);
        summaryDiv.classList.remove('d-none');
    }
}

function removeSelectedFile(index) {
    selectedFiles.splice(index, 1);
    updateSelectedFilesList();
}

function formatSize(bytes) {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(2)} ${units[unitIndex]}`;
}

function showAlert(message, type = 'info') {
    // Используем существующую функцию showAlert если есть, иначе создаем свою
    if (typeof window.showNotification === 'function') {
        window.showNotification(message, type);
    } else if (typeof window.showAlert === 'function') {
        window.showAlert(message, type);
    } else {
        // Простое уведомление через alert или создание элемента
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
        alertDiv.style.zIndex = '9999';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alertDiv);
        setTimeout(() => alertDiv.remove(), 5000);
    }
}

// Экспортируем функции для использования в других модулях
window.selectedFiles = () => selectedFiles;
window.clearSelectedFiles = () => {
    selectedFiles = [];
    updateSelectedFilesList();
};
window.getCurrentUploadMode = () => currentUploadMode;

