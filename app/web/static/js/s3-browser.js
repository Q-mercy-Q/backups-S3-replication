/**
 * JavaScript для просмотра и навигации по S3 бакету
 */

// Текущий путь в бакете
let currentPath = '';
let bucketName = '';

// API функции
async function listS3Objects(prefix = '', recursive = false) {
    const params = new URLSearchParams({
        prefix: prefix,
        recursive: recursive.toString()
    });
    
    const response = await fetch(`/api/s3/browser?${params}`);
    const data = await response.json();
    
    if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to list S3 objects');
    }
    
    return data;
}

async function getS3ObjectInfo(objectPath) {
    const params = new URLSearchParams({
        path: objectPath
    });
    
    const response = await fetch(`/api/s3/browser/object?${params}`);
    const data = await response.json();
    
    if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to get object info');
    }
    
    return data.object;
}

async function getS3Stats(prefix = '') {
    const params = new URLSearchParams({
        prefix: prefix
    });
    
    const response = await fetch(`/api/s3/browser/stats?${params}`);
    const data = await response.json();
    
    if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to get stats');
    }
    
    return data.stats;
}

// UI функции
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) return;
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 5000);
}

function renderBreadcrumb(path) {
    const breadcrumbDiv = document.getElementById('breadcrumb');
    if (!breadcrumbDiv) return;
    
    if (!path || path === '.' || path === '') {
        breadcrumbDiv.innerHTML = '<span class="bucket-breadcrumb-item active">Root</span>';
        return;
    }
    
    const parts = path.split('/').filter(p => p);
    let html = '<span class="bucket-breadcrumb-item" data-path="">Root</span>';
    
    let currentPrefix = '';
    parts.forEach((part, index) => {
        currentPrefix += part + '/';
        const isLast = index === parts.length - 1;
        html += ` <i class="fas fa-chevron-right mx-2 text-muted"></i> `;
        html += `<span class="bucket-breadcrumb-item ${isLast ? 'active' : ''}" data-path="${currentPrefix.slice(0, -1)}">${part}</span>`;
    });
    
    breadcrumbDiv.innerHTML = html;
    
    // Добавляем обработчики клика
    breadcrumbDiv.querySelectorAll('.bucket-breadcrumb-item:not(.active)').forEach(item => {
        item.addEventListener('click', () => {
            const path = item.dataset.path || '';
            navigateToPath(path);
        });
    });
}

