// Shared functionality for config selector on multiple pages
let configListGlobal = [];
let currentConfigIdGlobal = null;

async function loadConfigListForSelector(selectorId, defaultConfigId = null) {
    try {
        const result = await fetch('/api/config/list');
        const data = await result.json();
        
        if (data.status !== 'success') {
            throw new Error(data.message || 'Failed to load config list');
        }
        
        configListGlobal = data.configs || [];
        renderConfigSelector(selectorId, defaultConfigId);
        return configListGlobal;
    } catch (error) {
        console.error('Failed to load config list:', error);
        return [];
    }
}

function renderConfigSelector(selectorId, defaultConfigId = null) {
    const selector = document.getElementById(selectorId);
    if (!selector) return;
    
    selector.innerHTML = '';
    
    if (configListGlobal.length === 0) {
        selector.innerHTML = '<option value="">No configurations found</option>';
        return;
    }
    
    // Find default config
    let defaultId = defaultConfigId;
    if (!defaultId) {
        const defaultConfig = configListGlobal.find(c => c.is_default);
        if (defaultConfig) {
            defaultId = defaultConfig.id;
            currentConfigIdGlobal = defaultConfig.id;
        } else if (configListGlobal.length > 0) {
            defaultId = configListGlobal[0].id;
            currentConfigIdGlobal = configListGlobal[0].id;
        }
    } else {
        currentConfigIdGlobal = defaultId;
    }
    
    configListGlobal.forEach(config => {
        const option = document.createElement('option');
        option.value = config.id;
        option.textContent = config.name + (config.is_default ? ' (Default)' : '');
        if (config.id === defaultId) {
            option.selected = true;
        }
        selector.appendChild(option);
    });
}

function getSelectedConfigId(selectorId) {
    const selector = document.getElementById(selectorId);
    if (!selector) return null;
    return selector.value ? parseInt(selector.value) : null;
}

// Initialize config selector on page load
function initConfigSelector(selectorId) {
    loadConfigListForSelector(selectorId);
    
    const selector = document.getElementById(selectorId);
    if (selector) {
        selector.addEventListener('change', (e) => {
            currentConfigIdGlobal = e.target.value ? parseInt(e.target.value) : null;
        });
    }
}



