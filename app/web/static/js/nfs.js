/**
 * JavaScript для управления NFS монтированием
 */

// API функции
async function checkNfsStatus(mountPoint = null) {
    const params = mountPoint ? `?mount_point=${encodeURIComponent(mountPoint)}` : '';
    const response = await fetch(`/api/nfs/status${params}`);
    const data = await response.json();
    
    if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to check NFS status');
    }
    
    return data;
}

async function mountNfs(nfsServer, mountPoint, nfsOptions = null) {
    const response = await fetch('/api/nfs/mount', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            nfs_server: nfsServer,
            mount_point: mountPoint,
            nfs_options: nfsOptions
        })
    });
    
    const data = await response.json();
    
    if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to mount NFS');
    }
    
    return data;
}

async function unmountNfs(mountPoint) {
    const response = await fetch('/api/nfs/unmount', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            mount_point: mountPoint
        })
    });
    
    const data = await response.json();
    
    if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to unmount NFS');
    }
    
    return data;
}

async function createDirectory(mountPoint, permissions = '755') {
    const response = await fetch('/api/nfs/create-directory', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            mount_point: mountPoint,
            permissions: permissions
        })
    });
    
    const data = await response.json();
    
    if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to create directory');
    }
    
    return data;
}

async function testNfsServer(nfsServer) {
    const response = await fetch('/api/nfs/test', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            nfs_server: nfsServer
        })
    });
    
    const data = await response.json();
    
    if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to test NFS server');
    }
    
    return data;
}

// UI функции
function showNfsAlert(message, type = 'info') {
    const alertDiv = document.getElementById('nfsStatusAlert');
    if (!alertDiv) return;
    
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
}

function updateNfsStatusInfo(status) {
    const infoDiv = document.getElementById('nfsStatusInfo');
    if (!infoDiv) return;
    
    if (status.mounted) {
        infoDiv.innerHTML = `
            <div class="alert alert-success mb-0">
                <i class="fas fa-check-circle me-2"></i>
                <strong>NFS Mounted</strong><br>
                <small>Mount Point: ${status.mount_point}</small>
                ${status.mount_info ? `<br><small class="text-muted">${status.mount_info}</small>` : ''}
            </div>
        `;
    } else {
        infoDiv.innerHTML = `
            <div class="alert alert-warning mb-0">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>NFS Not Mounted</strong><br>
                <small>Mount Point: ${status.mount_point}</small>
            </div>
        `;
    }
}

function setButtonsDisabled(disabled) {
    const buttons = ['mountNfs', 'unmountNfs', 'checkNfsStatus', 'testNfsServer', 'createDirectory'];
    buttons.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.disabled = disabled;
    });
}

