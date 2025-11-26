const state = {
    currentConfig: {},
    currentPath: '.',
    basePath: '',
    categoryOptions: []
};

function showNotification(message, type = 'info') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    alert.role = 'alert';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.body.appendChild(alert);
    setTimeout(() => alert.remove(), 5000);
}

async function apiCall(url, options = {}) {
    const config = {
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
        ...options
    };

    if (config.body && typeof config.body !== 'string') {
        config.body = JSON.stringify(config.body);
    }

    const response = await fetch(url, config);
    const data = await response.json();
    if (!response.ok || data.status === 'error') {
        throw new Error(data.message || `Request failed with status ${response.status}`);
    }
    return data;
}

function collectConfigFromForm() {
    return {
        NFS_PATH: document.getElementById('nfsPath').value.trim(),
        S3_ENDPOINT: document.getElementById('s3Endpoint').value.trim(),
        S3_BUCKET: document.getElementById('s3Bucket').value.trim(),
        S3_ACCESS_KEY: document.getElementById('S3_ACCESS_KEY').value.trim(),
        S3_SECRET_KEY: document.getElementById('S3_SECRET_KEY').value.trim(),
        BACKUP_DAYS: document.getElementById('backupDays').value,
        MAX_THREADS: document.getElementById('maxThreads').value,
        STORAGE_CLASS: document.getElementById('storageClass').value,
        ENABLE_TAPE_STORAGE: document.getElementById('enableTapeStorage').checked ? 'true' : 'false',
        UPLOAD_RETRIES: document.getElementById('uploadRetries').value,
        RETRY_DELAY: document.getElementById('retryDelay').value,
        FILE_CATEGORIES: getSelectedCategories()
    };
}

function getSelectedCategories() {
    return Array.from(document.querySelectorAll('.category-option:checked')).map(input => input.value);
}

function setSelectedCategories(categories = []) {
    const normalized = new Set(categories);
    document.querySelectorAll('.category-option').forEach(input => {
        input.checked = normalized.has(input.value);
    });
}

function updateConfigPreview(config) {
    const preview = document.getElementById('configPreview');
    preview.textContent = JSON.stringify(config, null, 2);
}

async function loadConfiguration() {
    try {
        const config = await apiCall('/api/config');
        state.currentConfig = config;
        state.basePath = config.NFS_PATH || '';
        document.getElementById('nfsPath').value = config.NFS_PATH || '';
        document.getElementById('s3Endpoint').value = config.S3_ENDPOINT || '';
        document.getElementById('s3Bucket').value = config.S3_BUCKET || '';
        document.getElementById('S3_ACCESS_KEY').value = config.S3_ACCESS_KEY || '';
        document.getElementById('S3_SECRET_KEY').value = config.S3_SECRET_KEY || '';
        document.getElementById('backupDays').value = config.BACKUP_DAYS || '7';
        document.getElementById('maxThreads').value = config.MAX_THREADS || '4';
        document.getElementById('storageClass').value = config.STORAGE_CLASS || 'STANDARD';
        document.getElementById('enableTapeStorage').checked = config.ENABLE_TAPE_STORAGE === 'true';
        document.getElementById('uploadRetries').value = config.UPLOAD_RETRIES || '3';
        document.getElementById('retryDelay').value = config.RETRY_DELAY || '5';
        setSelectedCategories(config.FILE_CATEGORIES || []);
        updateConfigPreview(config);
        await loadFileBrowser('.');
        showNotification('Configuration loaded', 'success');
    } catch (error) {
        console.error('Failed to load configuration', error);
        showNotification('Failed to load configuration: ' + error.message, 'error');
    }
}

async function saveConfiguration() {
    try {
        const config = collectConfigFromForm();
        const result = await apiCall('/api/config', {
            method: 'POST',
            body: config
        });
        showNotification(result.message || 'Configuration saved', 'success');
        updateConfigPreview(result.config || config);
    } catch (error) {
        showNotification('Failed to save configuration: ' + error.message, 'error');
    }
}