function renderObjects(data) {
    const tbody = document.getElementById('objectsTableBody');
    const countDiv = document.getElementById('objectCount');
    
    if (!tbody) return;
    
    bucketName = data.bucket || '';
    
    // Отладочная информация для директорий
    if (data.entries) {
        const directories = data.entries.filter(e => e.type === 'directory');
        if (directories.length > 0) {
            console.log('Directories found:', directories.map(d => ({
                name: d.name,
                size: d.size,
                size_human: d.size_human,
                file_count: d.file_count
            })));
        }
    }
    
    if (!data.entries || data.entries.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted py-4">
                    <i class="fas fa-folder-open me-2"></i>This directory is empty
                </td>
            </tr>
        `;
        countDiv.textContent = '0 objects';
        updateSelectedCount(); // Обновляем счетчик выбранных (будет 0)
        return;
    }
    
    let html = '';
    
    data.entries.forEach(entry => {
        const icon = entry.type === 'directory' 
            ? '<i class="fas fa-folder text-warning"></i>' 
            : '<i class="fas fa-file text-primary"></i>';
        
        // Для директорий показываем размер и количество файлов
        let size;
        if (entry.type === 'directory') {
            const fileCount = entry.file_count || 0;
            const sizeHuman = entry.size_human || '0 B';
            const entrySize = entry.size || 0;
            
            // Отображаем статистику если она есть
            if (fileCount > 0 || entrySize > 0) {
                size = `${sizeHuman} (${fileCount} file${fileCount !== 1 ? 's' : ''})`;
            } else {
                size = '0 B (0 files)';
            }
        } else {
            size = entry.size_human || '-';
        }
        
        // Для директорий дата изменения - это дата последнего изменения файлов внутри
        let modified;
        if (entry.type === 'directory') {
            modified = entry.modified 
                ? new Date(entry.modified).toLocaleString()
                : '-';
        } else {
            modified = entry.modified 
                ? new Date(entry.modified).toLocaleString()
                : '-';
        }
        
        // Класс хранения - для директорий показываем определенный класс или "Mixed"
        let storageClass;
        if (entry.type === 'directory') {
            if (entry.storage_class) {
                const badgeClass = entry.storage_class === 'Mixed' ? 'bg-warning' : 'bg-secondary';
                storageClass = `<span class="badge ${badgeClass}">${entry.storage_class}</span>`;
            } else {
                storageClass = '<span class="text-muted">-</span>';
            }
        } else {
            storageClass = entry.storage_class 
                ? `<span class="badge bg-secondary">${entry.storage_class}</span>`
                : '-';
        }
        
        const deleteButton = entry.type === 'file' 
            ? `<button class="btn btn-sm btn-danger delete-object-btn" data-path="${entry.path}" data-name="${entry.name}" data-type="file" title="Delete file">
                <i class="fas fa-trash"></i>
            </button>`
            : `<button class="btn btn-sm btn-danger delete-object-btn" data-path="${entry.path}" data-name="${entry.name}" data-type="directory" title="Delete directory (recursive)">
                <i class="fas fa-trash"></i>
            </button>`;
        
        html += `
            <tr class="s3-object-row" data-path="${entry.path}" data-type="${entry.type}">
                <td>
                    <input type="checkbox" class="form-check-input object-checkbox" 
                           data-path="${entry.path}" 
                           data-name="${entry.name}" 
                           data-type="${entry.type}">
                </td>
                <td class="s3-object-icon">${icon}</td>
                <td>
                    <strong>${entry.name}</strong>
                    ${entry.type === 'directory' ? '<span class="badge bg-info ms-2">DIR</span>' : ''}
                </td>
                <td>${size}</td>
                <td><small>${modified || '-'}</small></td>
                <td>${storageClass}</td>
                <td>${deleteButton}</td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
    countDiv.textContent = `${data.count} ${data.count === 1 ? 'object' : 'objects'}`;
    
    // Обновляем счетчик выбранных элементов
    updateSelectedCount();
    
    // Добавляем обработчики клика
    tbody.querySelectorAll('.s3-object-row').forEach(row => {
        row.addEventListener('click', (e) => {
            // Не обрабатываем клик, если это кнопка удаления или чекбокс
            if (e.target.closest('.delete-object-btn') || e.target.closest('.object-checkbox')) {
                return;
            }
            
            const path = row.dataset.path;
            const type = row.dataset.type;
            
            if (type === 'directory') {
                // Для папки убираем завершающий / если есть, т.к. navigateToPath нормализует путь
                navigateToPath(path.replace(/\/$/, ''));
            } else {
                showObjectDetails(path);
            }
        });
    });
    
    // Добавляем обработчики для чекбоксов
    setupCheckboxes();
    
    // Добавляем обработчики удаления
    tbody.querySelectorAll('.delete-object-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const objectPath = btn.dataset.path;
            const objectName = btn.dataset.name;
            const objectType = btn.dataset.type || 'file';
            const isDirectory = objectType === 'directory';
            
            // Разные сообщения для файлов и директорий
            if (isDirectory) {
                // Для директорий используем стилизованное модальное окно с подтверждением через ввод
                const confirmed = await showConfirmInputModal(
                    'ВЫ УДАЛЯЕТЕ ДИРЕКТОРИЮ',
                    `Директория <strong>"${objectName}"</strong> будет удалена вместе со всем содержимым. Все файлы и поддиректории будут удалены без возможности восстановления.`,
                    'DELETE',
                    'Введите DELETE для подтверждения',
                    'Удалить',
                    'Отмена'
                );
                
                if (!confirmed) {
                    return;
                }
            } else {
                // Для файлов используем стилизованное модальное окно подтверждения
                const confirmed = await showConfirmModal(
                    'Удаление объекта',
                    `Вы уверены, что хотите удалить объект <strong>"${objectName}"</strong>?<br><small class="text-muted">Это действие нельзя отменить.</small>`,
                    'Удалить',
                    'Отмена',
                    'danger'
                );
                
                if (!confirmed) {
                    return;
                }
            }
            
            await deleteObject(objectPath, isDirectory);
        });
    });
}