// Инициализация обработчиков событий
document.addEventListener('DOMContentLoaded', () => {
    const mountBtn = document.getElementById('mountNfs');
    const unmountBtn = document.getElementById('unmountNfs');
    const statusBtn = document.getElementById('checkNfsStatus');
    const testBtn = document.getElementById('testNfsServer');
    
    // Проверка статуса при загрузке
    if (statusBtn) {
        statusBtn.addEventListener('click', async () => {
            const mountPoint = document.getElementById('nfsMountPoint')?.value;
            
            try {
                setButtonsDisabled(true);
                statusBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Checking...';
                
                const status = await checkNfsStatus(mountPoint);
                updateNfsStatusInfo(status);
                
                showNfsAlert(
                    status.mounted 
                        ? '<i class="fas fa-check-circle me-1"></i>NFS is mounted and accessible'
                        : '<i class="fas fa-exclamation-triangle me-1"></i>NFS is not mounted',
                    status.mounted ? 'success' : 'warning'
                );
            } catch (error) {
                showNfsAlert(`<i class="fas fa-exclamation-circle me-1"></i>Error: ${error.message}`, 'danger');
            } finally {
                setButtonsDisabled(false);
                statusBtn.innerHTML = '<i class="fas fa-sync me-1"></i>Check Status';
            }
        });
        
        // Автоматическая проверка при загрузке страницы
        setTimeout(() => statusBtn.click(), 500);
    }
    
    // Создание директории
    const createDirBtn = document.getElementById('createDirectory');
    if (createDirBtn) {
        createDirBtn.addEventListener('click', async () => {
            const mountPoint = document.getElementById('nfsMountPoint')?.value.trim();
            
            if (!mountPoint) {
                showNfsAlert('<i class="fas fa-exclamation-circle me-1"></i>Mount Point is required', 'danger');
                return;
            }
            
            try {
                setButtonsDisabled(true);
                createDirBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Creating...';
                
                const result = await createDirectory(mountPoint);
                
                showNfsAlert(
                    `<i class="fas fa-check-circle me-1"></i>${result.message}`,
                    'success'
                );
                
            } catch (error) {
                showNfsAlert(`<i class="fas fa-exclamation-circle me-1"></i>Error: ${error.message}`, 'danger');
            } finally {
                setButtonsDisabled(false);
                createDirBtn.innerHTML = '<i class="fas fa-folder-plus me-1"></i>Create Directory';
            }
        });
    }
    
    // Монтирование NFS
    if (mountBtn) {
        mountBtn.addEventListener('click', async () => {
            const nfsServer = document.getElementById('nfsServer')?.value.trim();
            const mountPoint = document.getElementById('nfsMountPoint')?.value.trim();
            const nfsOptions = document.getElementById('nfsOptions')?.value.trim() || null;
            
            if (!nfsServer) {
                showNfsAlert('<i class="fas fa-exclamation-circle me-1"></i>NFS Server is required', 'danger');
                return;
            }
            
            if (!mountPoint) {
                showNfsAlert('<i class="fas fa-exclamation-circle me-1"></i>Mount Point is required', 'danger');
                return;
            }
            
            try {
                setButtonsDisabled(true);
                mountBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Mounting...';
                
                const result = await mountNfs(nfsServer, mountPoint, nfsOptions);
                
                showNfsAlert(
                    `<i class="fas fa-check-circle me-1"></i>${result.message}`,
                    'success'
                );
                
                // Обновляем NFS Path в форме конфигурации
                const nfsPathInput = document.getElementById('nfsPath');
                if (nfsPathInput && !nfsPathInput.value) {
                    nfsPathInput.value = mountPoint;
                }
                
                // Обновляем статус
                await checkNfsStatus(mountPoint).then(updateNfsStatusInfo).catch(() => {});
                
            } catch (error) {
                showNfsAlert(`<i class="fas fa-exclamation-circle me-1"></i>Error: ${error.message}`, 'danger');
            } finally {
                setButtonsDisabled(false);
                mountBtn.innerHTML = '<i class="fas fa-link me-1"></i>Mount NFS';
            }
        });
    }
    
    // Размонтирование NFS
    if (unmountBtn) {
        unmountBtn.addEventListener('click', async () => {
            const mountPoint = document.getElementById('nfsMountPoint')?.value.trim();
            
            if (!mountPoint) {
                showNfsAlert('<i class="fas fa-exclamation-circle me-1"></i>Mount Point is required', 'danger');
                return;
            }
            
            const confirmed = await showConfirmModal(
                'Размонтирование NFS',
                `Вы уверены, что хотите размонтировать NFS из <strong>${mountPoint}</strong>?`,
                'Размонтировать',
                'Отмена',
                'warning'
            );
            if (!confirmed) {
                return;
            }
            
            try {
                setButtonsDisabled(true);
                unmountBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Unmounting...';
                
                const result = await unmountNfs(mountPoint);
                
                showNfsAlert(
                    `<i class="fas fa-check-circle me-1"></i>${result.message}`,
                    'success'
                );
                
                // Обновляем статус
                await checkNfsStatus(mountPoint).then(updateNfsStatusInfo).catch(() => {});
                
            } catch (error) {
                showNfsAlert(`<i class="fas fa-exclamation-circle me-1"></i>Error: ${error.message}`, 'danger');
            } finally {
                setButtonsDisabled(false);
                unmountBtn.innerHTML = '<i class="fas fa-unlink me-1"></i>Unmount NFS';
            }
        });
    }
    
    // Тестирование NFS сервера
    if (testBtn) {
        testBtn.addEventListener('click', async () => {
            const nfsServer = document.getElementById('nfsServer')?.value.trim();
            
            if (!nfsServer) {
                showNfsAlert('<i class="fas fa-exclamation-circle me-1"></i>NFS Server is required', 'danger');
                return;
            }
            
            try {
                setButtonsDisabled(true);
                testBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Testing...';
                
                const result = await testNfsServer(nfsServer);
                
                let message = `<i class="fas fa-info-circle me-1"></i>Server: ${result.server}<br>`;
                message += `Ping: ${result.ping_available ? '<span class="text-success">Available</span>' : '<span class="text-danger">Unavailable</span>'}`;
                
                if (result.exports) {
                    message += `<br><small><strong>Available exports:</strong><br><pre class="mt-2 mb-0">${result.exports}</pre></small>`;
                }
                
                showNfsAlert(message, result.ping_available ? 'info' : 'warning');
                
            } catch (error) {
                showNfsAlert(`<i class="fas fa-exclamation-circle me-1"></i>Error: ${error.message}`, 'danger');
            } finally {
                setButtonsDisabled(false);
                testBtn.innerHTML = '<i class="fas fa-search me-1"></i>Test';
            }
        });
    }
    
    // Автоматическое заполнение mount point из конфигурации
    const nfsPathInput = document.getElementById('nfsPath');
    const nfsMountPointInput = document.getElementById('nfsMountPoint');
    
    if (nfsPathInput && nfsMountPointInput && !nfsMountPointInput.value) {
        nfsPathInput.addEventListener('input', (e) => {
            if (!nfsMountPointInput.value || nfsMountPointInput.value === '/mnt/veeam_nfs') {
                nfsMountPointInput.value = e.target.value || '/mnt/veeam_nfs';
            }
        });
    }
});