async function testConnection() {
    try {
        const config = collectConfigFromForm();
        const result = await apiCall('/api/test_connection', {
            method: 'POST',
            body: config
        });
        showNotification(result.message || 'Connection test successful', 'success');
    } catch (error) {
        showNotification('Connection test failed: ' + error.message, 'error');
    }
}

async function scanFiles() {
    try {
        const config = collectConfigFromForm();
        const result = await apiCall('/api/scan_files', {
            method: 'POST',
            body: config
        });
        const status = result.status || 'success';
        showNotification(result.message || 'Scan completed', status === 'warning' ? 'warning' : 'success');
    } catch (error) {
        showNotification('Scan failed: ' + error.message, 'error');
    }
}

async function loadFileBrowser(path = '.') {
    try {
        const params = new URLSearchParams();
        params.set('path', path);
        const result = await apiCall(`/api/files?${params.toString()}`, { method: 'GET' });
        state.currentPath = result.path || '.';
        renderFileBrowser(result);
    } catch (error) {
        console.error('Failed to load file browser', error);
        showNotification('Failed to load files: ' + error.message, 'error');
    }
}

function renderFileBrowser(data) {
    const body = document.getElementById('fileBrowserBody');
    const pathDisplay = document.getElementById('fileBrowserPath');
    const relativePath = data.path === '.' ? '' : data.path;
    pathDisplay.textContent = state.basePath ? `${state.basePath}/${relativePath}`.replace(/\/+/g, '/') : relativePath || '.';

    if (!data.entries || data.entries.length === 0) {
        body.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-3">Directory is empty</td></tr>';
        return;
    }

    body.innerHTML = '';
    data.entries.forEach(entry => {
        const row = document.createElement('tr');
        row.className = entry.type === 'directory' ? 'table-active cursor-pointer' : '';
        row.innerHTML = `
            <td>
                <i class="fas fa-${entry.type === 'directory' ? 'folder text-warning' : 'file text-secondary'} me-2"></i>
                ${entry.name}
            </td>
            <td>${entry.type === 'file' ? (entry.size_human || entry.size || '-') : '-'}</td>
            <td>${entry.modified || '-'}</td>
        `;
        if (entry.type === 'directory') {
            row.style.cursor = 'pointer';
            row.addEventListener('click', () => navigateTo(entry.relative_path));
        }
        if (entry.type === 'file') {
            row.classList.add('text-muted');
        }
        body.appendChild(row);
    });
}

function navigateTo(relativePath) {
    loadFileBrowser(relativePath);
}

function navigateUp() {
    if (state.currentPath === '.' || !state.currentPath) return;
    const segments = state.currentPath.split('/').filter(Boolean);
    segments.pop();
    const newPath = segments.join('/') || '.';
    loadFileBrowser(newPath);
}

function setupCategoryInteractions() {
    const selected = new Set(state.currentConfig.FILE_CATEGORIES || []);
    document.querySelectorAll('.category-option').forEach(option => {
        if (selected.size === 0) {
            option.checked = true;
        } else {
            option.checked = selected.has(option.value);
        }
    });
}

function setupEventListeners() {
    document.getElementById('saveConfig').addEventListener('click', (e) => {
        e.preventDefault();
        saveConfiguration();
    });

    document.getElementById('resetConfig').addEventListener('click', (e) => {
        e.preventDefault();

        loadConfiguration();
    });

    document.getElementById('configTestConnection').addEventListener('click', (e) => {
        e.preventDefault();
        testConnection();
    });

    document.getElementById('configScanFiles').addEventListener('click', (e) => {
        e.preventDefault();
        scanFiles();
    });

    document.getElementById('fileBrowserUp').addEventListener('click', (e) => {
        e.preventDefault();
        navigateUp();
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    setupEventListeners();
    await loadConfiguration();
    setupCategoryInteractions();
});