async function navigateToPath(path) {
    try {
        // Нормализуем путь - убираем завершающий / если есть
        const normalizedPath = path ? path.replace(/\/$/, '') : '';
        currentPath = normalizedPath;
        
        const tbody = document.getElementById('objectsTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                            <td colspan="7" class="text-center text-muted py-4">
                                <i class="fas fa-spinner fa-spin me-2"></i>Loading...
                            </td>
                </tr>
            `;
        }
        
        const data = await listS3Objects(normalizedPath || '', false);
        
        renderBreadcrumb(normalizedPath || '');
        renderObjects(data);
        
        // Обновляем URL (опционально)
        if (normalizedPath) {
            window.history.pushState({path: normalizedPath}, '', `?path=${encodeURIComponent(normalizedPath)}`);
        } else {
            window.history.pushState({path: ''}, '', window.location.pathname);
        }
        
    } catch (error) {
        showAlert(`<i class="fas fa-exclamation-circle me-1"></i>Error: ${error.message}`, 'danger');
        console.error('Navigation error:', error);
    }
}

async function showObjectDetails(objectPath) {
    const modal = new bootstrap.Modal(document.getElementById('objectDetailsModal'));
    const contentDiv = document.getElementById('objectDetailsContent');
    const titleDiv = document.getElementById('objectDetailsModalLabel');
    
    contentDiv.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
    titleDiv.innerHTML = `<i class="fas fa-file me-2"></i>Object Details`;
    modal.show();
    
    try {
        const objectInfo = await getS3ObjectInfo(objectPath);
        
        const modified = objectInfo.modified 
            ? new Date(objectInfo.modified).toLocaleString()
            : 'N/A';
        
        contentDiv.innerHTML = `
            <div class="mb-3">
                <label class="form-label fw-bold">Object Path</label>
                <div class="form-control-plaintext"><code>${objectInfo.path}</code></div>
            </div>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label fw-bold">Size</label>
                    <div class="form-control-plaintext">${objectInfo.size_human} (${objectInfo.size?.toLocaleString()} bytes)</div>
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label fw-bold">Modified</label>
                    <div class="form-control-plaintext">${modified}</div>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label fw-bold">Content Type</label>
                    <div class="form-control-plaintext">${objectInfo.content_type || 'N/A'}</div>
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label fw-bold">ETag</label>
                    <div class="form-control-plaintext"><code>${objectInfo.etag || 'N/A'}</code></div>
                </div>
            </div>
            ${objectInfo.metadata && Object.keys(objectInfo.metadata).length > 0 ? `
            <div class="mb-3">
                <label class="form-label fw-bold">Metadata</label>
                <pre class="bg-light p-3 rounded">${JSON.stringify(objectInfo.metadata, null, 2)}</pre>
            </div>
            ` : ''}
        `;
        
    } catch (error) {
        contentDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle me-2"></i>Error: ${error.message}
            </div>
        `;
    }
}

async function refreshBucket() {
    await navigateToPath(currentPath);
}

async function showBucketStats() {
    try {
        const stats = await getS3Stats(currentPath);
        const statsDiv = document.getElementById('bucketStats');
        
        if (statsDiv) {
            statsDiv.innerHTML = `
                <strong>Total Objects:</strong> ${stats.total_objects?.toLocaleString() || 0}<br>
                <strong>Total Size:</strong> ${stats.total_size_human || '0 B'}
            `;
        }
    } catch (error) {
        showAlert(`<i class="fas fa-exclamation-circle me-1"></i>Error loading stats: ${error.message}`, 'danger');
    }
}

async function deleteObject(objectPath, isDirectory = false, showSuccessAlert = true) {
    try {
        const response = await fetch('/api/s3/browser/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                path: objectPath,
                is_directory: isDirectory
            })
        });
        
        const data = await response.json();
        
        if (!response.ok || data.status === 'error') {
            throw new Error(data.message || 'Failed to delete object');
        }
        
        // Показываем сообщение только если требуется
        if (showSuccessAlert) {
            if (data.status === 'partial') {
                showAlert(
                    `<i class="fas fa-exclamation-triangle me-1"></i>Partially deleted: ${data.deleted_count} objects removed, ${data.error_count} errors occurred`, 
                    'warning'
                );
            } else {
                const message = isDirectory && data.deleted_count !== undefined
                    ? `Directory deleted successfully (${data.deleted_count} objects removed)`
                    : 'Object deleted successfully';
                showAlert(`<i class="fas fa-check-circle me-1"></i>${message}`, 'success');
            }
        }
        
        // Обновляем список объектов только если требуется (для массового удаления обновим один раз)
        if (showSuccessAlert) {
            await refreshBucket();
        }
        
        return { success: true, data };
        
    } catch (error) {
        if (showSuccessAlert) {
            showAlert(`<i class="fas fa-exclamation-circle me-1"></i>Error deleting ${isDirectory ? 'directory' : 'object'}: ${error.message}`, 'danger');
        }
        throw error;
    }
}

