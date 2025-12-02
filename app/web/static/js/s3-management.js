/**
 * JavaScript для страницы расширенного управления S3 хранилищем
 */

// Глобальное состояние
const state = {
    buckets: [],
    currentBucket: null,
    bucketInfo: null
};

// Утилиты для уведомлений
function showNotification(message, type = 'info') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    alert.style.zIndex = '9999';
    alert.role = 'alert';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.body.appendChild(alert);
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// API функции
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        const data = await response.json();
        if (!response.ok || data.status === 'error') {
            throw new Error(data.message || 'API request failed');
        }
        return data;
    } catch (error) {
        console.error('API call error:', error);
        throw error;
    }
}

// Bucket Management
async function loadBuckets() {
    try {
        const data = await apiCall('/api/s3-management/buckets');
        state.buckets = data.buckets || [];
        renderBuckets();
        updateBucketSelects();
    } catch (error) {
        showNotification(`Error loading buckets: ${error.message}`, 'error');
        document.getElementById('bucketsList').innerHTML = `
            <div class="col-12">
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>Failed to load buckets: ${error.message}
                </div>
            </div>
        `;
    }
}

function renderBuckets() {
    const container = document.getElementById('bucketsList');
    if (!container) return;

    if (state.buckets.length === 0) {
        container.innerHTML = `
            <div class="col-12">
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>No buckets found. Create your first bucket to get started.
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = state.buckets.map(bucket => `
        <div class="col-md-4 mb-3">
            <div class="card bucket-card h-100">
                <div class="card-body">
                    <h5 class="card-title">
                        <i class="fas fa-folder text-primary me-2"></i>${bucket.name}
                    </h5>
                    <p class="text-muted small mb-2">
                        <i class="fas fa-calendar me-1"></i>
                        Created: ${bucket.creation_date ? new Date(bucket.creation_date).toLocaleDateString() : 'Unknown'}
                    </p>
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="badge bg-secondary stat-badge">
                            <i class="fas fa-file me-1"></i>${bucket.object_count || 0} objects
                        </span>
                        <span class="badge bg-info stat-badge">
                            <i class="fas fa-hdd me-1"></i>${formatBytes(bucket.size || 0)}
                        </span>
                    </div>
                </div>
                <div class="card-footer bg-transparent border-top-0">
                    <div class="btn-group w-100" role="group">
                        <button class="btn btn-sm btn-primary" onclick="viewBucketInfo('${bucket.name}')">
                            <i class="fas fa-info-circle me-1"></i>Info
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteBucketConfirm('${bucket.name}')">
                            <i class="fas fa-trash me-1"></i>Delete
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function updateBucketSelects() {
    const tabs = ['versioning', 'lifecycle', 'policy', 'cors', 'tags', 'analytics'];

    tabs.forEach(tab => {
        const selectId = `${tab}BucketSelect`;
        const gridId = `${tab}BucketGrid`;

        // Обновляем скрытый select (для обратной совместимости)
        const select = document.getElementById(selectId);
        if (select) {
            const currentValue = select.value;
            while (select.options.length > 1) {
                select.remove(1);
            }
            state.buckets.forEach(bucket => {
                const option = document.createElement('option');
                option.value = bucket.name;
                option.textContent = bucket.name;
                select.appendChild(option);
            });
            if (currentValue && state.buckets.some(b => b.name === currentValue)) {
                select.value = currentValue;
            }
        }

        // Обновляем плитки бакетов
        const grid = document.getElementById(gridId);
        if (!grid) return;

        // Сохраняем текущее выбранное значение
        const currentBucketName = grid.dataset.selectedBucket || '';

        // Очищаем grid
        grid.innerHTML = '';

        if (state.buckets.length === 0) {
            grid.innerHTML = '<div class="col-12 text-center text-muted">No buckets available</div>';
            return;
        }

        // Добавляем плитки бакетов
        state.buckets.forEach(bucket => {
            const tile = document.createElement('div');
            tile.className = `bucket-tile ${currentBucketName === bucket.name ? 'selected' : ''}`;
            tile.onclick = () => selectBucketForTab(tab, bucket.name);
            tile.innerHTML = `
                <div class="bucket-icon">
                    <i class="fas fa-folder"></i>
                </div>
                <div class="bucket-info">
                    <div class="bucket-name">${bucket.name}</div>
                    <div class="bucket-meta">
                        <span><i class="fas fa-file"></i> ${bucket.object_count || 0} objects</span>
                        <span><i class="fas fa-hdd"></i> ${formatBytes(bucket.size || 0)}</span>
                    </div>
                </div>
            `;
            grid.appendChild(tile);
        });
    });
}

// Функция для загрузки конфигурации бакета
async function loadBucketConfig(tab, bucketName) {
    try {
        switch(tab) {
            case 'versioning':
                await loadVersioningConfig(bucketName);
                break;
            case 'lifecycle':
                await loadLifecycleConfig(bucketName);
                break;
            case 'policy':
                await loadPolicyConfig(bucketName);
                break;
            case 'cors':
                await loadCorsConfig(bucketName);
                break;
            case 'tags':
                await loadTagsConfig(bucketName);
                break;
            case 'analytics':
                await loadAnalytics(bucketName);
                break;
        }
    } catch (error) {
        console.error(`Error loading ${tab} config:`, error);
        showNotification(`Error loading ${tab} configuration: ${error.message}`, 'error');
    }
}

// Функция для выбора бакета для конкретной вкладки
function selectBucketForTab(tab, bucketName) {
    const bucket = state.buckets.find(b => b.name === bucketName);
    if (!bucket) return;

    const gridId = `${tab}BucketGrid`;
    const selectId = `${tab}BucketSelect`;
    // Для analytics используется analyticsContent, для остальных - tabConfig
    const configId = tab === 'analytics' ? 'analyticsContent' : `${tab}Config`;

    // Обновляем скрытый select
    const select = document.getElementById(selectId);
    if (select) {
        select.value = bucketName;
        // Триггерим событие change для обратной совместимости
        select.dispatchEvent(new Event('change'));
    }

    // Обновляем выделение в плитках
    const grid = document.getElementById(gridId);
    if (grid) {
        grid.dataset.selectedBucket = bucketName;
        const tiles = grid.querySelectorAll('.bucket-tile');
        tiles.forEach(tile => {
            const tileBucketName = tile.querySelector('.bucket-name')?.textContent;
            tile.classList.toggle('selected', tileBucketName === bucketName);
        });
    }

    // Показываем конфигурацию
    const config = document.getElementById(configId);
    if (config) {
        config.classList.add('active');
    }

    // Загружаем конфигурацию для выбранного бакета
    loadBucketConfig(tab, bucketName);
}

// Функция для фильтрации плиток бакетов
function filterBucketTiles(tab) {
    const gridId = `${tab}BucketGrid`;
    const searchId = `${tab}BucketSearch`;
    
    const grid = document.getElementById(gridId);
    const search = document.getElementById(searchId);
    
    if (!grid || !search) return;
    
    const searchTerm = search.value.toLowerCase();
    const tiles = grid.querySelectorAll('.bucket-tile');
    
    tiles.forEach(tile => {
        const bucketName = tile.querySelector('.bucket-name')?.textContent.toLowerCase() || '';
        if (bucketName.includes(searchTerm)) {
            tile.classList.remove('d-none');
        } else {
            tile.classList.add('d-none');
        }
    });
}

async function createBucket(name, location = 'us-east-1') {
    try {
        const data = await apiCall('/api/s3-management/buckets', {
            method: 'POST',
            body: JSON.stringify({ name, location })
        });
        showNotification(data.message || 'Bucket created successfully', 'success');
        await loadBuckets();
        bootstrap.Modal.getInstance(document.getElementById('createBucketModal')).hide();
        document.getElementById('newBucketName').value = '';
    } catch (error) {
        showNotification(`Error creating bucket: ${error.message}`, 'error');
    }
}

async function deleteBucket(name, force = false) {
    try {
        const data = await apiCall(`/api/s3-management/buckets/${encodeURIComponent(name)}`, {
            method: 'DELETE',
            body: JSON.stringify({ force })
        });
        showNotification(data.message || 'Bucket deleted successfully', 'success');
        await loadBuckets();
    } catch (error) {
        showNotification(`Error deleting bucket: ${error.message}`, 'error');
    }
}

async function deleteBucketConfirm(bucketName) {
    if (typeof showConfirmInputModal === 'undefined') {
        if (!confirm(`Are you sure you want to delete bucket "${bucketName}"? This action cannot be undone.`)) {
            return;
        }
        await deleteBucket(bucketName, false);
        return;
    }

    const confirmed = await showConfirmInputModal(
        'DELETE BUCKET',
        `Вы уверены, что хотите удалить бакет "${bucketName}"?<br><br><strong class="text-danger">Это действие нельзя отменить!</strong>`,
        'DELETE',
        'Введите DELETE для подтверждения',
        'Удалить',
        'Отмена'
    );

    if (confirmed) {
        await deleteBucket(bucketName, false);
    }
}

async function viewBucketInfo(bucketName) {
    try {
        state.currentBucket = bucketName;
        const data = await apiCall(`/api/s3-management/buckets/${encodeURIComponent(bucketName)}`);
        state.bucketInfo = data.bucket;
        
        // Показываем модальное окно с информацией
        showBucketInfoModal(state.bucketInfo);
    } catch (error) {
        showNotification(`Error loading bucket info: ${error.message}`, 'error');
    }
}

function showBucketInfoModal(info) {
    // Создаем модальное окно с информацией о бакете
    const modalHTML = `
        <div class="modal fade" id="bucketInfoModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-info-circle me-2"></i>Bucket Information: ${info.name}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <dl class="row">
                            <dt class="col-sm-3">Name:</dt>
                            <dd class="col-sm-9">${info.name}</dd>
                            
                            <dt class="col-sm-3">Creation Date:</dt>
                            <dd class="col-sm-9">${info.creation_date ? new Date(info.creation_date).toLocaleString() : 'Unknown'}</dd>
                            
                            <dt class="col-sm-3">Versioning:</dt>
                            <dd class="col-sm-9">
                                <span class="badge ${info.versioning === 'Enabled' ? 'bg-success' : 'bg-secondary'}">
                                    ${info.versioning || 'Disabled'}
                                </span>
                            </dd>
                            
                            <dt class="col-sm-3">Lifecycle Rules:</dt>
                            <dd class="col-sm-9">${info.lifecycle ? info.lifecycle.length : 0} rule(s)</dd>
                            
                            <dt class="col-sm-3">CORS Rules:</dt>
                            <dd class="col-sm-9">${info.cors ? info.cors.length : 0} rule(s)</dd>
                            
                            <dt class="col-sm-3">Tags:</dt>
                            <dd class="col-sm-9">
                                ${Object.keys(info.tags || {}).length > 0 
                                    ? Object.entries(info.tags).map(([k, v]) => `<span class="badge bg-primary me-1">${k}: ${v}</span>`).join('')
                                    : 'No tags'}
                            </dd>
                        </dl>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Удаляем старое модальное окно если есть
    const oldModal = document.getElementById('bucketInfoModal');
    if (oldModal) {
        oldModal.remove();
    }
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = new bootstrap.Modal(document.getElementById('bucketInfoModal'));
    modal.show();
}

// Versioning
async function loadVersioningConfig(bucketName) {
    try {
        const data = await apiCall(`/api/s3-management/buckets/${encodeURIComponent(bucketName)}`);
        const bucket = data.bucket;
        
        document.getElementById('enableVersioning').checked = bucket.versioning === 'Enabled';
        document.getElementById('enableMfaDelete').checked = bucket.versioning_mfa_delete === 'Enabled';
        document.getElementById('versioningConfig').classList.add('active');
    } catch (error) {
        showNotification(`Error loading versioning config: ${error.message}`, 'error');
    }
}

async function saveVersioningConfig(bucketName) {
    try {
        const enabled = document.getElementById('enableVersioning').checked;
        const mfaDelete = document.getElementById('enableMfaDelete').checked;
        
        await apiCall(`/api/s3-management/buckets/${encodeURIComponent(bucketName)}/versioning`, {
            method: 'PUT',
            body: JSON.stringify({ enabled, mfa_delete: mfaDelete })
        });
        
        showNotification('Versioning settings saved successfully', 'success');
    } catch (error) {
        showNotification(`Error saving versioning config: ${error.message}`, 'error');
    }
}

// Lifecycle
const lifecycleRules = [];

async function loadLifecycleConfig(bucketName) {
    try {
        const data = await apiCall(`/api/s3-management/buckets/${encodeURIComponent(bucketName)}`);
        const bucket = data.bucket;
        
        lifecycleRules.length = 0;
        lifecycleRules.push(...(bucket.lifecycle || []));
        renderLifecycleRules();
        document.getElementById('lifecycleConfig').classList.add('active');
    } catch (error) {
        showNotification(`Error loading lifecycle config: ${error.message}`, 'error');
    }
}

function renderLifecycleRules() {
    const container = document.getElementById('lifecycleRulesList');
    if (!container) return;
    
    if (lifecycleRules.length === 0) {
        container.innerHTML = '<p class="text-muted">No lifecycle rules configured. Click "Add Rule" to create one.</p>';
        return;
    }
    
    container.innerHTML = lifecycleRules.map((rule, index) => `
        <div class="card mb-3 lifecycle-rule-card" data-index="${index}">
            <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                    <strong>${rule.Id || 'Untitled Rule'}</strong>
                    <span class="badge ${rule.Status === 'Enabled' ? 'bg-success' : 'bg-secondary'} ms-2">${rule.Status || 'Disabled'}</span>
                </div>
                <div>
                    <button class="btn btn-sm btn-primary me-1" onclick="editLifecycleRule(${index})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteLifecycleRule(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="card-body">
                ${rule.Filter?.Prefix ? `<p><strong>Prefix:</strong> ${rule.Filter.Prefix}</p>` : ''}
                ${rule.Transitions && rule.Transitions.length > 0 ? `
                    <p><strong>Transitions:</strong></p>
                    <ul>
                        ${rule.Transitions.map(t => `<li>After ${t.Days} days → ${t.StorageClass}</li>`).join('')}
                    </ul>
                ` : ''}
                ${rule.Expiration?.Days ? `<p><strong>Expiration:</strong> After ${rule.Expiration.Days} days</p>` : ''}
                ${rule.Expiration?.Date ? `<p><strong>Expiration Date:</strong> ${rule.Expiration.Date}</p>` : ''}
            </div>
        </div>
    `).join('');
}

function openLifecycleRuleModal(ruleIndex = null) {
    const modal = new bootstrap.Modal(document.getElementById('lifecycleRuleModal'));
    const rule = ruleIndex !== null ? lifecycleRules[ruleIndex] : null;
    
    if (rule) {
        document.getElementById('lifecycleRuleId').value = rule.Id || '';
        document.getElementById('lifecycleRuleStatus').value = rule.Status || 'Enabled';
        document.getElementById('lifecyclePrefix').value = rule.Filter?.Prefix || '';
        document.getElementById('expirationDays').value = rule.Expiration?.Days || '';
        document.getElementById('expirationDate').value = rule.Expiration?.Date || '';
        document.getElementById('deleteMarkerExpiration').checked = rule.Expiration?.ExpiredObjectDeleteMarker || false;
        
        // Render transitions
        renderTransitions(rule.Transitions || []);
    } else {
        // Clear form
        document.getElementById('lifecycleRuleId').value = '';
        document.getElementById('lifecycleRuleStatus').value = 'Enabled';
        document.getElementById('lifecyclePrefix').value = '';
        document.getElementById('expirationDays').value = '';
        document.getElementById('expirationDate').value = '';
        document.getElementById('deleteMarkerExpiration').checked = false;
        document.getElementById('lifecycleTransitionsList').innerHTML = '';
    }
    
    currentEditingRuleIndex = ruleIndex;
    modal.show();
}

let currentEditingRuleIndex = null;
let currentTransitions = [];

function renderTransitions(transitions) {
    currentTransitions = [...transitions];
    const container = document.getElementById('lifecycleTransitionsList');
    if (!container) return;
    
    if (transitions.length === 0) {
        container.innerHTML = '<p class="text-muted small">No transitions configured</p>';
        return;
    }
    
    container.innerHTML = transitions.map((t, i) => `
        <div class="d-flex justify-content-between align-items-center mb-2 p-2 bg-light rounded">
            <span>After <strong>${t.Days}</strong> days → <strong>${t.StorageClass}</strong></span>
            <button class="btn btn-sm btn-danger" onclick="removeTransition(${i})">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `).join('');
}

function removeTransition(index) {
    currentTransitions.splice(index, 1);
    renderTransitions(currentTransitions);
}

function saveLifecycleRuleFromModal() {
    const ruleId = document.getElementById('lifecycleRuleId').value.trim();
    if (!ruleId) {
        showNotification('Rule ID is required', 'warning');
        return;
    }
    
    const rule = {
        Id: ruleId,
        Status: document.getElementById('lifecycleRuleStatus').value,
        Filter: {}
    };
    
    const prefix = document.getElementById('lifecyclePrefix').value.trim();
    if (prefix) {
        rule.Filter.Prefix = prefix;
    }
    
    if (currentTransitions.length > 0) {
        rule.Transitions = currentTransitions;
    }
    
    const expirationDays = document.getElementById('expirationDays').value;
    const expirationDate = document.getElementById('expirationDate').value;
    const deleteMarkerExpiration = document.getElementById('deleteMarkerExpiration').checked;
    
    if (expirationDays || expirationDate || deleteMarkerExpiration) {
        rule.Expiration = {};
        if (expirationDays) rule.Expiration.Days = parseInt(expirationDays);
        if (expirationDate) rule.Expiration.Date = expirationDate;
        if (deleteMarkerExpiration) rule.Expiration.ExpiredObjectDeleteMarker = true;
    }
    
    if (currentEditingRuleIndex !== null) {
        lifecycleRules[currentEditingRuleIndex] = rule;
    } else {
        lifecycleRules.push(rule);
    }
    
    renderLifecycleRules();
    bootstrap.Modal.getInstance(document.getElementById('lifecycleRuleModal')).hide();
    currentEditingRuleIndex = null;
}

async function saveLifecycleConfig(bucketName) {
    try {
        await apiCall(`/api/s3-management/buckets/${encodeURIComponent(bucketName)}/lifecycle`, {
            method: 'PUT',
            body: JSON.stringify({ rules: lifecycleRules })
        });
        
        showNotification('Lifecycle policy saved successfully', 'success');
    } catch (error) {
        showNotification(`Error saving lifecycle config: ${error.message}`, 'error');
    }
}

function editLifecycleRule(index) {
    openLifecycleRuleModal(index);
}

function deleteLifecycleRule(index) {
    if (confirm('Are you sure you want to delete this rule?')) {
        lifecycleRules.splice(index, 1);
        renderLifecycleRules();
    }
}

// Policies
const policyTemplates = {
    'public-read': {
        Version: "2012-10-17",
        Statement: [{
            Sid: "PublicReadGetObject",
            Effect: "Allow",
            Principal: "*",
            Action: "s3:GetObject",
            Resource: "arn:aws:s3:::BUCKET_NAME/*"
        }]
    },
    'public-read-write': {
        Version: "2012-10-17",
        Statement: [{
            Sid: "PublicReadWriteGetObject",
            Effect: "Allow",
            Principal: "*",
            Action: ["s3:GetObject", "s3:PutObject"],
            Resource: "arn:aws:s3:::BUCKET_NAME/*"
        }]
    },
    'private': {
        Version: "2012-10-17",
        Statement: []
    },
    'authenticated-read': {
        Version: "2012-10-17",
        Statement: [{
            Sid: "AuthenticatedRead",
            Effect: "Allow",
            Principal: { AWS: "*" },
            Action: "s3:GetObject",
            Resource: "arn:aws:s3:::BUCKET_NAME/*",
            Condition: {
                StringEquals: {
                    "s3:authType": "REST-QUERY-STRING"
                }
            }
        }]
    }
};

async function loadPolicyConfig(bucketName) {
    try {
        const data = await apiCall(`/api/s3-management/buckets/${encodeURIComponent(bucketName)}`);
        const bucket = data.bucket;
        
        const policy = bucket.policy || { Version: "2012-10-17", Statement: [] };
        const bucketPolicyEl = document.getElementById('bucketPolicy');
        const policyConfigEl = document.getElementById('policyConfig');
        const policyVisualEditorEl = document.getElementById('policyVisualEditor');
        const policyViewModeEl = document.getElementById('policyViewMode');

        bucketPolicyEl.value = JSON.stringify(policy, null, 2);
        policyConfigEl.classList.add('active');
        
        // Show JSON editor by default if policy exists
        const hasPolicy = bucket.policy && Object.keys(bucket.policy).length > 0;
        policyViewModeEl.checked = hasPolicy;
        if (hasPolicy) {
            bucketPolicyEl.classList.remove('d-none');
            policyVisualEditorEl.classList.add('d-none');
        } else {
            bucketPolicyEl.classList.add('d-none');
            policyVisualEditorEl.classList.remove('d-none');
        }
    } catch (error) {
        showNotification(`Error loading policy config: ${error.message}`, 'error');
    }
}

function applyPolicyTemplate(templateName, bucketName) {
    if (!policyTemplates[templateName]) {
        showNotification('Invalid template', 'error');
        return;
    }
    
    const template = JSON.parse(JSON.stringify(policyTemplates[templateName]));
    
    // Replace BUCKET_NAME placeholder
    const templateStr = JSON.stringify(template, null, 2);
    const policyStr = templateStr.replace(/BUCKET_NAME/g, bucketName);
    const policy = JSON.parse(policyStr);
    
    const bucketPolicyEl = document.getElementById('bucketPolicy');
    const policyVisualEditorEl = document.getElementById('policyVisualEditor');
    document.getElementById('bucketPolicy').value = JSON.stringify(policy, null, 2);
    document.getElementById('policyViewMode').checked = true;
    bucketPolicyEl.classList.remove('d-none');
    policyVisualEditorEl.classList.add('d-none');
    
    bootstrap.Modal.getInstance(document.getElementById('policyTemplateModal')).hide();
}

async function savePolicyConfig(bucketName) {
    try {
        const policyText = document.getElementById('bucketPolicy').value;
        if (!policyText.trim()) {
            showNotification('Policy cannot be empty', 'warning');
            return;
        }
        
        const policy = JSON.parse(policyText);
        
        await apiCall(`/api/s3-management/buckets/${encodeURIComponent(bucketName)}/policy`, {
            method: 'PUT',
            body: JSON.stringify({ policy })
        });
        
        showNotification('Policy saved successfully', 'success');
    } catch (error) {
        showNotification(`Error saving policy config: ${error.message}`, 'error');
    }
}

// CORS
const corsRulesList = [];

async function loadCorsConfig(bucketName) {
    try {
        const data = await apiCall(`/api/s3-management/buckets/${encodeURIComponent(bucketName)}`);
        const bucket = data.bucket;
        
        corsRulesList.length = 0;
        corsRulesList.push(...(bucket.cors || []));
        renderCorsRules();
        document.getElementById('corsConfig').classList.add('active');
    } catch (error) {
        showNotification(`Error loading CORS config: ${error.message}`, 'error');
    }
}

function renderCorsRules() {
    const container = document.getElementById('corsRulesList');
    if (!container) return;
    
    if (corsRulesList.length === 0) {
        container.innerHTML = '<p class="text-muted">No CORS rules configured. Click "Add CORS Rule" to create one.</p>';
        return;
    }
    
    container.innerHTML = corsRulesList.map((rule, index) => `
        <div class="card mb-3 cors-rule-card" data-index="${index}">
            <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                    <strong>CORS Rule #${index + 1}</strong>
                </div>
                <div>
                    <button class="btn btn-sm btn-primary me-1" onclick="editCorsRule(${index})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteCorsRule(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="card-body">
                <p><strong>Origins:</strong> ${(rule.AllowedOrigins || []).join(', ')}</p>
                <p><strong>Methods:</strong> ${(rule.AllowedMethods || []).join(', ')}</p>
                ${rule.AllowedHeaders ? `<p><strong>Headers:</strong> ${(rule.AllowedHeaders || []).join(', ')}</p>` : ''}
                ${rule.ExposedHeaders ? `<p><strong>Exposed Headers:</strong> ${(rule.ExposedHeaders || []).join(', ')}</p>` : ''}
                ${rule.MaxAgeSeconds ? `<p><strong>Max Age:</strong> ${rule.MaxAgeSeconds} seconds</p>` : ''}
            </div>
        </div>
    `).join('');
}

function openCorsRuleModal(ruleIndex = null) {
    const modal = new bootstrap.Modal(document.getElementById('corsRuleModal'));
    const rule = ruleIndex !== null ? corsRulesList[ruleIndex] : null;
    
    if (rule) {
        document.getElementById('corsAllowedOrigins').value = (rule.AllowedOrigins || []).join(', ');
        document.getElementById('corsAllowedHeaders').value = (rule.AllowedHeaders || []).join(', ');
        document.getElementById('corsExposedHeaders').value = (rule.ExposedHeaders || []).join(', ');
        document.getElementById('corsMaxAge').value = rule.MaxAgeSeconds || 3000;
        
        // Set methods
        document.querySelectorAll('.cors-method').forEach(cb => {
            cb.checked = (rule.AllowedMethods || []).includes(cb.value);
        });
    } else {
        // Clear form
        document.getElementById('corsAllowedOrigins').value = '';
        document.getElementById('corsAllowedHeaders').value = '*';
        document.getElementById('corsExposedHeaders').value = '';
        document.getElementById('corsMaxAge').value = 3000;
        document.querySelectorAll('.cors-method').forEach(cb => cb.checked = false);
    }
    
    currentEditingCorsIndex = ruleIndex;
    modal.show();
}

let currentEditingCorsIndex = null;

function saveCorsRuleFromModal() {
    const origins = document.getElementById('corsAllowedOrigins').value.split(',').map(s => s.trim()).filter(s => s);
    if (origins.length === 0) {
        showNotification('At least one origin is required', 'warning');
        return;
    }
    
    const methods = Array.from(document.querySelectorAll('.cors-method:checked')).map(cb => cb.value);
    if (methods.length === 0) {
        showNotification('At least one method is required', 'warning');
        return;
    }
    
    const rule = {
        AllowedOrigins: origins,
        AllowedMethods: methods
    };
    
    const headers = document.getElementById('corsAllowedHeaders').value.trim();
    if (headers) {
        rule.AllowedHeaders = headers.split(',').map(s => s.trim()).filter(s => s);
    }
    
    const exposedHeaders = document.getElementById('corsExposedHeaders').value.trim();
    if (exposedHeaders) {
        rule.ExposedHeaders = exposedHeaders.split(',').map(s => s.trim()).filter(s => s);
    }
    
    const maxAge = document.getElementById('corsMaxAge').value;
    if (maxAge) {
        rule.MaxAgeSeconds = parseInt(maxAge);
    }
    
    if (currentEditingCorsIndex !== null) {
        corsRulesList[currentEditingCorsIndex] = rule;
    } else {
        corsRulesList.push(rule);
    }
    
    renderCorsRules();
    bootstrap.Modal.getInstance(document.getElementById('corsRuleModal')).hide();
    currentEditingCorsIndex = null;
}

async function saveCorsConfig(bucketName) {
    try {
        await apiCall(`/api/s3-management/buckets/${encodeURIComponent(bucketName)}/cors`, {
            method: 'PUT',
            body: JSON.stringify({ cors_rules: corsRulesList })
        });
        
        showNotification('CORS rules saved successfully', 'success');
    } catch (error) {
        showNotification(`Error saving CORS config: ${error.message}`, 'error');
    }
}

function editCorsRule(index) {
    openCorsRuleModal(index);
}

function deleteCorsRule(index) {
    if (confirm('Are you sure you want to delete this CORS rule?')) {
        corsRulesList.splice(index, 1);
        renderCorsRules();
    }
}

// Tags
async function loadTagsConfig(bucketName) {
    try {
        const data = await apiCall(`/api/s3-management/buckets/${encodeURIComponent(bucketName)}`);
        const bucket = data.bucket;
        
        const tags = bucket.tags || {};
        renderTags(tags);
        document.getElementById('tagsConfig').classList.add('active');
    } catch (error) {
        showNotification(`Error loading tags config: ${error.message}`, 'error');
    }
}

function renderTags(tags) {
    const container = document.getElementById('bucketTagsList');
    if (!container) return;
    
    container.innerHTML = Object.entries(tags).map(([key, value]) => `
        <div class="badge bg-primary me-2 mb-2 p-2">
            ${key}: ${value}
            <button type="button" class="btn-close btn-close-white ms-2" onclick="removeTag('${key}')"></button>
        </div>
    `).join('');
}

const currentTags = {};

function addTag() {
    const key = document.getElementById('tagKey').value.trim();
    const value = document.getElementById('tagValue').value.trim();
    
    if (!key || !value) {
        showNotification('Both tag key and value are required', 'warning');
        return;
    }
    
    currentTags[key] = value;
    renderTags(currentTags);
    document.getElementById('tagKey').value = '';
    document.getElementById('tagValue').value = '';
}

function removeTag(key) {
    delete currentTags[key];
    renderTags(currentTags);
}

async function saveTagsConfig(bucketName) {
    try {
        await apiCall(`/api/s3-management/buckets/${encodeURIComponent(bucketName)}/tags`, {
            method: 'PUT',
            body: JSON.stringify({ tags: currentTags })
        });
        
        showNotification('Tags saved successfully', 'success');
        await loadTagsConfig(bucketName);
    } catch (error) {
        showNotification(`Error saving tags config: ${error.message}`, 'error');
    }
}

// Analytics
async function loadAnalytics(bucketName) {
    try {
        const data = await apiCall(`/api/s3-management/buckets/${encodeURIComponent(bucketName)}/statistics`);
        const stats = data.statistics;
        
        document.getElementById('analyticsTotalSize').textContent = formatBytes(stats.total_size || 0);
        document.getElementById('analyticsObjectCount').textContent = (stats.object_count || 0).toLocaleString();
        
        const storageClasses = stats.storage_classes || {};
        const chartContainer = document.getElementById('storageClassesChart');
        
        if (Object.keys(storageClasses).length > 0) {
            chartContainer.innerHTML = Object.entries(storageClasses).map(([cls, count]) => `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span><strong>${cls}</strong></span>
                    <span class="badge bg-info">${count.toLocaleString()} objects</span>
                </div>
            `).join('');
        } else {
            chartContainer.innerHTML = '<p class="text-muted">No storage class information available</p>';
        }
        
        document.getElementById('analyticsContent').classList.add('active');
    } catch (error) {
        showNotification(`Error loading analytics: ${error.message}`, 'error');
    }
}

// Инициализация
document.addEventListener('DOMContentLoaded', async () => {
    console.log('S3 Management: DOM Content Loaded');
    
    // Убеждаемся, что контент виден
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.classList.remove('d-none');
    }
    
    try {
        // Загружаем бакеты при загрузке страницы
        console.log('S3 Management: Starting initialization...');
        await loadBuckets();
        console.log('S3 Management: Initialization complete');
    } catch (error) {
        console.error('Error initializing S3 Management:', error);
        console.error('Error details:', {
            message: error.message,
            stack: error.stack,
            name: error.name
        });
        
        // Показываем ошибку пользователю, но не блокируем страницу
        const bucketsList = document.getElementById('bucketsList');
        if (bucketsList) {
            bucketsList.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>Error loading buckets: ${error.message}
                        <br><small>Please check browser console (F12) for more details</small>
                    </div>
                </div>
            `;
        }
        
        // Показываем уведомление если функция доступна
        if (typeof showNotification === 'function') {
            try {
                showNotification(`Error loading page: ${error.message}`, 'error');
            } catch (e) {
                console.error('Failed to show notification:', e);
            }
        }
    }
    
    // Создание бакета
    document.getElementById('createBucketBtn')?.addEventListener('click', () => {
        const modal = new bootstrap.Modal(document.getElementById('createBucketModal'));
        modal.show();
    });
    
    document.getElementById('confirmCreateBucketBtn')?.addEventListener('click', () => {
        const name = document.getElementById('newBucketName').value.trim();
        const location = document.getElementById('bucketLocation').value.trim() || 'us-east-1';
        
        if (!name) {
            showNotification('Bucket name is required', 'warning');
            return;
        }
        
        createBucket(name, location);
    });
    
    // Versioning
    document.getElementById('versioningBucketSelect')?.addEventListener('change', (e) => {
        const configEl = document.getElementById('versioningConfig');
        if (e.target.value) {
            loadVersioningConfig(e.target.value);
        } else if (configEl) {
            configEl.classList.remove('active');
        }
    });
    
    document.getElementById('saveVersioningBtn')?.addEventListener('click', () => {
        const bucketName = document.getElementById('versioningBucketSelect').value;
        if (bucketName) {
            saveVersioningConfig(bucketName);
        }
    });
    
    // Lifecycle
    document.getElementById('lifecycleBucketSelect')?.addEventListener('change', (e) => {
        const configEl = document.getElementById('lifecycleConfig');
        if (e.target.value) {
            loadLifecycleConfig(e.target.value);
        } else if (configEl) {
            configEl.classList.remove('active');
        }
    });
    
    document.getElementById('addLifecycleRuleBtn')?.addEventListener('click', () => {
        openLifecycleRuleModal(null);
    });
    
    document.getElementById('saveLifecycleRuleBtn')?.addEventListener('click', () => {
        saveLifecycleRuleFromModal();
    });
    
    document.getElementById('addTransitionBtn')?.addEventListener('click', () => {
        const modal = new bootstrap.Modal(document.getElementById('transitionModal'));
        modal.show();
    });
    
    document.getElementById('saveTransitionBtn')?.addEventListener('click', () => {
        const days = parseInt(document.getElementById('transitionDays').value);
        const storageClass = document.getElementById('transitionStorageClass').value;
        
        if (!days || !storageClass) {
            showNotification('Days and Storage Class are required', 'warning');
            return;
        }
        
        currentTransitions.push({
            Days: days,
            StorageClass: storageClass
        });
        
        renderTransitions(currentTransitions);
        bootstrap.Modal.getInstance(document.getElementById('transitionModal')).hide();
        document.getElementById('transitionDays').value = '';
        document.getElementById('transitionStorageClass').value = 'STANDARD_IA';
    });
    
    document.getElementById('saveLifecycleBtn')?.addEventListener('click', () => {
        const bucketName = document.getElementById('lifecycleBucketSelect').value;
        if (bucketName) {
            saveLifecycleConfig(bucketName);
        }
    });
    
    // Policies
    document.getElementById('policyBucketSelect')?.addEventListener('change', (e) => {
        const configEl = document.getElementById('policyConfig');
        if (e.target.value) {
            loadPolicyConfig(e.target.value);
        } else if (configEl) {
            configEl.classList.remove('active');
        }
    });
    
    document.getElementById('policyViewMode')?.addEventListener('change', (e) => {
        const showJson = e.target.checked;
        const bucketPolicyEl = document.getElementById('bucketPolicy');
        const policyVisualEditorEl = document.getElementById('policyVisualEditor');
        if (!bucketPolicyEl || !policyVisualEditorEl) return;
        if (showJson) {
            bucketPolicyEl.classList.remove('d-none');
            policyVisualEditorEl.classList.add('d-none');
        } else {
            bucketPolicyEl.classList.add('d-none');
            policyVisualEditorEl.classList.remove('d-none');
        }
    });
    
    document.getElementById('usePolicyTemplateBtnHeader')?.addEventListener('click', () => {
        const bucketName = document.getElementById('policyBucketSelect').value;
        if (!bucketName) {
            showNotification('Please select a bucket first', 'warning');
            return;
        }
        
        const modal = new bootstrap.Modal(document.getElementById('policyTemplateModal'));
        
        // Update preview when template changes
        document.getElementById('policyTemplateSelect').addEventListener('change', (e) => {
            const templateName = e.target.value;
            if (templateName && policyTemplates[templateName]) {
                const template = JSON.parse(JSON.stringify(policyTemplates[templateName]));
                const templateStr = JSON.stringify(template, null, 2);
                const previewStr = templateStr.replace(/BUCKET_NAME/g, bucketName);
                document.getElementById('policyTemplateContent').textContent = previewStr;
            } else {
                document.getElementById('policyTemplateContent').textContent = '';
            }
        });
        
        modal.show();
    });
    
    document.getElementById('usePolicyTemplateBtn')?.addEventListener('click', () => {
        const bucketName = document.getElementById('policyBucketSelect').value;
        const templateName = document.getElementById('policyTemplateSelect').value;
        if (bucketName && templateName) {
            applyPolicyTemplate(templateName, bucketName);
        }
    });
    
    document.getElementById('savePolicyBtn')?.addEventListener('click', () => {
        const bucketName = document.getElementById('policyBucketSelect').value;
        if (bucketName) {
            savePolicyConfig(bucketName);
        }
    });
    
    // CORS
    document.getElementById('corsBucketSelect')?.addEventListener('change', (e) => {
        const configEl = document.getElementById('corsConfig');
        if (e.target.value) {
            loadCorsConfig(e.target.value);
        } else if (configEl) {
            configEl.classList.remove('active');
        }
    });
    
    document.getElementById('addCorsRuleBtn')?.addEventListener('click', () => {
        openCorsRuleModal(null);
    });
    
    document.getElementById('saveCorsRuleBtn')?.addEventListener('click', () => {
        saveCorsRuleFromModal();
    });
    
    document.getElementById('saveCorsBtn')?.addEventListener('click', () => {
        const bucketName = document.getElementById('corsBucketSelect').value;
        if (bucketName) {
            saveCorsConfig(bucketName);
        }
    });
    
    // Tags
    document.getElementById('tagsBucketSelect')?.addEventListener('change', async (e) => {
        const configEl = document.getElementById('tagsConfig');
        if (e.target.value) {
            Object.keys(currentTags).forEach(key => delete currentTags[key]);
            await loadTagsConfig(e.target.value);
            Object.assign(currentTags, state.bucketInfo?.tags || {});
        } else if (configEl) {
            configEl.classList.remove('active');
        }
    });
    
    document.getElementById('addTagBtn')?.addEventListener('click', addTag);
    
    document.getElementById('saveTagsBtn')?.addEventListener('click', () => {
        const bucketName = document.getElementById('tagsBucketSelect').value;
        if (bucketName) {
            saveTagsConfig(bucketName);
        }
    });
    
    // Analytics
    document.getElementById('analyticsBucketSelect')?.addEventListener('change', (e) => {
        const configEl = document.getElementById('analyticsContent');
        if (e.target.value) {
            loadAnalytics(e.target.value);
        } else if (configEl) {
            configEl.classList.remove('active');
        }
    });
    
    // Обновляем список бакетов и пользователей при смене таба
    const tabButtons = document.querySelectorAll('#managementTabs button[data-bs-toggle="tab"]');
    tabButtons.forEach(button => {
        button.addEventListener('shown.bs.tab', async (e) => {
            if (e.target.id === 'buckets-tab') {
                await loadBuckets();
            }
        });
    });
});

