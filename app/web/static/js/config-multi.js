// Additional functions for multiple config support

let configList = [];
let currentConfigId = null;

async function loadConfigList() {
    try {
        const result = await apiCall('/api/config/list');
        configList = result.configs || [];
        renderConfigSelector();
        return configList;
    } catch (error) {
        console.error('Failed to load config list:', error);
        showNotification('Failed to load configuration list: ' + error.message, 'error');
        return [];
    }
}

function renderConfigSelector() {
    const selector = document.getElementById('configSelector');
    if (!selector) return;
    
    selector.innerHTML = '';
    
    if (configList.length === 0) {
        selector.innerHTML = '<option value="">No configurations found</option>';
        return;
    }
    
    configList.forEach(config => {
        const option = document.createElement('option');
        option.value = config.id;
        option.textContent = config.name + (config.is_default ? ' (Default)' : '');
        if (config.is_default) {
            option.selected = true;
            currentConfigId = config.id;
        }
        selector.appendChild(option);
    });
    
    updateConfigButtonsState();
}

function updateConfigButtonsState() {
    const hasSelection = currentConfigId !== null;
    const renameBtn = document.getElementById('renameConfigBtn');
    const deleteBtn = document.getElementById('deleteConfigBtn');
    const setDefaultBtn = document.getElementById('setDefaultConfigBtn');
    
    if (renameBtn) renameBtn.disabled = !hasSelection;
    if (deleteBtn) deleteBtn.disabled = !hasSelection || configList.length <= 1;
    if (setDefaultBtn) setDefaultBtn.disabled = !hasSelection;
    
    // Update info
    const infoDiv = document.getElementById('configInfo');
    if (infoDiv) {
        const selectedConfig = configList.find(c => c.id === currentConfigId);
        if (selectedConfig) {
            infoDiv.innerHTML = `<small class="text-muted">
                ${selectedConfig.is_default ? '<i class="fas fa-star text-warning"></i> ' : ''}
                Configuration: ${selectedConfig.name} | 
                Created: ${new Date(selectedConfig.created_at).toLocaleDateString()}
            </small>`;
        } else {
            infoDiv.innerHTML = '<small class="text-muted">Select a configuration profile to view or edit</small>';
        }
    }
}

async function switchConfig(configId) {
    if (!configId) {
        currentConfigId = null;
        return;
    }
    
    currentConfigId = parseInt(configId);
    
    // Update loadConfiguration to use config_id
    if (typeof loadConfiguration === 'function') {
        // Reload with config_id
        await loadConfiguration();
    }
    
    updateConfigButtonsState();
}

async function createConfig() {
    const name = await showPromptModal(
        'Создание конфигурации',
        'Введите имя новой конфигурации:',
        'Имя конфигурации',
        '',
        'text',
        'Создать',
        'Отмена'
    );
    if (!name || !name.trim()) return;
    
    try {
        // Collect current config as template
        const configData = collectConfigFromForm();
        
        const result = await apiCall('/api/config/create', {
            method: 'POST',
            body: {
                name: name.trim(),
                config: configData,
                is_default: false
            }
        });
        
        showNotification(result.message || 'Configuration created', 'success');
        await loadConfigList();
        
        // Switch to newly created config
        if (result.config_id) {
            document.getElementById('configSelector').value = result.config_id;
            await switchConfig(result.config_id);
        }
    } catch (error) {
        showNotification('Failed to create configuration: ' + error.message, 'error');
    }
}

async function renameConfig() {
    if (!currentConfigId) return;
    
    const selectedConfig = configList.find(c => c.id === currentConfigId);
    if (!selectedConfig) return;
    
    const newName = await showPromptModal(
        'Переименование конфигурации',
        `Введите новое имя для конфигурации "${selectedConfig.name}":`,
        'Новое имя',
        selectedConfig.name,
        'text',
        'Переименовать',
        'Отмена'
    );
    if (!newName || !newName.trim() || newName === selectedConfig.name) return;
    
    try {
        await apiCall(`/api/config/${currentConfigId}`, {
            method: 'PATCH',
            body: {
                name: newName.trim()
            }
        });
        
        showNotification('Configuration renamed successfully', 'success');
        await loadConfigList();
        document.getElementById('configSelector').value = currentConfigId;
    } catch (error) {
        showNotification('Failed to rename configuration: ' + error.message, 'error');
    }
}

async function deleteConfig() {
    if (!currentConfigId) return;
    
    const selectedConfig = configList.find(c => c.id === currentConfigId);
    if (!selectedConfig) return;
    
    const confirmed = await showConfirmModal(
        'Удаление конфигурации',
        `Вы уверены, что хотите удалить конфигурацию <strong>"${selectedConfig.name}"</strong>?<br><small class="text-muted">Это действие нельзя отменить.</small>`,
        'Удалить',
        'Отмена',
        'danger'
    );
    if (!confirmed) {
        return;
    }
    
    try {
        await apiCall(`/api/config/${currentConfigId}`, {
            method: 'DELETE'
        });
        
        showNotification('Configuration deleted successfully', 'success');
        
        // Switch to default config
        const defaultConfig = configList.find(c => c.id !== currentConfigId && c.is_default);
        await loadConfigList();
        
        if (defaultConfig) {
            document.getElementById('configSelector').value = defaultConfig.id;
            await switchConfig(defaultConfig.id);
        } else if (configList.length > 0) {
            document.getElementById('configSelector').value = configList[0].id;
            await switchConfig(configList[0].id);
        }
    } catch (error) {
        showNotification('Failed to delete configuration: ' + error.message, 'error');
    }
}

async function setDefaultConfig() {
    if (!currentConfigId) return;
    
    try {
        await apiCall('/api/config/set-default', {
            method: 'POST',
            body: {
                config_id: currentConfigId
            }
        });
        
        showNotification('Default configuration updated', 'success');
        await loadConfigList();
        document.getElementById('configSelector').value = currentConfigId;
    } catch (error) {
        showNotification('Failed to set default configuration: ' + error.message, 'error');
    }
}

// Make currentConfigId globally accessible
window.getCurrentConfigId = function() {
    return currentConfigId;
};

window.setCurrentConfigId = function(configId) {
    currentConfigId = configId;
};

// Setup event listeners when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupConfigMultiListeners);
} else {
    setupConfigMultiListeners();
}

function setupConfigMultiListeners() {
    // Config selector listeners
    const configSelector = document.getElementById('configSelector');
    if (configSelector) {
        configSelector.addEventListener('change', async (e) => {
            await switchConfig(e.target.value);
        });
    }
    
    const createBtn = document.getElementById('createConfigBtn');
    if (createBtn) createBtn.addEventListener('click', createConfig);
    
    const renameBtn = document.getElementById('renameConfigBtn');
    if (renameBtn) renameBtn.addEventListener('click', renameConfig);
    
    const deleteBtn = document.getElementById('deleteConfigBtn');
    if (deleteBtn) deleteBtn.addEventListener('click', deleteConfig);
    
    const setDefaultBtn = document.getElementById('setDefaultConfigBtn');
    if (setDefaultBtn) setDefaultBtn.addEventListener('click', setDefaultConfig);
    
    // Load config list on page load
    loadConfigList();
}