// Функции для работы с чекбоксами
function setupCheckboxes() {
    // Обработчик для чекбокса "Select All"
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', (e) => {
            const checkboxes = document.querySelectorAll('.object-checkbox');
            checkboxes.forEach(checkbox => {
                checkbox.checked = e.target.checked;
            });
            updateSelectedCount();
        });
    }
    
    // Обработчики для индивидуальных чекбоксов
    document.querySelectorAll('.object-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            updateSelectedCount();
            updateSelectAllState();
        });
        
        // Предотвращаем всплытие события при клике на чекбокс
        checkbox.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    });
}

function updateSelectedCount() {
    const checkboxes = document.querySelectorAll('.object-checkbox:checked');
    const count = checkboxes.length;
    const selectedCountBadge = document.getElementById('selectedCount');
    const deleteSelectedBtn = document.getElementById('deleteSelectedBtn');
    
    if (count > 0) {
        selectedCountBadge.textContent = `${count} selected`;
        selectedCountBadge.classList.remove('d-none');
        deleteSelectedBtn.classList.remove('d-none');
    } else {
        selectedCountBadge.classList.add('d-none');
        deleteSelectedBtn.classList.add('d-none');
    }
}

function updateSelectAllState() {
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const checkboxes = document.querySelectorAll('.object-checkbox');
    const checkedCount = document.querySelectorAll('.object-checkbox:checked').length;
    
    if (selectAllCheckbox && checkboxes.length > 0) {
        selectAllCheckbox.checked = checkedCount === checkboxes.length;
        selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
    }
}

function getSelectedObjects() {
    const selected = [];
    document.querySelectorAll('.object-checkbox:checked').forEach(checkbox => {
        selected.push({
            path: checkbox.dataset.path,
            name: checkbox.dataset.name,
            type: checkbox.dataset.type
        });
    });
    return selected;
}