// NOTE: IAM / Users & Access Keys functionality is disabled in this deployment.

// Users & Access Keys Management
async function loadUsers() {
    try {
        const data = await apiCall('/api/s3-management/users');
        const users = data.users || [];
        renderUsers(users);
    } catch (error) {
        const container = document.getElementById('usersList');
        if (container) {
            container.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${error.message || 'IAM API may not be supported by your S3 storage. Some S3-compatible storage systems do not support IAM user management.'}
                </div>
            `;
        }
    }
}

function renderUsers(users) {
    const container = document.getElementById('usersList');
    if (!container) return;
    
    if (users.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>No IAM users found. Click "Create User" to create your first user.
            </div>
        `;
        return;
    }
    
    container.innerHTML = users.map(user => `
        <div class="card mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="card-title mb-1">
                            <i class="fas fa-user me-2"></i>${user.UserName}
                        </h5>
                        <p class="text-muted small mb-1">
                            <i class="fas fa-calendar me-1"></i>
                            Created: ${user.CreateDate ? new Date(user.CreateDate).toLocaleDateString() : 'Unknown'}
                        </p>
                        <p class="text-muted small mb-0">
                            <i class="fas fa-key me-1"></i>
                            Access Keys: <span class="badge bg-info">${user.AccessKeysCount || 0}</span>
                        </p>
                    </div>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-primary" onclick="viewUserAccessKeys('${user.UserName}')">
                            <i class="fas fa-key me-1"></i>Keys
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteUserConfirm('${user.UserName}')">
                            <i class="fas fa-trash me-1"></i>Delete
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

async function createUser(userName, createAccessKey = false) {
    try {
        const data = await apiCall('/api/s3-management/users', {
            method: 'POST',
            body: JSON.stringify({
                user_name: userName,
                create_access_key: createAccessKey
            })
        });
        
        showNotification(data.message || 'User created successfully', 'success');
        
        // Если создан ключ доступа, показываем его
        if (data.user && data.user.AccessKey) {
            showAccessKeyCreated(data.user.AccessKey);
        }
        
        await loadUsers();
        bootstrap.Modal.getInstance(document.getElementById('createUserModal')).hide();
        document.getElementById('newUserName').value = '';
    } catch (error) {
        showNotification(`Error creating user: ${error.message}`, 'error');
    }
}

async function deleteUser(userName) {
    try {
        const data = await apiCall(`/api/s3-management/users/${encodeURIComponent(userName)}`, {
            method: 'DELETE'
        });
        showNotification(data.message || 'User deleted successfully', 'success');
        await loadUsers();
    } catch (error) {
        showNotification(`Error deleting user: ${error.message}`, 'error');
    }
}

async function deleteUserConfirm(userName) {
    if (typeof showConfirmInputModal === 'undefined') {
        if (!confirm(`Are you sure you want to delete user "${userName}"? This action cannot be undone.`)) {
            return;
        }
        await deleteUser(userName);
        return;
    }
    
    const confirmed = await showConfirmInputModal(
        'DELETE USER',
        `Вы уверены, что хотите удалить пользователя "${userName}"?<br><br><strong class="text-danger">Это действие нельзя отменить!</strong>`,
        'DELETE',
        'Введите DELETE для подтверждения',
        'Удалить',
        'Отмена'
    );
    
    if (confirmed) {
        await deleteUser(userName);
    }
}

async function viewUserAccessKeys(userName) {
    try {
        const data = await apiCall(`/api/s3-management/users/${encodeURIComponent(userName)}/access-keys`);
        const keys = data.access_keys || [];
        
        document.getElementById('accessKeysUserName').textContent = userName;
        renderAccessKeys(userName, keys);
        
        const modal = new bootstrap.Modal(document.getElementById('accessKeysModal'));
        modal.show();
        
        // Сохраняем имя пользователя для создания новых ключей
        document.getElementById('accessKeysModal').dataset.userName = userName;
    } catch (error) {
        showNotification(`Error loading access keys: ${error.message}`, 'error');
    }
}

function renderAccessKeys(userName, keys) {
    const container = document.getElementById('accessKeysList');
    if (!container) return;
    
    if (keys.length === 0) {
        container.innerHTML = '<p class="text-muted">No access keys found. Click "Create New Key" to create one.</p>';
        return;
    }
    
    container.innerHTML = keys.map(key => `
        <div class="card mb-2">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <code class="text-primary">${key.AccessKeyId}</code>
                        <span class="badge ${key.Status === 'Active' ? 'bg-success' : 'bg-secondary'} ms-2">${key.Status}</span>
                        <p class="text-muted small mb-0 mt-1">
                            Created: ${key.CreateDate ? new Date(key.CreateDate).toLocaleDateString() : 'Unknown'}
                        </p>
                    </div>
                    <button class="btn btn-sm btn-danger" onclick="deleteAccessKeyConfirm('${userName}', '${key.AccessKeyId}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

async function createAccessKeyForUser(userName) {
    try {
        const data = await apiCall(`/api/s3-management/users/${encodeURIComponent(userName)}/access-keys`, {
            method: 'POST'
        });
        
        if (data.access_key) {
            showAccessKeyCreated(data.access_key);
            await viewUserAccessKeys(userName);
        }
    } catch (error) {
        showNotification(`Error creating access key: ${error.message}`, 'error');
    }
}

function showAccessKeyCreated(accessKey) {
    const modalHTML = `
        <div class="modal fade" id="accessKeyCreatedModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-success text-white">
                        <h5 class="modal-title"><i class="fas fa-check-circle me-2"></i>Access Key Created</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            <strong>Important:</strong> Save these credentials now. The secret access key cannot be retrieved later.
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Access Key ID:</label>
                            <div class="input-group">
                                <input type="text" class="form-control" id="displayAccessKeyId" value="${accessKey.AccessKeyId}" readonly>
                                <button class="btn btn-outline-secondary" type="button" onclick="copyToClipboard('displayAccessKeyId')">
                                    <i class="fas fa-copy"></i>
                                </button>
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Secret Access Key:</label>
                            <div class="input-group">
                                <input type="text" class="form-control" id="displaySecretKey" value="${accessKey.SecretAccessKey}" readonly>
                                <button class="btn btn-outline-secondary" type="button" onclick="copyToClipboard('displaySecretKey')">
                                    <i class="fas fa-copy"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" data-bs-dismiss="modal">I've Saved These</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Удаляем старое модальное окно если есть
    const oldModal = document.getElementById('accessKeyCreatedModal');
    if (oldModal) {
        oldModal.remove();
    }
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = new bootstrap.Modal(document.getElementById('accessKeyCreatedModal'));
    modal.show();
}

async function deleteAccessKey(userName, accessKeyId) {
    try {
        const data = await apiCall(`/api/s3-management/users/${encodeURIComponent(userName)}/access-keys/${encodeURIComponent(accessKeyId)}`, {
            method: 'DELETE'
        });
        showNotification(data.message || 'Access key deleted successfully', 'success');
        await viewUserAccessKeys(userName);
    } catch (error) {
        showNotification(`Error deleting access key: ${error.message}`, 'error');
    }
}

async function deleteAccessKeyConfirm(userName, accessKeyId) {
    if (typeof showConfirmModal === 'undefined') {
        if (!confirm(`Are you sure you want to delete this access key?`)) {
            return;
        }
        await deleteAccessKey(userName, accessKeyId);
        return;
    }
    
    const confirmed = await showConfirmModal(
        'DELETE ACCESS KEY',
        `Вы уверены, что хотите удалить этот ключ доступа?<br><br><code>${accessKeyId}</code><br><br><strong class="text-danger">Это действие нельзя отменить!</strong>`,
        'Удалить',
        'Отмена',
        'danger'
    );
    
    if (confirmed) {
        await deleteAccessKey(userName, accessKeyId);
    }
}

function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    element.select();
    document.execCommand('copy');
    showNotification('Copied to clipboard!', 'success');
}

// Экспортируем функции в глобальную область для использования в HTML
window.viewBucketInfo = viewBucketInfo;
window.deleteBucketConfirm = deleteBucketConfirm;
window.addTag = addTag;
window.removeTag = removeTag;
window.editLifecycleRule = editLifecycleRule;
window.deleteLifecycleRule = deleteLifecycleRule;
window.removeTransition = removeTransition;
window.editCorsRule = editCorsRule;
window.deleteCorsRule = deleteCorsRule;
window.viewUserAccessKeys = viewUserAccessKeys;
window.deleteUserConfirm = deleteUserConfirm;
window.deleteAccessKeyConfirm = deleteAccessKeyConfirm;
window.copyToClipboard = copyToClipboard;
window.filterBucketTiles = filterBucketTiles;
window.selectBucketForTab = selectBucketForTab;