async function deleteSelectedObjects() {
    const selected = getSelectedObjects();
    
    if (selected.length === 0) {
        showAlert('<i class="fas fa-exclamation-circle me-1"></i>No objects selected', 'warning');
        return;
    }
    
    // Подсчитываем файлы и директории
    const files = selected.filter(obj => obj.type === 'file');
    const directories = selected.filter(obj => obj.type === 'directory');
    
    // Формируем сообщение подтверждения
    let confirmTitle = 'МАССОВОЕ УДАЛЕНИЕ';
    let confirmMessage = `Вы выбрали для удаления:<br>`;
    
    if (files.length > 0) {
        confirmMessage += `<strong>${files.length}</strong> файл${files.length !== 1 ? 'ов' : ''}<br>`;
    }
    if (directories.length > 0) {
        confirmMessage += `<strong>${directories.length}</strong> директори${directories.length === 1 ? 'ю' : 'й'}<br>`;
    }
    
    confirmMessage += `<br><strong class="text-danger">Все выбранные объекты будут удалены без возможности восстановления.</strong>`;
    
    if (directories.length > 0) {
        confirmMessage += `<br><br><small class="text-warning">⚠️ Внимание: Директории будут удалены вместе со всем содержимым!</small>`;
        confirmTitle = 'МАССОВОЕ УДАЛЕНИЕ (ВКЛЮЧАЯ ДИРЕКТОРИИ)';
    }
    
    const confirmDelete = await showConfirmInputModal(
        confirmTitle,
        confirmMessage,
        'DELETE',
        'Введите DELETE для подтверждения',
        'Удалить',
        'Отмена'
    );
    
    if (!confirmDelete) {
        return;
    }
    
    try {
        showAlert(`<i class="fas fa-spinner fa-spin me-1"></i>Удаление ${selected.length} объектов...`, 'info');
        
        let successCount = 0;
        let errorCount = 0;
        const errors = [];
        
        // Удаляем объекты последовательно
        for (const obj of selected) {
            try {
                await deleteObject(obj.path, obj.type === 'directory', false); // false = не показывать алерт
                successCount++;
            } catch (error) {
                errorCount++;
                errors.push(`${obj.name}: ${error.message}`);
            }
        }
        
        // Очищаем выбранные элементы
        document.querySelectorAll('.object-checkbox').forEach(cb => cb.checked = false);
        updateSelectedCount();
        
        // Показываем результат
        if (errorCount === 0) {
            showAlert(`<i class="fas fa-check-circle me-1"></i>Successfully deleted ${successCount} object${successCount !== 1 ? 's' : ''}`, 'success');
        } else {
            showAlert(
                `<i class="fas fa-exclamation-triangle me-1"></i>Deleted ${successCount} object${successCount !== 1 ? 's' : ''}, ${errorCount} error${errorCount !== 1 ? 's' : ''}. ${errors.slice(0, 3).join(', ')}${errors.length > 3 ? '...' : ''}`,
                'warning'
            );
        }
        
        // Обновляем список
        await refreshBucket();
        
    } catch (error) {
        showAlert(`<i class="fas fa-exclamation-circle me-1"></i>Error during bulk deletion: ${error.message}`, 'danger');
    }
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    // Проверяем путь из URL
    const urlParams = new URLSearchParams(window.location.search);
    const pathParam = urlParams.get('path');
    const initialPath = pathParam ? decodeURIComponent(pathParam) : '';
    
    // Загружаем начальный путь
    navigateToPath(initialPath);
    
    // Обработчики кнопок
    const refreshBtn = document.getElementById('refreshBucket');
    const statsBtn = document.getElementById('showStats');
    const deleteSelectedBtn = document.getElementById('deleteSelectedBtn');
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshBucket);
    }
    
    if (statsBtn) {
        statsBtn.addEventListener('click', showBucketStats);
    }
    
    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', deleteSelectedObjects);
    }
    
    // Обработка кнопки "Назад" в браузере
    window.addEventListener('popstate', (event) => {
        if (event.state && event.state.path !== undefined) {
            navigateToPath(event.state.path);
        }
    });
});

